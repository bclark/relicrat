"""Authoring is bounded data validation; it never installs a type or writes copies."""
import copy
import json
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from relicrat.collection_proposals import CollectionProposal, authoring_contract, parse_proposal, router

EXAMPLE = Path(__file__).with_name('fixtures') / 'tmnt-original-1988.json'


def example():
    return json.loads(EXAMPLE.read_text())


def test_example_and_generated_contract():
    value = parse_proposal(EXAMPLE.read_bytes())
    assert len(value.collection.checklist) == 10
    assert authoring_contract()['schema'] == CollectionProposal.model_json_schema()
    assert 'plain HTTPS string' in authoring_contract()['prompt']
    assert 'never [label]' in authoring_contract()['prompt']
    assert value.model_dump() == example()
    published = Path(__file__).resolve().parent / '../../../packages/collection-packs/proposals/tmnt-original-1988/collection.draft.json'
    if published.exists():
        assert json.loads(published.read_text()) == example()


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(owned=True),
    lambda d: d.update(draft_format='unknown'),
    lambda d: d['type_definition'].update(id='comic'),
    lambda d: d['type_definition'].update(lookup={'provider':'untrusted'}),
    lambda d: d['type_definition']['optional_fields'].append(d['type_definition']['optional_fields'][0]),
    lambda d: d['type_definition']['title'].update(required=False),
    lambda d: d['type_definition']['title'].update(required=1),
    lambda d: d['type_definition']['title'].update(max_length=10000),
    lambda d: d['collection'].update(type_id='different'),
    lambda d: d['collection']['completion'].update(required_entries=11),
    lambda d: d['collection']['completion'].update(required_entries=True),
    lambda d: d['collection']['completion'].update(variants_count_separately=True),
    lambda d: d['collection']['checklist'][1].update(id='leonardo'),
    lambda d: d['collection']['checklist'][0].update(source_ids=['missing']),
    lambda d: d['sources'][0].update(url='javascript:alert(1)'),
    lambda d: d['sources'][0].update(url='https://owner:secret@example.com'),
    lambda d: d['sources'].append(d['sources'][0]),
])
def test_reject_unsupported_or_inconsistent_data(mutation):
    value = copy.deepcopy(example())
    mutation(value)
    with pytest.raises(HTTPException) as error:
        parse_proposal(json.dumps(value).encode())
    assert error.value.status_code == 422


@pytest.mark.parametrize('content', [b'{"status":1,"status":2}', b'{', b'NaN', b'\xff', b'[' * 2000, b'null', '{}'.encode('utf-16')])
def test_invalid_json_is_rejected_without_echo(content):
    with pytest.raises(HTTPException) as error:
        parse_proposal(content)
    assert error.value.status_code == 422


def test_preview_has_no_writes_and_bounds_actual_stream_bytes():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    result = client.post('/api/v1/collection-proposals/preview', content=EXAMPLE.read_bytes(), headers={'content-type':'application/json'})
    assert result.status_code == 200
    assert result.json()['proposal'] == example()
    assert 'Nothing was installed' in result.json()['notice']
    assert client.post('/api/v1/collection-proposals/preview', content=b' ' * 65537, headers={'content-type':'application/json'}).status_code == 413
    assert client.post('/api/v1/collection-proposals/preview', content=b'{}', headers={'content-type':'text/plain'}).status_code == 415
    assert client.get('/api/v1/collection-proposals/authoring').status_code == 200
