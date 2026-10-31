"""Additive Comics upgrade preserves earlier observations; downgrade refuses loss."""
import os
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine,text

URL=os.getenv('TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='TEST_DATABASE_URL not configured')


def test_comics_upgrade_preserves_rows_and_downgrade_refuses_data_history_and_preferences():
    engine=create_engine(URL);config=Config('alembic.ini');old=uuid4();comic=uuid4();event=uuid4()
    command.downgrade(config,'0006_records_setup')
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO owned_copies(id,provisional_title,collection_type,record_details) VALUES (:id,'Existing album','record',jsonb_build_object('artist','Existing artist'))"),{'id':old})
            before=dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':old}).mappings().one())
            preferences=dict(db.execute(text('SELECT * FROM collection_settings WHERE id=1')).mappings().one())
        command.upgrade(config,'head')
        with engine.begin() as db:
            actual=dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':old}).mappings().one())
            assert actual.pop('comic_details')=={} and actual==before
            settings=dict(db.execute(text('SELECT * FROM collection_settings WHERE id=1')).mappings().one())
            assert settings.pop('comics_enabled') is False
            assert settings.pop('comic_fields')==['issue_number','publisher','edition','notes'] and settings==preferences
            db.execute(text("INSERT INTO owned_copies(id,provisional_title,collection_type,comic_details) VALUES (:id,'Example series','comic',jsonb_build_object('issue_number','001½','publisher','Example Press'))"),{'id':comic})
        with pytest.raises(RuntimeError,match='Refusing Comics downgrade'):command.downgrade(config,'0006_records_setup')
        with engine.begin() as db:
            assert db.scalar(text('SELECT version_num FROM alembic_version'))=='0007_comics'
            assert db.scalar(text("SELECT comic_details->>'issue_number' FROM owned_copies WHERE id=:id"),{'id':comic})=='001½'
            db.execute(text("UPDATE owned_copies SET collection_type='other',comic_details='{}' WHERE id=:id"),{'id':comic})
            db.execute(text("INSERT INTO copy_detail_events(id,owned_copy_id,before_title,after_title,before_collection_type,after_collection_type,before_comic_details,after_comic_details,identification_revision,before_revision,after_revision) VALUES (:event,:id,'Example series','Example series','comic','other',jsonb_build_object('publisher','Example Press'),'{}',0,0,1)"),{'event':event,'id':comic})
        with pytest.raises(RuntimeError,match='Refusing Comics downgrade'):command.downgrade(config,'0006_records_setup')
        with engine.begin() as db:
            db.execute(text('DELETE FROM copy_detail_events WHERE id=:id'),{'id':event})
            db.execute(text('DELETE FROM owned_copies WHERE id=:id'),{'id':comic})
            db.execute(text('UPDATE collection_settings SET comics_enabled=true WHERE id=1'))
        with pytest.raises(RuntimeError,match='Refusing Comics downgrade'):command.downgrade(config,'0006_records_setup')
        with engine.begin() as db:db.execute(text('UPDATE collection_settings SET comics_enabled=false WHERE id=1'))
        command.downgrade(config,'0006_records_setup')
        with engine.connect() as db:
            assert dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':old}).mappings().one())==before
        command.upgrade(config,'head')
    finally:
        command.upgrade(config,'head')
        with engine.begin() as db:
            db.execute(text('DELETE FROM copy_detail_events WHERE owned_copy_id IN (:old,:comic)'),{'old':old,'comic':comic})
            db.execute(text('DELETE FROM owned_copies WHERE id IN (:old,:comic)'),{'old':old,'comic':comic})
            db.execute(text('UPDATE collection_settings SET comics_enabled=false WHERE id=1'))
        engine.dispose()
