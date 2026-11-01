"""New labels/history upgrade existing data; downgrade loss is explicit and bounded."""
import os
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine,text

URL=os.getenv('TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='TEST_DATABASE_URL not configured')


def test_copy_detail_upgrade_downgrade_preserves_legacy_columns():
    engine=create_engine(URL);config=Config('alembic.ini');cid=uuid4()
    command.downgrade(config,'0004_owner_access')
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO owned_copies(id,provisional_title) VALUES (:id,'Legacy physical copy')"),{'id':cid})
            before=dict(conn.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one())
        command.upgrade(config,'head')
        with engine.begin() as conn:
            after=dict(conn.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one())
            assert after.pop('barcode')=={}
            assert after.pop('comic_details')=={}
            assert after.pop('movie_details')=={}
            assert after.pop('collection_type')=='other' and after.pop('record_details')=={}
            assert after.pop('edition_label') is None and after.pop('details_revision')==0 and after==before
            conn.execute(text("UPDATE owned_copies SET provisional_title='Edited physical copy',edition_label='Blue vinyl',details_revision=1 WHERE id=:id"),{'id':cid})
            conn.execute(text("INSERT INTO copy_detail_events(id,owned_copy_id,before_title,after_title,after_edition_label,identification_revision,before_revision,after_revision) VALUES (:event,:id,'Legacy physical copy','Edited physical copy','Blue vinyl',0,0,1)"),{'event':uuid4(),'id':cid})
            current=dict(conn.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one());current.pop('barcode');current.pop('collection_type');current.pop('record_details');current.pop('comic_details');current.pop('movie_details');current.pop('edition_label');current.pop('details_revision')
        command.downgrade(config,'0004_owner_access')
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT to_regclass('copy_detail_events')")) is None
            assert dict(conn.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one())==current
        command.upgrade(config,'head')
        with engine.connect() as conn:
            assert conn.scalar(text('SELECT count(*) FROM copy_detail_events'))==0
            assert conn.scalar(text('SELECT details_revision FROM owned_copies WHERE id=:id'),{'id':cid})==0
    finally:
        command.upgrade(config,'head')
        with engine.begin() as conn:
            conn.execute(text('DELETE FROM copy_detail_events WHERE owned_copy_id=:id'),{'id':cid})
            conn.execute(text('DELETE FROM owned_copies WHERE id=:id'),{'id':cid})
        engine.dispose()
