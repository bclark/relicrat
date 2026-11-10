"""Test the recipe boundary with synthetic source rows."""
import base64
import json
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from relicrat.models import Release
from test_inventory_api import client  # noqa: F401

CLZ_FIXTURE = Path(__file__).with_name('fixtures').joinpath('clz-games.synthetic.csv')


def post(api, stage, raw, recipe=None, **params):
    headers = {'content-type': 'text/csv'}
    if recipe is not None:
        headers['x-relicrat-import-recipe'] = base64.b64encode(json.dumps(recipe).encode()).decode()
    return api.post(f'/api/v1/imports/{stage}', content=raw, headers=headers,
                    params={'source': 'game_recipe', **params})


def reviewed(preview):
    return dict(reviewed_sha256=preview['sha256'], duplicate_digest=preview['duplicate_review']['digest'],
                skip_mask='0' * 1250)


def test_bundled_clz_games_recipe_preview_commit_and_retry(client):
    api, connection = client
    raw = CLZ_FIXTURE.read_bytes()
    p = post(api, 'preview', raw).json()
    assert p['copy_count'] == 2 and p['errors'] == []
    assert p['sample'][0]['game_release'] == {'platform': 'Synthetic Console'}
    assert p['sample'][1]['title'] == 'Synthetic Mystery'
    assert api.get('/api/v1/inventory').json() == []
    assert api.get('/api/v1/imports').json() == []
    response = post(api, 'commit', raw, **reviewed(p))
    assert response.status_code == 200, response.text
    batch = response.json()['batch']['id']
    assert post(api, 'commit', raw, **reviewed(p)).json()['already_imported']
    bundled = api.get('/api/v1/imports/recipes/clz-games').json()
    assert post(api, 'preview', raw, bundled).json()['existing_batch']['id'] == batch
    copies = {c['title']: c for c in api.get('/api/v1/inventory?collection_type=game').json()}
    assert len(copies) == 2
    assert copies['Synthetic Mystery']['release_id'] is None
    with Session(bind=connection) as db:
        release = db.get(Release, UUID(copies['Sample Quest']['release_id']))
        assert str(release.catalog_item_id) == copies['Sample Quest']['catalog_item_id']
        assert release.attributes == {'game': {'platform': 'Synthetic Console'}}
    rows = api.get(f'/api/v1/imports/{batch}/rows').json()
    assert rows[0]['source']['Publisher'] == 'Example Studio'
    assert api.get(f'/api/v1/imports/{batch}/possible-duplicates').json() == []


def test_custom_mapping_binds_review_and_keeps_copy_fields_separate(client):
    api, _ = client
    recipe = {'schema_version': 1, 'name': 'An invented export', 'collection': 'game',
              'columns': {'title': 'Name', 'region': 'Zone', 'edition': 'Version',
                          'quantity': 'Count', 'manual': 'Booklet', 'notes': 'Comment'}}
    raw = b'Name,Zone,Version,Count,Booklet,Comment\nSynthetic Adventure,PAL,Launch,2,missing,Copy note\n'
    result = post(api, 'preview', raw, recipe)
    assert result.status_code == 200, result.text
    p = result.json()
    assert p['copy_count'] == 2 and not p['errors']
    assert p['sample'][0]['game_release'] == {'region': 'PAL', 'edition': 'Launch'}
    changed = recipe | {'columns': recipe['columns'] | {'region': 'Version', 'edition': 'Zone'}}
    assert post(api, 'commit', raw, changed, **reviewed(p)).status_code == 409
    assert post(api, 'commit', raw, recipe, reviewed_sha256=p['sha256']).status_code == 422
    assert api.get('/api/v1/inventory').json() == []
    assert post(api, 'commit', raw, recipe, **reviewed(p)).status_code == 200
    copies = api.get('/api/v1/inventory?collection_type=game').json()
    assert len({c['id'] for c in copies}) == 2
    assert len({c['release_id'] for c in copies}) == 1
    assert all(c['game_contents']['manual'] == 'missing' and c['description'] == 'Copy note' for c in copies)


@pytest.mark.parametrize('extra', [{'transform': 'run me'}, {'schema_version': 2}, {'collection': 'comic'}])
def test_recipe_rejects_unsupported_values(client, extra):
    api, _ = client
    recipe = {'schema_version': 1, 'name': 'Synthetic', 'collection': 'game', 'columns': {'title': 'Title'}}
    assert post(api, 'preview', b'Title\nSynthetic\n', recipe | extra).status_code == 422
    assert api.get('/api/v1/imports').json() == []
