"""Validated, bundled form definitions. No user-selected paths or executable rules."""
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TypeField(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    key: Literal['title', 'artist', 'format', 'edition', 'notes']
    label: str = Field(min_length=1, max_length=80, pattern=r'^[^\x00]*$')
    max_length: int = Field(ge=1, le=10000)
    placeholder: str = Field(max_length=120, pattern=r'^[^\x00]*$')
    suggested: bool


class CollectionType(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    schema_version: Literal[1]
    id: Literal['other', 'record']
    label: str = Field(min_length=1, max_length=80, pattern=r'^[^\x00]*$')
    plural_label: str = Field(min_length=1, max_length=80, pattern=r'^[^\x00]*$')
    title: TypeField
    fields: list[TypeField] = Field(max_length=4)

    @field_validator('schema_version', mode='before')
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError('Schema version must be an integer')
        return value

    @model_validator(mode='after')
    def supported_storage(self):
        # These limits describe deployed storage, not an arbitrary custom-field engine.
        limits = {'title': 500, 'artist': 500, 'format': 100, 'edition': 500, 'notes': 10000}
        allowed = {'notes'} if self.id == 'other' else {'artist', 'format', 'edition', 'notes'}
        keys = [field.key for field in self.fields]
        if self.title.key != 'title' or len(keys) != len(set(keys)) or set(keys) != allowed:
            raise ValueError('Definition must describe exactly the supported fields')
        if any(field.max_length != limits[field.key] for field in [self.title, *self.fields]):
            raise ValueError('Field limits must match deployed storage validation')
        return self


def load_types() -> dict[str, CollectionType]:
    definitions = {}
    for ident in ('other', 'record'):
        path = Path(__file__).with_suffix('') / f'{ident}.json'
        definition = CollectionType.model_validate(json.loads(path.read_text()))
        if definition.id != ident:
            raise ValueError('Definition identity must match its bundled filename')
        definitions[ident] = definition
    return definitions


COLLECTION_TYPES = load_types()
