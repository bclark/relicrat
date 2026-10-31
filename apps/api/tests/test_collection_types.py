"""Bundled definitions are bounded data and must match deployed field storage."""
import copy
import pytest
from pydantic import ValidationError
from relicrat.collection_types import COLLECTION_TYPES, CollectionType, load_types
from relicrat.record_details import RecordDetails


def test_bundled_definitions_and_api_limits():
    types = load_types()
    assert list(types) == ['other', 'record']
    assert types['record'].title.label == 'Album title'
    assert [field.key for field in types['record'].fields if field.suggested] == ['artist', 'format', 'edition', 'notes']
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
])
def test_reject_invalid_definition(change):
    value = copy.deepcopy(COLLECTION_TYPES['record'].model_dump())
    change(value)
    with pytest.raises(ValidationError):
        CollectionType.model_validate(value)
