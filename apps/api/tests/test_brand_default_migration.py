"""Factory default upgrades preserve owner choices and invalidate stale saves."""
import json
import os
import runpy
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from relicrat.theme_values import DEFAULT_THEME, PRESETS

URL = os.getenv('TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='TEST_DATABASE_URL not configured')


@pytest.mark.parametrize('factory,revision', [(True, 0), (True, 7), (False, 0), (False, 9)])
def test_brand_default_preserves_choices_and_revisions(factory, revision):
    engine = create_engine(URL); config = Config('alembic.ini')
    migration = runpy.run_path('alembic/versions/0010_brand_default.py')
    old = json.loads(migration['OLD_DEFAULT'])
    theme = old if factory else PRESETS[1]
    try:
        command.downgrade(config, '0009_csv_import')
        with engine.begin() as db:
            db.execute(text('UPDATE appearance_settings SET theme=CAST(:theme AS jsonb),revision=:revision WHERE id=1'),
                       {'theme':json.dumps(theme), 'revision':revision})
            preferences = dict(db.execute(text('SELECT * FROM collection_settings WHERE id=1')).mappings().one())
        command.upgrade(config, '0010_brand_default')
        changed = factory and revision == 0
        with engine.connect() as db:
            row = db.execute(text('SELECT theme,revision FROM appearance_settings WHERE id=1')).one()
            assert row.theme == (DEFAULT_THEME if changed else theme)
            assert row.revision == revision + int(changed)
            assert dict(db.execute(text('SELECT * FROM collection_settings WHERE id=1')).mappings().one()) == preferences
        command.downgrade(config, '0009_csv_import')
        with engine.connect() as db:
            row = db.execute(text('SELECT theme,revision FROM appearance_settings WHERE id=1')).one()
            assert row.theme == theme
            assert row.revision == revision + (2 if changed else 0)
        command.upgrade(config, '0010_brand_default')
        with engine.connect() as db:
            row = db.execute(text('SELECT theme,revision FROM appearance_settings WHERE id=1')).one()
            # A rollback's higher revision must never be mistaken for pristine.
            assert row.theme == theme
            assert row.revision == revision + (2 if changed else 0)
    finally:
        command.upgrade(config, 'head')
        with engine.begin() as db:
            db.execute(text('UPDATE appearance_settings SET theme=CAST(:theme AS jsonb),revision=0 WHERE id=1'),
                       {'theme':json.dumps(DEFAULT_THEME)})
        engine.dispose()


def test_fresh_install_and_database_default_match_runtime():
    engine = create_engine(URL); config = Config('alembic.ini')
    migration = runpy.run_path('alembic/versions/0010_brand_default.py')
    assert json.loads(migration['NEW_DEFAULT']) == DEFAULT_THEME
    try:
        command.downgrade(config, '0007_comics')
        command.upgrade(config, 'head')
        with engine.connect() as db:
            assert db.scalar(text('SELECT theme FROM appearance_settings WHERE id=1')) == DEFAULT_THEME
            assert db.scalar(text('SELECT revision FROM appearance_settings WHERE id=1')) == 1
            # These disposable writes roll back when the connection closes.
            db.execute(text('DELETE FROM appearance_settings WHERE id=1'))
            db.execute(text('INSERT INTO appearance_settings (id) VALUES (1)'))
            assert db.scalar(text('SELECT theme FROM appearance_settings WHERE id=1')) == DEFAULT_THEME
        command.downgrade(config, '0009_csv_import')
        with engine.connect() as db:
            db.execute(text('DELETE FROM appearance_settings WHERE id=1'))
            db.execute(text('INSERT INTO appearance_settings (id) VALUES (1)'))
            assert db.scalar(text('SELECT theme FROM appearance_settings WHERE id=1')) == json.loads(migration['OLD_DEFAULT'])
    finally:
        command.upgrade(config, 'head')
        with engine.begin() as db:
            db.execute(text('UPDATE appearance_settings SET theme=CAST(:theme AS jsonb),revision=0 WHERE id=1'),
                       {'theme':json.dumps(DEFAULT_THEME)})
        engine.dispose()
