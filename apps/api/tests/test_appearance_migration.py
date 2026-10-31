"""Upgrade and downgrade on disposable PostgreSQL; customized themes are guarded."""
import json
import os
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from relicrat.theme_values import DEFAULT_THEME, PRESETS, THEME_CHECK

URL = os.getenv('TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='TEST_DATABASE_URL not configured')


def test_appearance_upgrade_and_guarded_downgrade():
    engine = create_engine(URL); config = Config('alembic.ini')
    command.downgrade(config,'0007_comics')
    try:
        with engine.connect() as db:
            before = dict(db.execute(text('SELECT * FROM collection_settings WHERE id=1')).mappings().one())
        command.upgrade(config,'head')
        with engine.begin() as db:
            assert dict(db.execute(text('SELECT * FROM collection_settings WHERE id=1')).mappings().one()) == before
            assert db.scalar(text('SELECT theme FROM appearance_settings WHERE id=1')) == DEFAULT_THEME
            db.execute(text('UPDATE appearance_settings SET theme=CAST(:theme AS jsonb),revision=1 WHERE id=1'),{'theme':json.dumps(PRESETS[1])})
        with pytest.raises(RuntimeError,match='Export the customized theme'):
            command.downgrade(config,'0007_comics')
        with engine.begin() as db:
            assert db.scalar(text('SELECT theme FROM appearance_settings WHERE id=1')) == PRESETS[1]
            db.execute(text('UPDATE appearance_settings SET theme=CAST(:theme AS jsonb) WHERE id=1'),{'theme':json.dumps(DEFAULT_THEME)})
        command.downgrade(config,'0007_comics')
        with engine.connect() as db: assert db.scalar(text("SELECT to_regclass('appearance_settings')")) is None
        command.upgrade(config,'head')
        # Migrations freeze the contract instead of importing changing runtime code.
        import runpy
        migration = runpy.run_path('alembic/versions/0008_appearance.py')
        assert migration['THEME_CHECK'] == THEME_CHECK
    finally:
        command.upgrade(config,'head'); engine.dispose()
