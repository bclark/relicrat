"""Real transactions and independent sessions on the disposable PostgreSQL DB."""
import io
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
import time

import pytest
from fastapi.testclient import TestClient
from auth_helpers import sign_in
from PIL import Image
from sqlalchemy import create_engine, delete, event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.main import app
from relicrat.models import Category, CatalogItem, Release, OwnedCopy, MediaAsset, ReconciliationEvent, StorageLocation

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not configured")
BASE = "/api/v1/inventory"


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    engine = create_engine(URL)
    with Session(engine) as db:
        category = Category(slug=str(uuid.uuid4()), name="Synthetic")
        db.add(category)
        db.flush()
        items = [CatalogItem(category_id=category.id, canonical_name="Synthetic", identity_key=str(uuid.uuid4())) for _ in range(2)]
        db.add_all(items)
        db.flush()
        location = StorageLocation(name="Synthetic shelf")
        db.add(location)
        db.flush()
        release = Release(catalog_item_id=items[0].id, release_key="standard")
        copy = OwnedCopy(provisional_title="Original mystery", description="Original notes", ownership_status="sold", storage_location_id=location.id)
        db.add_all([release, copy])
        db.commit()
        ids = [x.id for x in items]
        copy_id, release_id, category_id, location_id = copy.id, release.id, category.id, location.id
    def override():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as api:
            sign_in(api)
            yield api, engine, copy_id, ids, release_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        with engine.begin() as conn:
            conn.execute(delete(ReconciliationEvent).where(ReconciliationEvent.owned_copy_id == copy_id))
            conn.execute(delete(MediaAsset).where(MediaAsset.owned_copy_id == copy_id))
            conn.execute(delete(OwnedCopy).where(OwnedCopy.id == copy_id))
            conn.execute(delete(Release).where(Release.id == release_id))
            conn.execute(delete(CatalogItem).where(CatalogItem.id.in_(ids)))
            conn.execute(delete(StorageLocation).where(StorageLocation.id == location_id))
            conn.execute(delete(Category).where(Category.id == category_id))
        engine.dispose()


def request(api, copy_id, item, revision, release=None):
    return api.post(f"{BASE}/{copy_id}/reconcile", json={"catalog_item_id": str(item), "release_id": str(release) if release else None, "expected_revision": revision})


def history(api, copy_id):
    response = api.get(f"{BASE}/{copy_id}/reconciliations")
    assert response.status_code == 200
    return response.json()


def test_corrections_noop_and_exact_media_survive(setup):
    api, engine, cid, items, release = setup
    before = api.get(f"{BASE}/{cid}").json()
    output = io.BytesIO()
    Image.new("RGB", (3, 3), (23, 44, 67)).save(output, "PNG")
    data = output.getvalue()
    photo = api.post(f"{BASE}/{cid}/photos", files={"file": ("x.png", data, "image/png")}).json()
    with Session(engine) as db:
        asset_before = dict(db.execute(select(MediaAsset.__table__).where(MediaAsset.id == uuid.UUID(photo['id']))).mappings().one())
    assert request(api, cid, items[0], 0).status_code == 200
    first = history(api, cid)
    assert first[0]["before_catalog_item_id"] is None
    assert first[0]["before_status"] == "unidentified"
    assert first[0]["after_release_id"] is None
    assert request(api, cid, items[0], 1, release).status_code == 200
    assert request(api, cid, items[1], 2).status_code == 200
    final = api.get(f"{BASE}/{cid}").json()
    assert final["identification_revision"] == 3
    assert final["identification_status"] == "identified"
    for key in ('id', 'title', 'description', 'ownership_status', 'storage_location_id', 'created_at'):
        assert final[key] == before[key]
    events = history(api, cid)
    assert len(events) == 3 and events[:1] == first
    assert events[2]['before_release_id'] == str(release)
    assert events[2]['after_catalog_item_id'] == str(items[1])
    assert all(e['operation'] == 'manual' for e in events)
    assert request(api, cid, items[1], 3).json() == final
    assert history(api, cid) == events
    assert api.get(f"{BASE}/{cid}/reconciliations?limit=1&offset=1").json() == events[1:2]
    for query in ('limit=101', 'limit=0', 'offset=-1'):
        assert api.get(f"{BASE}/{cid}/reconciliations?{query}").status_code == 422
    assert api.get(f"{BASE}/{cid}/photos/{photo['id']}").content == data
    with Session(engine) as db:
        assert dict(db.execute(select(MediaAsset.__table__).where(MediaAsset.id == uuid.UUID(photo['id']))).mappings().one()) == asset_before
        assert db.get(OwnedCopy, cid).identification_revision == 3
        assert len(db.scalars(select(ReconciliationEvent).where(ReconciliationEvent.owned_copy_id == cid)).all()) == 3


def test_rejections_are_unchanged(setup):
    api, engine, cid, items, release = setup
    before = api.get(f"{BASE}/{cid}").json()
    for item, rev, rel, status in [(uuid.uuid4(), 0, None, 404), (items[0], 0, uuid.uuid4(), 404), (items[1], 0, release, 422), (items[0], 1, None, 409)]:
        assert request(api, cid, item, rev, rel).status_code == status
        assert api.get(f"{BASE}/{cid}").json() == before
        assert history(api, cid) == []
    for payload in ({}, {'catalog_item_id': str(items[0])}, {'catalog_item_id': None, 'expected_revision': 0}, {'catalog_item_id': 'bad', 'expected_revision': 0}, *({'catalog_item_id': str(items[0]), 'expected_revision': r} for r in (-1, True, '0', 0.5)), {'catalog_item_id': str(items[0]), 'expected_revision': 0, 'verified': True}):
        assert api.post(f"{BASE}/{cid}/reconcile", json=payload).status_code == 422
        assert api.get(f"{BASE}/{cid}").json() == before
        assert history(api, cid) == []
    assert request(api, uuid.uuid4(), items[0], 0).status_code == 404
    assert api.get(f"{BASE}/{uuid.uuid4()}/reconciliations").status_code == 404
    assert request(api, cid, items[0], 0).status_code == 200
    saved = history(api, cid)
    assert request(api, cid, items[0], 0).status_code == 409  # even stale no-op
    assert history(api, cid) == saved
    with Session(engine) as db:
        db.get(OwnedCopy, cid).deleted_at = datetime.now(timezone.utc)
        db.commit()
    assert request(api, cid, items[1], 1).status_code == 404
    assert api.get(f"{BASE}/{cid}/reconciliations").status_code == 404
    with Session(engine) as db:
        assert db.get(OwnedCopy, cid).identification_revision == 1
        assert len(db.scalars(select(ReconciliationEvent).where(ReconciliationEvent.owned_copy_id == cid)).all()) == 1


def test_event_write_failure_rolls_back_copy(setup):
    api, engine, cid, items, _ = setup
    assert request(api, cid, items[0], 0).status_code == 200
    saved = history(api, cid)
    before = api.get(f"{BASE}/{cid}").json()
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('INSERT INTO reconciliation_events'):
            raise RuntimeError('Injected event write failure')
    event.listen(engine, 'before_cursor_execute', fail)
    try:
        with pytest.raises(RuntimeError, match='Injected event write failure'):
            request(api, cid, items[1], 1)
    finally:
        event.remove(engine, 'before_cursor_execute', fail)
    assert api.get(f"{BASE}/{cid}").json() == before
    assert history(api, cid) == saved
    with Session(engine) as db:
        assert db.get(OwnedCopy, cid).catalog_item_id == items[0]
        assert db.get(OwnedCopy, cid).identification_revision == 1


def test_concurrent_requests_only_one_commits(setup):
    api, engine, cid, items, _ = setup
    barrier = Barrier(2)
    def run(item):
        barrier.wait(timeout=10)
        return request(api, cid, item, 0)
    # Hold the row so both API transactions must reach and wait at FOR UPDATE.
    # This proves overlap rather than relying on thread scheduling alone.
    with engine.connect() as holder, ThreadPoolExecutor(max_workers=2) as pool:
        transaction = holder.begin()
        holder.execute(select(OwnedCopy).where(OwnedCopy.id == cid).with_for_update())
        futures = [pool.submit(run, item) for item in items]
        try:
            deadline = time.monotonic() + 10
            blocked = 0
            while time.monotonic() < deadline:
                with engine.connect() as monitor:
                    blocked = monitor.scalar(text("""
                        SELECT count(*) FROM pg_stat_activity
                        WHERE datname = current_database()
                          AND cardinality(pg_blocking_pids(pid)) > 0
                          AND query LIKE '%FROM owned_copies%FOR UPDATE%'
                    """))
                if blocked == 2:
                    break
                time.sleep(0.01)
            assert blocked == 2, "Both requests must wait for the identification row lock"
        finally:
            transaction.rollback()
        results = [future.result(timeout=10) for future in futures]
    assert sorted(r.status_code for r in results) == [200, 409]
    winner = next(r.json() for r in results if r.status_code == 200)
    assert api.get(f"{BASE}/{cid}").json() == winner
    assert len(history(api, cid)) == 1
    assert history(api, cid)[0]['after_catalog_item_id'] == winner['catalog_item_id']


@pytest.mark.parametrize('assignment', ["identification_revision = -1"])
def test_revision_sql_constraint(setup, assignment):
    _, engine, cid, _, _ = setup
    with engine.connect() as conn:
        with pytest.raises(DBAPIError):
            conn.execute(text(f"UPDATE owned_copies SET {assignment} WHERE id = :id"), {'id': cid})


@pytest.mark.parametrize('changes', [
    {'after_revision': 4}, {'before_revision': -1}, {'operation': 'automatic'},
    {'after_status': 'verified'}, {'before_status': 'invalid'},
    {'after_catalog_item_id': uuid.uuid4()}, {'owned_copy_id': uuid.uuid4()},
    {'before_release_id': 'release'}, {'after_catalog_item_id': 'other'},
    {'before_catalog_item_id': 'other', 'before_release_id': 'release'},
])
def test_history_sql_constraints(setup, changes):
    api, engine, cid, items, release = setup
    values = dict(id=uuid.uuid4(), owned_copy_id=cid, before_catalog_item_id=None,
                  before_release_id=None, after_catalog_item_id=items[0], after_release_id=release,
                  before_status='unidentified', after_status='identified', before_revision=0, after_revision=1, operation='manual')
    values.update({k: release if v == 'release' else items[1] if v == 'other' else v for k, v in changes.items()})
    with engine.connect() as conn:
        with pytest.raises(DBAPIError):
            conn.execute(ReconciliationEvent.__table__.insert().values(**values))


def test_history_unique_revision_and_references_restrict_deletion(setup):
    api, engine, cid, items, _ = setup
    request(api, cid, items[0], 0)
    with engine.connect() as conn:
        values = dict(conn.execute(select(ReconciliationEvent.__table__).where(ReconciliationEvent.owned_copy_id == cid)).mappings().one())
        values['id'] = uuid.uuid4()
        with pytest.raises(DBAPIError):
            conn.execute(ReconciliationEvent.__table__.insert().values(**values))
        conn.rollback()
        with pytest.raises(DBAPIError):
            conn.execute(delete(OwnedCopy).where(OwnedCopy.id == cid))


def test_omitted_release_and_status_only_change(setup):
    api, engine, cid, items, release = setup
    assert request(api, cid, items[0], 0, release).status_code == 200
    response = api.post(f"{BASE}/{cid}/reconcile", json={"catalog_item_id": str(items[0]), "expected_revision": 1})
    assert response.status_code == 200
    assert response.json()['release_id'] is None
    assert response.json()['identification_revision'] == 2
    with Session(engine) as db:
        db.get(OwnedCopy, cid).identification_status = 'verified'
        db.commit()
    assert request(api, cid, items[0], 2).json()['identification_status'] == 'identified'
    assert history(api, cid)[-1]['before_status'] == 'verified'
    assert history(api, cid)[-1]['after_revision'] == 3
