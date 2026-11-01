"""Validated definitions with optional operator-owned, read-only overrides."""
import json
import os
from pathlib import Path
from typing import Literal
from relicrat.barcodes import BarcodeFormat
from relicrat.barcode_providers import PROVIDERS
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TypeField(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    key: Literal['title', 'artist', 'format', 'issue_number', 'publisher', 'media_format', 'studio', 'edition', 'notes']
    label: str = Field(min_length=1, max_length=80, pattern=r'^[^\x00]*$')
    max_length: int = Field(ge=1, le=10000)
    placeholder: str = Field(max_length=120, pattern=r'^[^\x00]*$')
    suggested: bool
    input: Literal['text', 'autocomplete', 'select'] = 'text'
    options: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def supported_control(self):
        if self.input == 'autocomplete' and self.key not in ('artist','publisher','studio'):
            raise ValueError('Saved-value autocomplete is supported for artist, publisher and studio only')
        if self.input == 'select':
            if self.key not in ('format','media_format') or not self.options:
                raise ValueError('Format choices must be nonempty')
            if any(option == '__other__' or not option.strip() or option != option.strip() or len(option) > self.max_length or '\x00' in option for option in self.options):
                raise ValueError('Choices must be meaningful bounded text')
            if len({option.casefold() for option in self.options}) != len(self.options):
                raise ValueError('Choices must be unique')
        elif self.options:
            raise ValueError('Choices require a select control')
        return self


class BrowseGrouping(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True,str_strip_whitespace=True)
    field: Literal['artist','title']
    plural_label: str = Field(min_length=1,max_length=80,pattern=r'^[^\x00]*$')
    unknown_label: str = Field(min_length=1,max_length=80,pattern=r'^[^\x00]*$')
    order: Literal['title','issue_number']


class BarcodeLookup(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    provider: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,39}$')
    action_label: str = Field(min_length=1,max_length=80,pattern=r'^[^\x00]*$')
    max_results: int = Field(default=5,ge=1,le=10)
    field_mappings: dict[str,str] = Field(min_length=1,max_length=8)
    value_maps: dict[str,dict[str,str]] = Field(default_factory=dict,max_length=8)
    cover_art: bool = False


class CollectionType(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    schema_version: Literal[1]
    id: Literal['other', 'record', 'comic', 'movie']
    label: str = Field(min_length=1, max_length=80, pattern=r'^[^\x00]*$')
    plural_label: str = Field(min_length=1, max_length=80, pattern=r'^[^\x00]*$')
    barcode_formats: list[BarcodeFormat] = Field(default_factory=list, max_length=4)
    lookup: BarcodeLookup | None = None
    grouping: BrowseGrouping | None = None
    title: TypeField
    fields: list[TypeField] = Field(max_length=4)
    entry_order: list[Literal['title', 'artist', 'format', 'issue_number', 'publisher', 'media_format', 'studio', 'edition', 'notes']] = Field(default_factory=list, max_length=5)

    @field_validator('schema_version', mode='before')
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError('Schema version must be an integer')
        return value

    @model_validator(mode='after')
    def supported_storage(self):
        if len(self.barcode_formats) != len(set(self.barcode_formats)):
            raise ValueError('Barcode formats must be unique')
        # These limits describe deployed storage, not an arbitrary custom-field engine.
        limits = {'title': 500, 'artist': 500, 'format': 100, 'edition': 500, 'notes': 10000, 'issue_number': 100, 'publisher': 250, 'media_format': 100, 'studio': 250}
        allowed = {'other': {'notes'}, 'record': {'artist','format','edition','notes'}, 'comic': {'issue_number','publisher','edition','notes'}, 'movie': {'media_format','studio','edition','notes'}}[self.id]
        if self.lookup:
            lookup=self.lookup
            if lookup.provider not in PROVIDERS:
                raise ValueError('Lookup provider must be an installed adapter')
            provider=PROVIDERS[lookup.provider]
            if not self.barcode_formats or 'title' not in lookup.field_mappings or not set(lookup.field_mappings)<=(allowed|{'title'})-{'notes'}:
                raise ValueError('Lookup mappings must target supported fields and include title')
            if not set(lookup.field_mappings.values())<=provider['fields']:
                raise ValueError('Lookup mappings reference unavailable provider fields')
            if lookup.cover_art and not provider.get('cover'):
                raise ValueError('This provider has no cover adapter')
            for key,values in lookup.value_maps.items():
                if key not in lookup.field_mappings or len(values)>20:
                    raise ValueError('Value maps require a mapped target field and at most20 translations')
                if any(not source or len(source)>500 or '\x00' in source or not value or len(value)>limits[key] or '\x00' in value for source,value in values.items()):
                    raise ValueError('Value translations must fit stored fields')
        if self.grouping and (self.grouping.field,self.grouping.order) != {'record':('artist','title'),'comic':('title','issue_number'),'movie':('title','title')}.get(self.id):
            raise ValueError('Grouping must use supported storage fields and order')
        keys = [field.key for field in self.fields]
        if self.title.key != 'title' or len(keys) != len(set(keys)) or set(keys) != allowed:
            raise ValueError('Definition must describe exactly the supported fields')
        if 'entry_order' not in self.model_fields_set:
            self.entry_order = ['title', *keys]
        if len(self.entry_order) != len(set(self.entry_order)) or set(self.entry_order) != allowed | {'title'}:
            raise ValueError('Entry order must contain every supported field exactly once')
        if any(field.max_length != limits[field.key] for field in [self.title, *self.fields]):
            raise ValueError('Field limits must match deployed storage validation')
        return self


def _unique_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Collection definition contains duplicate keys')
        value[key] = item
    return value


def load_types() -> dict[str, CollectionType]:
    identifiers = ('other', 'record', 'comic', 'movie')
    bundled = Path(__file__).with_suffix('')
    overrides = {}
    directory = os.environ.get('RELICRAT_COLLECTION_TYPES_DIR')
    if directory is not None:
        # Operator-owned, read-only mount; never a browser/upload-selected path.
        root = Path(directory)
        if not directory or not root.is_absolute() or not root.is_dir():
            raise ValueError('Collection definition override directory is unavailable')
        overrides = {path.stem: path for path in root.iterdir() if path.suffix == '.json'}
        if not overrides or not set(overrides) <= set(identifiers):
            raise ValueError('Overrides must contain known collection-type JSON filenames')
    definitions = {}
    for ident in identifiers:
        path = overrides.get(ident, bundled / f'{ident}.json')
        if not path.is_file():
            raise ValueError('Collection definition must be a regular file')
        with path.open('rb') as source:
            content = source.read(65537)
        if len(content) > 65536:
            raise ValueError('Collection definition exceeds 64 KiB')
        definition = CollectionType.model_validate(json.loads(content, object_pairs_hook=_unique_keys))
        if definition.id != ident:
            raise ValueError('Definition identity must match its filename')
        definitions[ident] = definition
    return definitions


COLLECTION_TYPES = load_types()
