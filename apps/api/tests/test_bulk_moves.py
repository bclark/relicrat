"""Atomic selections, retained per-copy history and overlapping PostgreSQL writes."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import delete, text
from test_reconciliation import setup as reconciliation_setup, request as reconcile
from relicrat.models import CopyLocationEvent, MediaAsset, OwnedCopy

pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable PostgreSQL')
BASE = '/api/v1/inventory'
LOC = '/api/v1/storage-locations'


@pytest.fixture
def selection(reconciliation_setup):
    api, engine, _, items, release = reconciliation_setup
    copies = [api.post(BASE, json={'title': f'Synthetic bulk copy {i}'}).json() for i in range(2)]
    locations = [api.post(LOC, json={'name': f'Synthetic bulk box {i}'}).json() for i in range(2)]
    ids = [uuid.UUID(c['id']) for c in copies]
    try:
        yield api, engine, copies, locations, items, release
    finally:
        from relicrat.models import ReconciliationEvent, StorageLocation
        with engine.begin() as db:
            for model in (CopyLocationEvent, MediaAsset, ReconciliationEvent):
                db.execute(delete(model).where(model.owned_copy_id.in_(ids)))
            db.execute(delete(OwnedCopy).where(OwnedCopy.id.in_(ids)))
            db.execute(delete(StorageLocation).where(StorageLocation.id.in_([uuid.UUID(l['id']) for l in locations])))


def move(api, destination, copies):
    return api.post(f'{LOC}/{destination}/move-copies', json={'copies': [
        {'id': c['id'], 'expected_storage_revision': c['storage_revision']} for c in copies]})


def test_bulk_retains_identity_links_media_and_each_history(selection):
    import io
    from PIL import Image
    api, _, copies, boxes, items, release = selection
    assert reconcile(api, copies[0]['id'], items[0], 0, release).status_code == 200
    image = io.BytesIO(); Image.new('RGB', (2, 2), (23, 44, 88)).save(image, 'PNG')
    photo = api.post(f"{BASE}/{copies[0]['id']}/photos", files={'file': ('synthetic.png', image.getvalue(), 'image/png')}).json()
    originals = [api.get(f"{BASE}/{c['id']}").json() for c in copies]
    for box in boxes:
        response = move(api, box['id'], copies)
        assert response.status_code == 200, response.text
        assert response.json() == {'moved_count': 2, 'unchanged_count': 0}
        copies = [api.get(f"{BASE}/{c['id']}").json() for c in copies]
    for original, copy in zip(originals, copies):
        for key in original.keys() - {'storage_location_id', 'storage_revision', 'updated_at'}:
            assert copy[key] == original[key]
        events = api.get(f"{BASE}/{copy['id']}/locations").json()
        assert [(e['before_revision'], e['after_revision']) for e in events] == [(0, 1), (1, 2)]
        assert [(e['before_location_id'], e['after_location_id']) for e in events] == [(None, boxes[0]['id']), (boxes[0]['id'], boxes[1]['id'])]
    assert api.get(f"{BASE}/{copies[0]['id']}/photos/{photo['id']}").content == image.getvalue()
    assert move(api, boxes[1]['id'], copies).json() == {'moved_count': 0, 'unchanged_count': 2}
    assert len(api.get(f"{BASE}/{copies[0]['id']}/locations").json()) == 2


def test_one_stale_copy_rejects_entire_selection_even_at_destination(selection):
    api, _, copies, boxes, *_ = selection
    assert api.post(f"{BASE}/{copies[1]['id']}/location", json={'storage_location_id': boxes[1]['id'], 'expected_storage_revision': 0}).status_code == 200
    assert move(api, boxes[1]['id'], copies).status_code == 409
    assert api.get(f"{BASE}/{copies[0]['id']}").json()['storage_location_id'] is None
    assert api.get(f"{BASE}/{copies[0]['id']}/locations").json() == []
    assert api.get(f"{BASE}/{copies[1]['id']}").json()['storage_location_id'] == boxes[1]['id']


@pytest.mark.parametrize('changed', ['missing', 'deleted', 'sold'])
def test_unavailable_copy_cannot_partially_move_selection(selection, changed):
    api, engine, copies, boxes, *_ = selection
    if changed == 'missing':
        copies[1] = {**copies[1], 'id': str(uuid.uuid4())}
    else:
        with engine.begin() as db:
            db.execute(text('UPDATE owned_copies SET '+("deleted_at = now()" if changed == 'deleted' else "ownership_status = 'sold'")+ ' WHERE id = :id'), {'id': copies[1]['id']})
    assert move(api, boxes[0]['id'], copies).status_code == 409
    assert api.get(f"{BASE}/{copies[0]['id']}/locations").json() == []


def test_invalid_selection_and_destination(selection):
    api, _, copies, boxes, *_ = selection
    path = f"{LOC}/{boxes[0]['id']}/move-copies"
    for value in [[], [{'id': copies[0]['id'], 'expected_storage_revision': 0}]*2,
                  [{'id': str(uuid.uuid4()), 'expected_storage_revision': 0} for _ in range(101)],
                  [{'id': copies[0]['id'], 'expected_storage_revision': True}],
                  [{'id': copies[0]['id'], 'expected_storage_revision': -1}]]:
        assert api.post(path, json={'copies': value}).status_code == 422
    assert move(api, str(uuid.uuid4()), copies).status_code == 404
    assert all(api.get(f"{BASE}/{c['id']}/locations").json() == [] for c in copies)


def test_overlapping_batches_serialize_without_partial_moves(selection):
    api, _, copies, boxes, *_ = selection
    start = Barrier(2)
    def submit(index):
        start.wait(timeout=10)
        return move(api, boxes[index]['id'], copies if index == 0 else list(reversed(copies)))
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, [0, 1]))
    assert sorted(r.status_code for r in responses) == [200, 409]
    destination = boxes[next(i for i,r in enumerate(responses) if r.status_code == 200)]['id']
    for copy in copies:
        assert api.get(f"{BASE}/{copy['id']}").json()['storage_location_id'] == destination
        assert len(api.get(f"{BASE}/{copy['id']}/locations").json()) == 1
