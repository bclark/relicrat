"""Catalog boundaries and ownership separation on disposable PostgreSQL."""
import io
import os
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import text

from test_inventory_api import client

pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL not configured')
BASE = '/api/v1/catalog'


def created(api, path, payload):
    response = api.post(BASE + path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def identities(api):
    category = created(api, '/categories', {'name': '  Synthetic comics  '})
    item = created(api, '/items', {'category_id': category['id'], 'canonical_name': '  Synthetic 100%_comic  '})
    release = created(api, f"/items/{item['id']}/releases", {'name': '  First printing  '})
    return category, item, release


def test_catalog_creates_no_ownership_and_similar_names_stay_distinct(client):
    api, connection = client
    before = connection.execute(text('SELECT count(*) FROM owned_copies')).scalar_one()
    category, item, release = identities(api)
    other = created(api, '/items', {'category_id': category['id'], 'canonical_name': item['canonical_name']})
    assert category['name'] == 'Synthetic comics' and item['canonical_name'] == 'Synthetic 100%_comic'
    assert release['name'] == 'First printing' and release['catalog_item_id'] == item['id']
    assert other['id'] != item['id']
    assert connection.execute(text('SELECT count(*) FROM owned_copies')).scalar_one() == before
    keys = connection.execute(text('SELECT identity_key FROM catalog_items WHERE id IN (:a, :b)'), {'a': item['id'], 'b': other['id']}).scalars().all()
    assert len(set(keys)) == 2 and all(key.startswith('manual-') for key in keys)
    assert api.get(f"{BASE}/items/{item['id']}").json() == item
    assert api.get(f"{BASE}/items/{item['id']}/releases/{release['id']}").json() == release
    assert api.get(f"{BASE}/items/{other['id']}/releases/{release['id']}").status_code == 404
    assert api.get(f"{BASE}/items/{other['id']}/releases").json() == []


def test_search_is_literal_bounded_and_pages_are_deterministic(client):
    api, _ = client
    category, item, _ = identities(api)
    other = created(api, '/items', {'category_id': category['id'], 'canonical_name': 'Synthetic 100xxcomic'})
    for query in ('100%', '%_'):
        result = api.get(BASE + '/items', params={'q': query}).json()
        assert [row['id'] for row in result] == [item['id']]
    assert api.get(BASE + '/items', params={'q': "' OR 1=1 --"}).json() == []
    assert api.get(BASE + '/items', params={'q': 'X' * 201}).status_code == 422
    assert api.get(BASE + '/items', params={'q': '\x00'}).status_code == 422
    listed = api.get(BASE + '/items').json()
    assert listed == sorted(listed, key=lambda row: (row['canonical_name'], row['id']))
    assert api.get(BASE + '/items?limit=1&offset=1').json() == listed[1:2]
    assert {item['id'], other['id']} <= {row['id'] for row in listed}
    for path in ('/categories', '/items', f"/items/{item['id']}/releases"):
        for query in ('limit=0', 'limit=101', 'offset=-1'):
            assert api.get(BASE + path + '?' + query).status_code == 422
    categories = api.get(BASE + '/categories').json()
    assert api.get(BASE + '/categories?limit=1&offset=0').json() == categories[:1]


def test_creation_validation_and_missing_parents(client):
    api, _ = client
    category, item, _ = identities(api)
    for payload in ({}, {'name': ' '}, {'name': 'x' * 201}, {'name': '\x00'}, {'name': 'x', 'slug': 'override'}):
        assert api.post(BASE + '/categories', json=payload).status_code == 422
    for payload in ({}, {'category_id': 'bad', 'canonical_name': 'x'}, {'category_id': category['id'], 'canonical_name': ' '},
                    {'category_id': category['id'], 'canonical_name': '\x00'}, {'category_id': category['id'], 'canonical_name': 'x' * 501},
                    {'category_id': category['id'], 'canonical_name': 'x', 'owned_copy_id': str(uuid4())}):
        assert api.post(BASE + '/items', json=payload).status_code == 422
    assert api.post(BASE + '/items', json={'category_id': str(uuid4()), 'canonical_name': 'x'}).status_code == 404
    for payload in ({}, {'name': ' '}, {'name': 'x' * 501}, {'name': '\x00'}, {'name': 'x', 'catalog_item_id': str(uuid4())}):
        assert api.post(f"{BASE}/items/{item['id']}/releases", json=payload).status_code == 422
    for path in (f'/items/{uuid4()}', f'/items/{uuid4()}/releases', f"/items/{item['id']}/releases/{uuid4()}"):
        assert api.get(BASE + path).status_code == 404
    assert api.post(f'{BASE}/items/{uuid4()}/releases', json={'name': 'x'}).status_code == 404


def test_identification_preserves_copy_media_storage_and_retained_history(client, tmp_path, monkeypatch):
    api, _ = client
    monkeypatch.setenv('MEDIA_ROOT', str(tmp_path))
    _, item, release = identities(api)
    copy = api.post('/api/v1/inventory', json={'title': 'Mystery', 'description': 'Original notes'}).json()
    cid = copy['id']
    image = io.BytesIO()
    Image.new('RGB', (2, 2), 'blue').save(image, format='PNG')
    photo = api.post(f'/api/v1/inventory/{cid}/photos', files={'file': ('test.png', image.getvalue(), 'image/png')}).json()
    location = api.post('/api/v1/storage-locations', json={'name': 'Test shelf'}).json()
    copy = api.post(f'/api/v1/inventory/{cid}/location', json={'storage_location_id': location['id'], 'expected_storage_revision': 0}).json()
    for revision, edition in enumerate((release['id'], None)):
        response = api.post(f'/api/v1/inventory/{cid}/reconcile', json={'catalog_item_id': item['id'], 'release_id': edition, 'expected_revision': revision})
        assert response.status_code == 200, response.text
        actual = response.json()
        for key in ('id', 'title', 'description', 'ownership_status', 'storage_location_id', 'storage_revision', 'created_at'):
            assert actual[key] == copy[key]
    assert actual['identification_revision'] == 2 and actual['release_id'] is None
    history = api.get(f'/api/v1/inventory/{cid}/reconciliations').json()
    assert len(history) == 2 and history[-1]['before_release_id'] == release['id']
    assert api.get(f'/api/v1/inventory/{cid}/photos/{photo["id"]}').content == image.getvalue()
    assert api.post(f'/api/v1/inventory/{cid}/reconcile', json={'catalog_item_id': item['id'], 'expected_revision': 0}).status_code == 409


def test_game_releases_are_shared_and_copy_contents_are_independent(client):
    api, connection = client
    inventory = '/api/v1/inventory'
    assert api.post(inventory, json={'collection_type': 'game', 'description': 'Title unknown'}).status_code == 422
    assert api.post(inventory, json={'title': 'Other', 'game_contents': {'manual': 'missing'}}).status_code == 422
    title = 'Synthetic Orbit Racer'
    response = api.post(inventory, json={'collection_type': 'game', 'title': title})
    assert response.status_code == 201, response.text
    first = response.json()
    assert first['game_contents'] == {} and first['release_id'] is None
    response = api.post(inventory, json={'collection_type': 'game', 'title': title,
                                        'game_contents': {'media': 'present', 'packaging': 'present'}})
    assert response.status_code == 201, response.text
    second = response.json()
    item = created(api, '/items', {'video_game': True, 'canonical_name': title})
    other = created(api, '/items', {'video_game': True, 'canonical_name': 'Synthetic Other Game'})
    assert other['category_id'] == item['category_id']
    assert api.get(BASE + '/items', params={'video_game': 'true', 'q': title}).json() == [item]
    release_path = f"/items/{item['id']}/releases"
    details = {'platform': 'Example 64', 'region': 'Japan', 'edition': 'Launch'}
    release = created(api, release_path, {'game_details': details})
    assert api.get(BASE + release_path).json() == [release]
    for copy in (first, second):
        response = api.post(f"{inventory}/{copy['id']}/reconcile",
                            json={'catalog_item_id': item['id'], 'release_id': release['id'], 'expected_revision': 0})
        assert response.status_code == 200, response.text
        assert response.json()['game_contents'] == copy['game_contents']

    path = f"{inventory}/{first['id']}"
    edit = {'title': title, 'edition_label': None, 'expected_details_revision': 0,
            'expected_identification_revision': 1, 'game_contents': {'packaging': 'missing', 'inserts': 'not_applicable'}}
    response = api.post(path + '/details', json=edit)
    assert response.status_code == 200, response.text
    assert response.json()['release_id'] == release['id']
    assert api.post(path + '/details', json=edit).status_code == 409
    event = api.get(path + '/detail-history').json()[0]
    assert event['before_game_contents'] == {} and event['after_game_contents'] == edit['game_contents']
    assert api.get(f"{inventory}/{second['id']}").json()['game_contents'] == second['game_contents']
    assert api.get(BASE + release_path + '/' + release['id']).json()['game_details'] == details
    assert connection.execute(text('SELECT attributes FROM releases WHERE id=:id'), {'id': release['id']}).scalar_one() == {'game': details}
    assert {r['id'] for r in api.get(inventory, params={'collection_type': 'game'}).json()} >= {first['id'], second['id']}


def test_game_suggestions_combine_local_titles_and_release_details(client):
    api, _ = client
    for kind, title in [('game', 'Orbit Quest'), ('movie', 'Orbit Film')]:
        response = api.post('/api/v1/inventory', json={'collection_type': kind, 'title': title})
        assert response.status_code == 201, response.text
    item = created(api, '/items', {'video_game': True, 'canonical_name': 'orbit quest'})
    created(api, '/items', {'video_game': True, 'canonical_name': 'Orbit Quest II'})
    created(api, f"/items/{item['id']}/releases", {
        'game_details': {'platform': 'Example 64', 'region': 'Japan', 'edition': 'Launch'},
    })
    base = '/api/v1/collection-settings/game-suggestions/'
    for field, term, expected in [
        ('title', 'orBIT', ['Orbit Quest', 'Orbit Quest II']),
        ('platform', 'Ex', ['Example 64']),
        ('region', 'ja', ['Japan']),
        ('edition', 'lau', ['Launch']),
        ('title', '%', []),
        ('title', ' ', []),
    ]:
        response = api.get(base + field, params={'q': term})
        assert response.status_code == 200, response.text
        assert response.json() == expected
    assert api.get(base + 'notes', params={'q': 'or'}).status_code == 422
