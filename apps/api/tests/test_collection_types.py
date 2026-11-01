"""Bundled definitions are bounded data and must match deployed field storage."""
import copy
import pytest
from pydantic import ValidationError
from relicrat.collection_types import COLLECTION_TYPES, CollectionType, load_types
from relicrat.record_details import RecordDetails


def test_bundled_definitions_and_api_limits():
    types = load_types()
    assert list(types) == ['other', 'record', 'comic']
    assert types['record'].label == 'Album'
    assert types['record'].plural_label == 'Albums'
    assert types['record'].id == 'record'  # Stable persisted ID; a label change needs no migration.
    assert types['record'].title.label == 'Album title'
    assert [field.key for field in types['record'].fields if field.suggested] == ['artist', 'format', 'edition', 'notes']
    assert types['record'].entry_order[0:2] == ['artist','title']
    assert types['record'].fields[0].input == 'autocomplete'
    assert types['record'].fields[1].options == ['Vinyl','CD','Cassette']
    for key in ('artist', 'format'):
        limit = next(field.max_length for field in types['record'].fields if field.key == key)
        assert getattr(RecordDetails(**{key: 'x'*limit}),key) == 'x'*limit
        with pytest.raises(ValidationError):
            RecordDetails(**{key: 'x'*(limit+1)})


@pytest.mark.parametrize('change', [
    lambda value: value.update(schema_version=2),
    lambda value: value.update(schema_version=True),
    lambda value: value.update(script='anything'),
    lambda value: value.update(id='../../secret'),
    lambda value: value['fields'].append(value['fields'][0]),
    lambda value: value['fields'][0].update(key='price'),
    lambda value: value['fields'][0].update(max_length=501),
    lambda value: value['fields'][0].update(label='  '),
    lambda value: value['fields'][0].update(label='bad\x00label'),
    lambda value: value['fields'][0].update(suggested='yes'),
    lambda value: value['title'].update(key='artist'),
    lambda value: value.update(fields=[]),
    lambda value: value.update(entry_order=[]),
    lambda value: value.update(entry_order=['artist','title','format','edition','artist']),
    lambda value: value.update(entry_order=['title','format','edition','notes']),
    lambda value: value['fields'][0].update(input='select',options=['A']),
    lambda value: value['fields'][1].update(input='autocomplete',options=[]),
    lambda value: value['fields'][1].update(options=['Vinyl','vinyl']),
    lambda value: value['fields'][1].update(options=[]),
    lambda value: value['fields'][1].update(options=['__other__']),
    lambda value: value['fields'][1].update(options=['x'*101]),
    lambda value: value['fields'][1].update(options=[' ']),
    lambda value: value['fields'][0].update(options=['x']),
])
def test_reject_invalid_definition(change):
    value = copy.deepcopy(COLLECTION_TYPES['record'].model_dump())
    change(value)
    with pytest.raises(ValidationError):
        CollectionType.model_validate(value)


def test_earlier_v1_definitions_keep_title_first_when_order_is_omitted():
    value=COLLECTION_TYPES['record'].model_dump(exclude={'entry_order'})
    definition=CollectionType.model_validate(value)
    assert definition.entry_order==['title','artist','format','edition','notes']


def test_comic_definition_matches_bounded_storage():
    from relicrat.comic_details import ComicDetails
    definition=COLLECTION_TYPES['comic']
    assert definition.label=='Comic' and definition.title.label=='Series/title'
    assert definition.entry_order==['title','issue_number','publisher','edition','notes']
    assert ComicDetails(issue_number=' 001½ ',publisher=' Example Press ').model_dump()=={'issue_number':'001½','publisher':'Example Press'}
    for values in ({'issue_number':'x'*101},{'publisher':'x'*251},{'issue_number':423},{'unknown':'x'}):
        with pytest.raises(ValidationError):ComicDetails(**values)


def test_browse_grouping_is_bounded_and_uses_supported_fields():
    from copy import deepcopy
    from pydantic import ValidationError
    from relicrat.collection_types import CollectionType,load_types
    definitions=load_types()
    assert definitions['record'].grouping.field=='artist'
    assert definitions['comic'].grouping.order=='issue_number'
    assert definitions['other'].grouping is None
    for patch in ({'field':'price'},{'field':'title'},{'order':'issue_number'},{'unknown_label':'bad\x00label'},{'url':'https://invalid.test'}):
        value=deepcopy(definitions['record'].model_dump());value['grouping'].update(patch)
        with pytest.raises(ValidationError):CollectionType.model_validate(value)


def test_barcode_formats_are_declared_bounded_unique_and_optional():
    for definition in COLLECTION_TYPES.values():
        assert definition.barcode_formats==['UPC_A','UPC_E','EAN_8','EAN_13']
    earlier=COLLECTION_TYPES['record'].model_dump(exclude={'barcode_formats'})
    assert CollectionType.model_validate(earlier).barcode_formats==[]
    for formats in (['QR_CODE'],['UPC_A','UPC_A'],['EAN_13']*5,'UPC_A'):
        value=copy.deepcopy(earlier);value['barcode_formats']=formats
        with pytest.raises(ValidationError):CollectionType.model_validate(value)
