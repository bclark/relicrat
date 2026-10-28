"""Auth upgrade/downgrade preserves collection rows; sessions are deliberately lost."""
import os
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

URL = os.getenv('TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='TEST_DATABASE_URL not configured')


def test_auth_migration_preserves_existing_copy_and_drops_access_state():
    engine = create_engine(URL)
    config = Config('alembic.ini')
    ident = uuid4()
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO owned_copies (id, provisional_title) VALUES (:id, 'Synthetic auth migration')"), {'id': ident})
            before = dict(connection.execute(text('SELECT * FROM owned_copies WHERE id=:id'), {'id': ident}).mappings().one())
        command.downgrade(config, '0003_storage')
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT to_regclass('owner_sessions')")) is None
            assert dict(connection.execute(text('SELECT * FROM owned_copies WHERE id=:id'), {'id': ident}).mappings().one()) == before
        command.upgrade(config, 'head')
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT count(*) FROM owner_sessions')) == 0
            assert connection.scalar(text('SELECT failures FROM owner_login_guard WHERE id=1')) == 0
            assert dict(connection.execute(text('SELECT * FROM owned_copies WHERE id=:id'), {'id': ident}).mappings().one()) == before
    finally:
        command.upgrade(config, 'head')
        with engine.begin() as connection:
            connection.execute(text('DELETE FROM owned_copies WHERE id=:id'), {'id': ident})
        engine.dispose()
