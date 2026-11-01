"""Additive upgrade preserves old rows; downgrade losses remain explicit."""
import os
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine,text

URL=os.getenv('TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='TEST_DATABASE_URL not configured')


def test_records_upgrade_and_disposable_downgrade():
    engine=create_engine(URL);config=Config('alembic.ini');cid=uuid4();event_id=uuid4();new_event=uuid4()
    command.downgrade(config,'0005_copy_details')
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO owned_copies(id,provisional_title,details_revision) VALUES (:id,'Old album',1)"),{'id':cid})
            db.execute(text("INSERT INTO copy_detail_events(id,owned_copy_id,before_title,after_title,identification_revision,before_revision,after_revision) VALUES (:event,:id,'Earlier album','Old album',0,0,1)"),{'event':event_id,'id':cid})
            before=dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one())
            history=dict(db.execute(text('SELECT * FROM copy_detail_events WHERE id=:id'),{'id':event_id}).mappings().one())
        command.upgrade(config,'head')
        with engine.begin() as db:
            after=dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one())
            assert after.pop('barcode')=={}
            assert after.pop('comic_details')=={}
            assert after.pop('collection_type')=='other' and after.pop('record_details')=={} and after==before
            upgraded=dict(db.execute(text('SELECT * FROM copy_detail_events WHERE id=:id'),{'id':event_id}).mappings().one())
            for key in ['before_barcode','after_barcode','before_collection_type','after_collection_type','before_record_details','after_record_details','before_comic_details','after_comic_details']:assert upgraded.pop(key) is None
            assert upgraded==history
            assert db.scalar(text("SELECT status FROM collection_settings WHERE id=1"))=='not_started'
            db.execute(text("UPDATE owned_copies SET collection_type='record',record_details=jsonb_build_object('artist','Synthetic artist'),details_revision=2 WHERE id=:id"),{'id':cid})
            db.execute(text("INSERT INTO copy_detail_events(id,owned_copy_id,before_title,after_title,before_collection_type,after_collection_type,before_record_details,after_record_details,identification_revision,before_revision,after_revision) VALUES (:event,:id,'Old album','Old album','other','record','{}',jsonb_build_object('artist','Synthetic artist'),0,1,2)"),{'event':new_event,'id':cid})
            current=dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one());current.pop('barcode');current.pop('collection_type');current.pop('record_details');current.pop('comic_details')
        command.downgrade(config,'0005_copy_details')
        with engine.connect() as db:
            assert db.scalar(text("SELECT to_regclass('collection_settings')")) is None
            assert dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one())==current
            assert dict(db.execute(text('SELECT * FROM copy_detail_events WHERE id=:id'),{'id':event_id}).mappings().one())==history
            assert db.scalar(text('SELECT count(*) FROM copy_detail_events WHERE id=:id'),{'id':new_event})==0
        command.upgrade(config,'head')
    finally:
        command.upgrade(config,'head')
        with engine.begin() as db:
            db.execute(text('DELETE FROM copy_detail_events WHERE owned_copy_id=:id'),{'id':cid})
            db.execute(text('DELETE FROM owned_copies WHERE id=:id'),{'id':cid})
        engine.dispose()
