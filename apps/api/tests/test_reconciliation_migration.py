"""Migration round trip exclusively on the harness's disposable database.

The harness runs tests sequentially; no application writer is active here.
"""
import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

URL = os.getenv('TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='TEST_DATABASE_URL not configured')


def test_upgrade_initializes_existing_copy_and_roundtrip():
    config = Config('alembic.ini')
    engine = create_engine(URL)
    cid = uuid.uuid4()
    command.downgrade(config, '0001_foundation')
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO owned_copies (id, provisional_title) VALUES (:id, 'Synthetic pre-upgrade copy')"), {'id': cid})
            before = dict(conn.execute(text('SELECT * FROM owned_copies WHERE id = :id'), {'id': cid}).mappings().one())
        command.upgrade(config, 'head')
        with engine.connect() as conn:
            after = dict(conn.execute(text('SELECT * FROM owned_copies WHERE id = :id'), {'id': cid}).mappings().one())
            assert after.pop('identification_revision') == 0
            assert after.pop('storage_revision') == 0
            assert after == before
            assert conn.scalar(text('SELECT count(*) FROM reconciliation_events')) == 0
        command.downgrade(config, '0001_foundation')
        command.upgrade(config, 'head')
        with engine.connect() as conn:
            assert conn.scalar(text('SELECT identification_revision FROM owned_copies WHERE id = :id'), {'id': cid}) == 0
    finally:
        command.upgrade(config, 'head')
        with engine.begin() as conn:
            conn.execute(text('DELETE FROM owned_copies WHERE id = :id'), {'id': cid})
        engine.dispose()
