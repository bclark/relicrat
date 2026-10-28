"""Storage boundary, persistence and deterministic PostgreSQL concurrency checks."""
import io
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from PIL import Image
from sqlalchemy import delete, event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_reconciliation import setup as reconciliation_setup, request as reconcile, history as ident_history
from relicrat.models import CopyLocationEvent, MediaAsset, OwnedCopy, StorageLocation

BASE = '/api/v1/inventory'
LOC = '/api/v1/storage-locations'


@pytest.fixture
def setup(reconciliation_setup):
    api, engine, cid, items, release = reconciliation_setup
    locations = []
    for i in range(3):
        response = api.post(LOC, json={'name': f'  Synthetic {i}  ', 'parent_id': locations[-1]['id'] if locations else None})
        assert response.status_code == 201, response.text
        locations.append(response.json())
    try:
        yield api, engine, cid, items, release, locations
    finally:
        with engine.begin() as conn:
            conn.execute(delete(CopyLocationEvent).where(CopyLocationEvent.owned_copy_id == cid))
            conn.execute(text('UPDATE owned_copies SET storage_location_id = NULL WHERE id = :id'), {'id': cid})
            # Tests may change graph; clear parents before removing synthetic nodes.
            ids = [uuid.UUID(loc['id']) for loc in locations]
            conn.execute(StorageLocation.__table__.update().where(StorageLocation.id.in_(ids)).values(parent_id=None))
            conn.execute(delete(StorageLocation).where(StorageLocation.id.in_(ids)))


def assign(api, cid, location, revision):
    return api.post(f'{BASE}/{cid}/location', json={'storage_location_id': location, 'expected_storage_revision': revision})


def history(api, cid):
    r = api.get(f'{BASE}/{cid}/locations')
    assert r.status_code == 200
    return r.json()


def test_locations_boundaries(setup):
    api, _, _, _, _, locations = setup
    for i, location in enumerate(locations):
        assert location['name'] == f'Synthetic {i}'
        assert api.get(f"{LOC}/{location['id']}").json() == location
        assert location['parent_id'] == (locations[i-1]['id'] if i else None)
    listed = api.get(LOC).json()
    assert listed == sorted(listed, key=lambda x: (x['created_at'], x['id']))
    assert api.get(f'{LOC}?limit=1&offset=1').json() == listed[1:2]
    for query in ('limit=101', 'limit=0', 'offset=-1', 'limit=bad'):
        assert api.get(f'{LOC}?{query}').status_code == 422
    for payload in ({}, {'name': ' '}, {'name': 'x'*251}, {'name': 'x', 'kind': 'x'*101},
                    {'name': 'x', 'description': 'x'*10001}, {'name': 'x', 'parent_id': 'bad'},
                    {'name': 'x', 'unexpected': True}, {'name': None}):
        assert api.post(LOC, json=payload).status_code == 422
    assert api.post(LOC, json={'name': 'x', 'parent_id': str(uuid.uuid4())}).status_code == 404
    assert api.get(f'{LOC}/{uuid.uuid4()}').status_code == 404
    assert api.get(f'{LOC}/bad').status_code == 422
    assert api.get(LOC).json() == listed


def test_moves_preserve_reconciled_copy_and_exact_media(setup):
    api, engine, cid, items, release, locations = setup
    assert reconcile(api, cid, items[0], 0, release).status_code == 200
    identification = ident_history(api, cid)
    output = io.BytesIO()
    Image.new('RGB', (3, 3), (13, 43, 88)).save(output, 'PNG')
    data = output.getvalue()
    photo = api.post(f'{BASE}/{cid}/photos', files={'file': ('x.png', data, 'image/png')}).json()
    before = api.get(f'{BASE}/{cid}').json()
    with engine.connect() as conn:
        metadata = dict(conn.execute(select(MediaAsset.__table__).where(MediaAsset.id == uuid.UUID(photo['id']))).mappings().one())
    first = None
    for revision, target in enumerate((locations[0]['id'], locations[2]['id'], None)):
        response = assign(api, cid, target, revision)
        assert response.status_code == 200, response.text
        current = response.json()
        assert current['storage_revision'] == revision + 1
        assert current['storage_location_id'] == target
        for key in before.keys() - {'storage_revision', 'storage_location_id', 'updated_at'}:
            assert current[key] == before[key]
        events = history(api, cid)
        assert len(events) == revision + 1
        if first is None:
            first = events[:1]
        assert events[:1] == first
        assert events[-1]['before_revision'] == revision
        assert events[-1]['after_revision'] == revision + 1
        assert events[-1]['operation'] == 'manual'
        assert assign(api, cid, target, revision + 1).json() == current
        assert history(api, cid) == events
        assert assign(api, cid, target, revision).status_code == 409
        assert api.get(f'{BASE}/{cid}').json() == current
    assert ident_history(api, cid) == identification
    assert api.get(f"{BASE}/{cid}/photos/{photo['id']}").content == data
    assert api.get(f'{BASE}/{cid}/locations?limit=1&offset=1').json() == events[1:2]
    with engine.connect() as conn:
        assert dict(conn.execute(select(MediaAsset.__table__).where(MediaAsset.id == uuid.UUID(photo['id']))).mappings().one()) == metadata
        assert conn.scalar(select(OwnedCopy.storage_revision).where(OwnedCopy.id == cid)) == 3
        assert len(conn.execute(select(CopyLocationEvent).where(CopyLocationEvent.owned_copy_id == cid)).all()) == 3


def test_rejections_and_event_failure_rollback(setup):
    api, engine, cid, _, _, locations = setup
    before = api.get(f'{BASE}/{cid}').json()
    for payload in ({}, {'expected_storage_revision': 0}, {'storage_location_id': None},
                    {'storage_location_id': 'bad', 'expected_storage_revision': 0},
                    *({'storage_location_id': None, 'expected_storage_revision': rev} for rev in (-1, True, '0', .5, 2147483647)),
                    {'storage_location_id': None, 'expected_storage_revision': 0, 'extra': True}):
        assert api.post(f'{BASE}/{cid}/location', json=payload).status_code == 422
    assert assign(api, cid, str(uuid.uuid4()), 0).status_code == 404
    assert assign(api, cid, None, 1).status_code == 409
    assert assign(api, uuid.uuid4(), None, 0).status_code == 404
    assert api.get(f'{BASE}/{uuid.uuid4()}/locations').status_code == 404
    assert assign(api, 'bad', None, 0).status_code == 422
    for query in ('limit=0', 'limit=101', 'offset=-1'):
        assert api.get(f'{BASE}/{cid}/locations?{query}').status_code == 422
    assert api.get(f'{BASE}/{cid}').json() == before
    assert history(api, cid) == []
    assert assign(api, cid, locations[0]['id'], 0).status_code == 200
    before = api.get(f'{BASE}/{cid}').json()
    saved = history(api, cid)
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('INSERT INTO copy_location_events'):
            raise RuntimeError('Injected movement write failure')
    event.listen(engine, 'before_cursor_execute', fail)
    try:
        with pytest.raises(RuntimeError, match='Injected movement write failure'):
            assign(api, cid, locations[1]['id'], 1)
    finally:
        event.remove(engine, 'before_cursor_execute', fail)
    assert api.get(f'{BASE}/{cid}').json() == before
    assert history(api, cid) == saved
    with Session(engine) as db:
        db.get(OwnedCopy, cid).deleted_at = datetime.now(timezone.utc)
        db.commit()
    assert assign(api, cid, None, 1).status_code == 404
    assert api.get(f'{BASE}/{cid}/locations').status_code == 404
    with engine.connect() as conn:
        assert conn.scalar(select(OwnedCopy.storage_revision).where(OwnedCopy.id == cid)) == 1
        assert len(conn.execute(select(CopyLocationEvent).where(CopyLocationEvent.owned_copy_id == cid)).all()) == 1


def wait_blocked(engine, count, pattern):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with engine.connect() as conn:
            n = conn.scalar(text('''SELECT count(*) FROM pg_stat_activity
                WHERE datname = current_database() AND cardinality(pg_blocking_pids(pid)) > 0
                AND query LIKE :pattern'''), {'pattern': pattern})
        if n == count:
            return
        time.sleep(.01)
    pytest.fail(f'Expected {count} overlapping blocked transactions, saw {n}')


@pytest.mark.parametrize('independent', [False, True])
def test_overlapping_assignment_and_identification(setup, independent):
    api, engine, cid, items, release, locations = setup
    with engine.connect() as holder, ThreadPoolExecutor(max_workers=2) as pool:
        tx = holder.begin()
        holder.execute(select(OwnedCopy).where(OwnedCopy.id == cid).with_for_update())
        first = pool.submit(assign, api, cid, locations[0]['id'], 0)
        second = (pool.submit(reconcile, api, cid, items[0], 0, release) if independent
                  else pool.submit(assign, api, cid, locations[1]['id'], 0))
        try:
            wait_blocked(engine, 2, '%FROM owned_copies%FOR UPDATE%')
        finally:
            tx.rollback()
        results = [first.result(timeout=10), second.result(timeout=10)]
    assert sorted(r.status_code for r in results) == ([200, 200] if independent else [200, 409])
    current = api.get(f'{BASE}/{cid}').json()
    assert current['storage_revision'] == 1
    assert len(history(api, cid)) == 1
    if independent:
        assert current['identification_revision'] == 1
        assert current['catalog_item_id'] == str(items[0])
        assert current['release_id'] == str(release)
        assert current['storage_location_id'] == locations[0]['id']
        assert len(ident_history(api, cid)) == 1


@pytest.mark.parametrize('changes', [dict(before_revision=-1), dict(after_revision=3), dict(operation='ai'),
                                  dict(before_location_id=None, after_location_id=None), dict(after_location_id=uuid.uuid4()),
                                  dict(owned_copy_id=uuid.uuid4())])
def test_event_constraints(setup, changes):
    _, engine, cid, _, _, locations = setup
    values = dict(id=uuid.uuid4(), owned_copy_id=cid, before_location_id=None,
                  after_location_id=uuid.UUID(locations[0]['id']), before_revision=0, after_revision=1)
    values.update(changes)
    with engine.connect() as conn, pytest.raises(DBAPIError):
        conn.execute(CopyLocationEvent.__table__.insert().values(**values))


def test_historical_foreign_keys_and_unique_revision(setup):
    api, engine, cid, _, _, locations = setup
    for revision, target in enumerate((locations[2]['id'], None)):
        assert assign(api, cid, target, revision).status_code == 200
    with engine.connect() as conn:
        row = dict(conn.execute(select(CopyLocationEvent.__table__).where(CopyLocationEvent.owned_copy_id == cid).order_by(CopyLocationEvent.after_revision)).mappings().first())
        row['id'] = uuid.uuid4()
        with pytest.raises(DBAPIError):
            conn.execute(CopyLocationEvent.__table__.insert().values(**row))
        conn.rollback()
        for sql, value in [('DELETE FROM storage_locations WHERE id = :id', locations[2]['id']),
                           ('DELETE FROM owned_copies WHERE id = :id', cid),
                           ('UPDATE owned_copies SET storage_revision = -1 WHERE id = :id', cid)]:
            with pytest.raises(DBAPIError):
                conn.execute(text(sql), {'id': value})
            conn.rollback()


@pytest.mark.parametrize('mode', ['self', 'long', 'multi', 'insert', 'guard'])
def test_direct_sql_cycles_and_missing_guard(setup, mode):
    _, engine, _, _, _, locations = setup
    a, b, c = [x['id'] for x in locations]
    with engine.connect() as conn:
        before = conn.execute(text('SELECT id, parent_id FROM storage_locations ORDER BY id')).all()
        if mode == 'guard':
            conn.execute(text('DELETE FROM storage_hierarchy_guard'))
        with pytest.raises(DBAPIError):
            if mode == 'multi':
                conn.execute(text('UPDATE storage_locations SET parent_id = CASE WHEN id = :a THEN CAST(:c AS uuid) ELSE parent_id END WHERE id IN (:a, :b, :c)'), dict(a=a, b=b, c=c))
            elif mode == 'insert':
                x, y = uuid.uuid4(), uuid.uuid4()
                conn.execute(text("INSERT INTO storage_locations (id, name, parent_id) VALUES (:x, 'x', :y), (:y, 'y', :x)"), dict(x=x, y=y))
            else:
                conn.execute(text('UPDATE storage_locations SET parent_id = :parent WHERE id = :id'), dict(id=a, parent=a if mode == 'self' else None if mode == 'guard' else c))
        conn.rollback()
        assert conn.execute(text('SELECT id, parent_id FROM storage_locations ORDER BY id')).all() == before
        assert conn.scalar(text('SELECT count(*) FROM storage_hierarchy_guard')) == 1


@pytest.mark.parametrize('isolation', ['READ COMMITTED', 'REPEATABLE READ'])
def test_opposing_changes_with_preestablished_snapshots(setup, isolation):
    _, engine, _, _, _, locations = setup
    a, b, _ = [x['id'] for x in locations]
    with engine.begin() as conn:
        conn.execute(text('UPDATE storage_locations SET parent_id = NULL WHERE id = :b'), {'b': b})
    with engine.connect().execution_options(isolation_level=isolation) as one, engine.connect().execution_options(isolation_level=isolation) as two:
        # Both snapshots are established before the competing write and commit.
        one.execute(text('SELECT * FROM storage_locations')).all()
        two.execute(text('SELECT * FROM storage_locations')).all()
        one.execute(text('UPDATE storage_locations SET parent_id = :b WHERE id = :a'), dict(a=a, b=b))
        def opposing():
            try:
                two.execute(text('UPDATE storage_locations SET parent_id = :a WHERE id = :b'), dict(a=a, b=b))
                two.commit()
                return None
            except DBAPIError as error:
                two.rollback()
                return error.orig.sqlstate
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(opposing)
            try:
                wait_blocked(engine, 1, 'UPDATE storage_locations%')
            finally:
                one.commit()
            assert future.result(timeout=10) == ('40001' if isolation == 'REPEATABLE READ' else '23514')
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT parent_id FROM storage_locations WHERE id = :id'), {'id': a}) == uuid.UUID(b)
        assert conn.scalar(text('SELECT parent_id FROM storage_locations WHERE id = :id'), {'id': b}) is None
        conn.execute(text('SELECT check_storage_graph()'))


def test_deep_graph_and_valid_multirow_rotation(setup):
    _, engine, _, _, _, locations = setup
    a, b, c = [x['id'] for x in locations]
    with engine.connect() as conn:
        # Final graph c <- a <- b is valid even if row processing would
        # temporarily produce a -> c -> b -> a. Validate after the full statement.
        conn.execute(text("""UPDATE storage_locations SET parent_id =
            CASE WHEN id = :a THEN CAST(:c AS uuid) WHEN id = :c THEN NULL ELSE parent_id END
            WHERE id IN (:a, :c)"""), dict(a=a, c=c))
        conn.execute(text('SELECT check_storage_graph()'))
        conn.rollback()
        ids = [uuid.uuid4() for _ in range(160)]
        conn.execute(StorageLocation.__table__.insert().values([
            dict(id=ident, parent_id=ids[i-1] if i else None, name='Deep synthetic')
            for i, ident in enumerate(ids)]))
        conn.execute(text('SELECT check_storage_graph()'))
        with pytest.raises(DBAPIError, match='hierarchy contains a cycle'):
            conn.execute(text('UPDATE storage_locations SET parent_id = :last WHERE id = :first'),
                         dict(first=ids[0], last=ids[-1]))
        conn.rollback()
        assert conn.scalar(select(StorageLocation.id).where(StorageLocation.id == ids[0])) is None


@pytest.mark.parametrize("shadow", ["storage_locations", "storage_hierarchy_guard"])
def test_hierarchy_guard_uses_canonical_relations(setup, shadow):
    _, engine, _, _, _, locations = setup
    a, _, c = [location["id"] for location in locations]
    with engine.connect() as conn:
        if shadow == "storage_locations":
            conn.execute(text("CREATE TEMP TABLE storage_locations (id uuid, parent_id uuid)"))
            with pytest.raises(DBAPIError, match="hierarchy contains a cycle"):
                conn.execute(text("UPDATE public.storage_locations SET parent_id = :c WHERE id = :a"), dict(a=a, c=c))
        else:
            conn.execute(text("CREATE TEMP TABLE storage_hierarchy_guard (LIKE public.storage_hierarchy_guard INCLUDING ALL)"))
            conn.execute(text("INSERT INTO pg_temp.storage_hierarchy_guard (id) VALUES (1)"))
            before = conn.scalar(text("SELECT generation FROM public.storage_hierarchy_guard WHERE id = 1"))
            conn.execute(text("UPDATE public.storage_locations SET name = name WHERE id = :a"), dict(a=a))
            assert conn.scalar(text("SELECT generation FROM public.storage_hierarchy_guard WHERE id = 1")) == 1 - before
            assert conn.scalar(text("SELECT generation FROM pg_temp.storage_hierarchy_guard WHERE id = 1")) == 0
        conn.rollback()
