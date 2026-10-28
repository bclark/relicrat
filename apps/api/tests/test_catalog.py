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
