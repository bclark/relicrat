"""Synthetic CLZ storage review, atomicity, stale-state and owner boundaries."""
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from relicrat import import_storage
from relicrat.csv_import import commit_import
from relicrat.models import CopyLocationEvent, ImportCopy, OwnedCopy, StorageLocation
from test_csv_import import encoded, post
from test_inventory_api import client


def imported(api, rows, source='clz'):
    raw = encoded(source, rows)
    result = post(api, 'commit', raw, source, reviewed_sha256=hashlib.sha256(raw).hexdigest())
    assert result.status_code == 200, result.text
    batch = result.json()['batch']['id']
    copies = api.get(f'/api/v1/imports/{batch}/rows?limit=100').json()
    return f'/api/v1/imports/{batch}', [c['copy_id'] for c in copies]


def place(api, name='Synthetic destination'):
    return api.post('/api/v1/storage-locations', json={'name': name}).json()['id']


def move(api, copy, location, revision):
    result = api.post(f'/api/v1/inventory/{copy}/location', json={
        'storage_location_id': location, 'expected_storage_revision': revision})
    assert result.status_code == 200, result.text


def test_preview_and_atomic_mapping_preserve_prior_choices(client):
    api, connection = client
    path, copies = imported(api, [{'Quantity': '6'}, {'Storage Box': 'Other box'}, {'Storage Box': ''}])
    destination = place(api)
    move(api, copies[0], destination, 0)
    move(api, copies[1], destination, 0)
    move(api, copies[1], None, 1)
    connection.execute(text("UPDATE owned_copies SET ownership_status='sold' WHERE id=:id"), {'id': copies[2]})
    connection.execute(text('UPDATE owned_copies SET deleted_at=now() WHERE id=:id'), {'id': copies[3]})
    choice = {'label': ' Test Box \t', 'destination_id': destination}
    labels = api.get(path+'/storage-labels').json()
    assert labels['unlabeled_copy_count'] == 1
    box = next(b for b in labels['labels'] if b['label'] == 'Test Box')
    assert (box['copy_count'], box['eligible_count'], box['preserved_count']) == (6, 2, 4)
    preview = api.post(path+'/storage-preview', json=choice).json()
    assert (preview['assigned_count'], preview['previously_moved_count'], preview['inactive_count']) == (1, 1, 2)
    assert {c['id'] for c in preview['copies']} == set(copies[4:6])
    assert api.get(f'/api/v1/inventory/{copies[4]}/locations').json() == []
    body = choice | {'reviewed_token': preview['reviewed_token']}
    result = api.post(path+'/storage-apply', json=body)
    assert result.status_code == 200, result.text
    assert result.json()['moved_count'] == 2 and result.json()['preserved_count'] == 4
    for copy in copies[4:6]:
        events = api.get(f'/api/v1/inventory/{copy}/locations').json()
        assert len(events) == 1
        assert events[0]['before_location_id'] is None and events[0]['after_location_id'] == destination
        assert events[0]['after_revision'] == 1 and events[0]['operation'] == 'manual'
    assert api.get(f'/api/v1/inventory/{copies[1]}').json()['storage_location_id'] is None
    assert api.get(f'/api/v1/inventory/{copies[6]}').json()['storage_revision'] == 0
    assert api.get(path+'/rows?limit=100').json()[0]['source']['Storage Box'] == 'Test Box'
    assert api.post(path+'/storage-apply', json=body).status_code == 409
    assert len(api.get(f'/api/v1/inventory/{copies[4]}/locations').json()) == 1


def test_labels_and_copy_pagination_scoping_and_literal_labels(client):
    api, _ = client
    unusual = '<script>%_ box & "label"'
    path, copies = imported(api, [{'Storage Box': unusual, 'Quantity': '25'}] +
                            [{'Storage Box': f'Box {i:02}'} for i in range(24)] +
                            [{'Storage Box': 'X'*501}, {'Storage Box': '\t  '}])
    other, other_copies = imported(api, [{'Series': 'Separate batch', 'Storage Box': unusual}])
    labels = api.get(path+'/storage-labels?limit=20').json()['labels']
    rest = api.get(path+'/storage-labels?limit=20&offset=20').json()['labels']
    assert len(labels) == 20 and len(rest) == 6
    assert not rest[-1]['supported']
    destination = place(api)
    choice = {'label': unusual, 'destination_id': destination}
    first = api.post(path+'/storage-preview?limit=20', json=choice).json()
    last = api.post(path+'/storage-preview?limit=20&offset=20', json=choice).json()
    assert first['eligible_count'] == 25 and first['more']
    assert len(last['copies']) == 5 and not last['more']
    assert first['reviewed_token'] == last['reviewed_token']
    assert not {c['id'] for c in first['copies']} & {c['id'] for c in last['copies']}
    assert api.post(other+'/storage-apply', json=choice | {'reviewed_token': first['reviewed_token']}).status_code == 409
    assert api.get(f'/api/v1/inventory/{other_copies[0]}').json()['storage_revision'] == 0
    assert api.post(path+'/storage-preview', json=choice | {'label': 'missing'}).status_code == 404
    assert api.post(path+'/storage-preview', json=choice | {'label': 'X'*501}).status_code == 422


@pytest.mark.parametrize('change', ['move', 'details', 'inactive', 'destination'])
def test_stale_review_rejects_whole_mapping(client, change):
    api, connection = client
    path, copies = imported(api, [{'Quantity': '3'}])
    choice = {'label': 'Test Box', 'destination_id': place(api)}
    preview = api.post(path+'/storage-preview', json=choice).json()
    if change == 'move': move(api, copies[0], place(api, 'Manual destination'), 0)
    elif change == 'details': connection.execute(text('UPDATE owned_copies SET details_revision=details_revision+1 WHERE id=:id'), {'id': copies[0]})
    elif change == 'inactive': connection.execute(text("UPDATE owned_copies SET ownership_status='sold' WHERE id=:id"), {'id': copies[0]})
    else: choice['destination_id'] = place(api, 'Different destination')
    result = api.post(path+'/storage-apply', json=choice | {'reviewed_token': preview['reviewed_token']})
    assert result.status_code == 409, result.text
    assert all(api.get(f'/api/v1/inventory/{c}').json()['storage_revision'] == 0 for c in copies[1:])


def test_failure_rolls_back_every_move_and_event(client, monkeypatch):
    api, _ = client
    path, copies = imported(api, [{'Quantity': '3'}])
    choice = {'label': 'Test Box', 'destination_id': place(api)}
    preview = api.post(path+'/storage-preview', json=choice).json()
    original = import_storage.stage_location_assignment
    calls = 0
    def fail(db, copy, destination):
        nonlocal calls
        calls += 1
        original(db, copy, destination)
        db.flush()
        if calls == 2: raise RuntimeError('synthetic move failure')
    monkeypatch.setattr(import_storage, 'stage_location_assignment', fail)
    with pytest.raises(RuntimeError, match='synthetic move failure'):
        api.post(path+'/storage-apply', json=choice | {'reviewed_token': preview['reviewed_token']})
    for copy in copies:
        assert api.get(f'/api/v1/inventory/{copy}').json()['storage_revision'] == 0
        assert api.get(f'/api/v1/inventory/{copy}/locations').json() == []


def test_source_owner_and_input_boundaries(client):
    api, _ = client
    path, _ = imported(api, [{}], 'discogs')
    choice = {'label': 'Test Box', 'destination_id': place(api)}
    assert api.get(path+'/storage-labels').status_code == 422
    assert api.post(path+'/storage-preview', json=choice).status_code == 422
    clz, _ = imported(api, [{}])
    assert api.post(clz+'/storage-apply', json=choice).status_code == 422
    assert api.post(clz+'/storage-preview', json=choice | {'unexpected': True}).status_code == 422
    assert api.post(clz+'/storage-preview', json=choice | {'destination_id': str(uuid4())}).status_code == 404
    assert api.get(clz+'/storage-labels?limit=101').status_code == 422
    assert api.get(f'/api/v1/imports/{uuid4()}/storage-labels').status_code == 404
    api.cookies.clear(); api.headers.pop('authorization', None)
    assert api.get(clz+'/storage-labels').status_code == 401
    assert api.post(clz+'/storage-preview', json=choice).status_code == 401
    assert api.post(clz+'/storage-apply', json=choice | {'reviewed_token': 'a'*64}).status_code == 401


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable PostgreSQL')
def test_concurrent_mapping_applies_once():
    engine = create_engine(os.environ['TEST_DATABASE_URL'])
    raw = encoded('clz', [{'Series': 'Synthetic concurrency '+str(uuid4()), 'Quantity': '5'}])
    batch_id = None; ids = []; destination_id = None
    try:
        with Session(engine) as db:
            batch = commit_import('clz', raw, hashlib.sha256(raw).hexdigest(), db)['batch']
            batch_id = UUID(str(batch['id']))
            ids = list(db.scalars(select(ImportCopy.owned_copy_id).where(ImportCopy.batch_id == batch_id)))
            destination = StorageLocation(name='Synthetic concurrent destination')
            db.add(destination); db.commit(); destination_id = destination.id
            choice = import_storage.MappingChoice(label='Test Box', destination_id=destination_id)
            plan, _ = import_storage.mapping_plan(db, batch_id, choice)
        body = import_storage.MappingCommit(**choice.model_dump(), reviewed_token=plan['reviewed_token'])
        barrier = Barrier(2)
        def run():
            with Session(engine) as db:
                db.execute(text("SET lock_timeout='8s'"))
                barrier.wait()
                try: return import_storage.apply(batch_id, body, db)['moved_count']
                except HTTPException as e: return e.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(lambda _: run(), range(2))) == [5, 409]
        with Session(engine) as db:
            assert len(list(db.scalars(select(CopyLocationEvent).where(CopyLocationEvent.owned_copy_id.in_(ids))))) == 5
    finally:
        with engine.begin() as db:
            for ident in ids:
                db.execute(text('DELETE FROM copy_location_events WHERE owned_copy_id=:id'), {'id': ident})
                db.execute(text('DELETE FROM import_copies WHERE owned_copy_id=:id'), {'id': ident})
                db.execute(text('DELETE FROM owned_copies WHERE id=:id'), {'id': ident})
            if batch_id: db.execute(text('DELETE FROM import_batches WHERE id=:id'), {'id': batch_id})
            if destination_id: db.execute(text('DELETE FROM storage_locations WHERE id=:id'), {'id': destination_id})
        engine.dispose()


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable PostgreSQL')
def test_concurrent_manual_move_and_mapping_respect_revisions():
    from relicrat.storage import assign_location, AssignmentError
    engine = create_engine(os.environ['TEST_DATABASE_URL'])
    raw = encoded('clz', [{'Series': 'Synthetic manual race '+str(uuid4()), 'Quantity': '3'}])
    batch_id = None; ids = []; location_ids = []
    try:
        with Session(engine) as db:
            batch = commit_import('clz', raw, hashlib.sha256(raw).hexdigest(), db)['batch']
            batch_id = UUID(str(batch['id']))
            ids = list(db.scalars(select(ImportCopy.owned_copy_id).where(ImportCopy.batch_id == batch_id).order_by(ImportCopy.owned_copy_id)))
            places = [StorageLocation(name='Synthetic mapping race'), StorageLocation(name='Synthetic manual race')]
            db.add_all(places); db.commit(); location_ids = [p.id for p in places]
            choice = import_storage.MappingChoice(label='Test Box', destination_id=location_ids[0])
            plan, _ = import_storage.mapping_plan(db, batch_id, choice)
        body = import_storage.MappingCommit(**choice.model_dump(), reviewed_token=plan['reviewed_token'])
        barrier = Barrier(2)
        def run(mapping):
            with Session(engine) as db:
                db.execute(text("SET lock_timeout='8s'")); barrier.wait()
                try:
                    if mapping: return import_storage.apply(batch_id, body, db)['moved_count']
                    assign_location(db, ids[-1], location_ids[1], 0); return 1
                except (HTTPException, AssignmentError) as error: return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(run, [True, False]))
        assert results in ([3, 409], [409, 1])
        with Session(engine) as db:
            events = list(db.scalars(select(CopyLocationEvent).where(CopyLocationEvent.owned_copy_id.in_(ids))))
            assert len(events) == (3 if results[0] == 3 else 1)
            assert all(event.after_revision == 1 for event in events)
    finally:
        with engine.begin() as db:
            for ident in ids:
                db.execute(text('DELETE FROM copy_location_events WHERE owned_copy_id=:id'), {'id': ident})
                db.execute(text('DELETE FROM import_copies WHERE owned_copy_id=:id'), {'id': ident})
                db.execute(text('DELETE FROM owned_copies WHERE id=:id'), {'id': ident})
            if batch_id: db.execute(text('DELETE FROM import_batches WHERE id=:id'), {'id': batch_id})
            for ident in location_ids: db.execute(text('DELETE FROM storage_locations WHERE id=:id'), {'id': ident})
        engine.dispose()
