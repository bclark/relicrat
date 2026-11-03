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
    assert value.model_dump(exclude_defaults=True) == example()
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


@pytest.mark.parametrize('field', [
 {'id':'head','label':'Head','input':'radio','max_length':50,'options':[]},
 {'id':'head','label':'Head','input':'select','max_length':50,'options':['Soft','soft']},
 {'id':'head','label':'Head','input':'checkbox','max_length':50,'options':['Yes']},
 {'id':'head','label':'Head','input':'text','max_length':50,'options':['Text']},
])
def test_invalid_control_contract(field):
    value=example();value['type_definition']['optional_fields']=[field]
    with pytest.raises(HTTPException):parse_proposal(json.dumps(value).encode())


def test_authoring_contract_confirms_controls_before_json():
    prompt = authoring_contract()['prompt']
    assert 'Confirm the field plan before final JSON' in prompt
    assert 'exact option labels' in prompt
    assert 'options ["Soft Head", "Hard Head"]' in prompt
    assert 'within the three-question budget' in prompt
    assert 'Preserve existing value labels exactly' in prompt


def test_preview_preserves_agreed_controls_and_exact_choice_labels():
    value = example()
    fields = [
        {'id':'head_variant','label':'Head Variant','input':'radio','max_length':50,'options':['Soft Head','Hard Head']},
        {'id':'packaging','label':'Packaging','input':'select','max_length':50,'options':['Loose','Carded']},
        {'id':'accessories','label':'Accessories','input':'checkboxes','max_length':50,'options':['Sword','Belt']},
    ]
    value['type_definition']['optional_fields'] = fields
    app = FastAPI()
    app.include_router(router)
    result = TestClient(app).post('/api/v1/collection-proposals/preview', json=value)
    assert result.status_code == 200
    assert result.json()['proposal']['type_definition']['optional_fields'] == fields
    assert 'Nothing was installed or added to inventory' in result.json()['notice']


@pytest.mark.parametrize('destination', [
    'https://example.com/checklist',
    'https://example.com/List_of_figures_(1988_series)',
])
def test_single_markdown_evidence_link_has_canonical_plain_url(destination):
    value = example()
    value['sources'][0]['url'] = destination
    plain = parse_proposal(json.dumps(value).encode()).model_dump(exclude_defaults=True)
    value['sources'][0]['url'] = f'[Checklist]({destination})'
    corrected = parse_proposal(json.dumps(value).encode())
    assert corrected.model_dump(exclude_defaults=True) == plain
    assert corrected.sources[0]._markdown_link_corrected
    assert '_markdown_link_corrected' not in json.dumps(corrected.model_dump())


@pytest.mark.parametrize('url', [
    '[Checklist](http://example.com/checklist)',
    '[Checklist](javascript:alert(1))',
    '[Checklist](https://owner:secret@example.com/checklist)',
    '[One](https://example.com/one) [Two](https://example.com/two)',
    '[One](https://example.com/one)[Two](https://example.com/two)',
    'See [Checklist](https://example.com/checklist)',
    '[Checklist](https://example.com/unbalanced(foo)',
    '[Checklist](https://example.com/one)(https://example.com/two)',
    '[Checklist](https://example.com/with space)',
    '<a href="https://example.com/checklist">Checklist</a>',
])
def test_ambiguous_or_unsafe_markdown_evidence_stays_rejected(url):
    value = example()
    value['sources'][0]['url'] = url
    with pytest.raises(HTTPException) as error:
        parse_proposal(json.dumps(value).encode())
    assert error.value.status_code == 422
    assert 'secret' not in str(error.value.detail)


def test_preview_reports_markdown_corrections_and_retains_raw_input():
    value = example()
    value['sources'] = [dict(value['sources'][0], id=f'source_{i}', url=f'[Checklist](https://example.com/checklist_{i})') for i in range(3)]
    for entry in value['collection']['checklist']:
        entry['source_ids'] = ['source_0']
    original = json.dumps(value)
    app = FastAPI()
    app.include_router(router)
    result = TestClient(app).post('/api/v1/collection-proposals/preview', content=original, headers={'content-type':'application/json'})
    assert result.status_code == 200
    assert 'Converted 3 Markdown evidence link(s)' in result.json()['notice']
    assert [s['url'] for s in result.json()['proposal']['sources']] == [f'https://example.com/checklist_{i}' for i in range(3)]
    assert json.dumps(value) == original
