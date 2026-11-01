"""0003 validates legacy data atomically and retains assignments on downgrade."""
import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

URL = os.getenv('TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='TEST_DATABASE_URL not configured')


@pytest.mark.parametrize('cyclic', [False, True])
def test_legacy_topology_upgrade_and_roundtrip(cyclic):
    config = Config('alembic.ini')
    engine = create_engine(URL)
    a, b, c, cid = [uuid.uuid4() for _ in range(4)]
    command.downgrade(config, '0002_reconciliation')
    try:
        with engine.begin() as conn:
            for ident, parent in ((a, None), (b, a), (c, b)):
                conn.execute(text("INSERT INTO storage_locations (id, name, parent_id) VALUES (:id, 'Legacy synthetic', :parent)"), dict(id=ident, parent=parent))
            if cyclic:
                conn.execute(text('UPDATE storage_locations SET parent_id = :c WHERE id = :a'), dict(a=a, c=c))
            conn.execute(text("INSERT INTO owned_copies (id, provisional_title, storage_location_id) VALUES (:id, 'Legacy copy', :loc)"), dict(id=cid, loc=c))
            before = dict(conn.execute(text('SELECT * FROM owned_copies WHERE id = :id'), dict(id=cid)).mappings().one())
            topology = conn.execute(text('SELECT * FROM storage_locations ORDER BY id')).all()
        if cyclic:
            with pytest.raises(DBAPIError, match='hierarchy contains a cycle'):
                command.upgrade(config, 'head')
            with engine.connect() as conn:
                assert conn.scalar(text('SELECT version_num FROM alembic_version')) == '0002_reconciliation'
                assert conn.scalar(text("SELECT to_regclass('storage_hierarchy_guard')")) is None
                assert conn.scalar(text("SELECT to_regprocedure('check_storage_graph()')")) is None
                assert conn.execute(text('SELECT * FROM storage_locations ORDER BY id')).all() == topology
                assert dict(conn.execute(text('SELECT * FROM owned_copies WHERE id = :id'), dict(id=cid)).mappings().one()) == before
            with engine.begin() as conn:
                conn.execute(text('UPDATE storage_locations SET parent_id = NULL WHERE id = :a'), dict(a=a))
        command.upgrade(config, 'head')
        with engine.connect() as conn:
            after = dict(conn.execute(text('SELECT * FROM owned_copies WHERE id = :id'), dict(id=cid)).mappings().one())
            assert after.pop('storage_revision') == 0
            assert after.pop('collection_type') == 'other'
            assert after.pop('record_details') == {}
            assert after.pop('barcode') == {}
            assert after.pop('comic_details') == {}
            assert after.pop('edition_label') is None
            assert after.pop('details_revision') == 0
            assert after == before
            assert conn.scalar(text('SELECT count(*) FROM copy_location_events')) == 0
        # Verify downgrade drops populated history but retains current assignment.
        with engine.begin() as conn:
            conn.execute(text('''INSERT INTO copy_location_events
                (id, owned_copy_id, before_location_id, after_location_id, before_revision, after_revision)
                VALUES (:event, :id, NULL, :c, 0, 1)'''), dict(event=uuid.uuid4(), id=cid, c=c))
            conn.execute(text('UPDATE owned_copies SET storage_revision = 1 WHERE id = :id'), dict(id=cid))
        command.downgrade(config, '0002_reconciliation')
        with engine.connect() as conn:
            assert dict(conn.execute(text('SELECT * FROM owned_copies WHERE id = :id'), dict(id=cid)).mappings().one()) == before
            assert conn.scalar(text("SELECT to_regclass('copy_location_events')")) is None
        command.upgrade(config, 'head')
        with engine.connect() as conn:
            assert conn.scalar(text('SELECT storage_revision FROM owned_copies WHERE id = :id'), dict(id=cid)) == 0
            assert conn.scalar(text('SELECT count(*) FROM copy_location_events')) == 0
    finally:
        # Repair legacy cycle if a failed assertion left the graph at 0002.
        with engine.begin() as conn:
            conn.execute(text('UPDATE storage_locations SET parent_id = NULL WHERE id IN (:a, :b, :c)'), dict(a=a, b=b, c=c))
            conn.execute(text('DELETE FROM owned_copies WHERE id = :id'), dict(id=cid))
            conn.execute(text('DELETE FROM storage_locations WHERE id IN (:a, :b, :c)'), dict(a=a, b=b, c=c))
        command.upgrade(config, 'head')
        engine.dispose()
