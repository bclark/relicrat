"""Additive upgrade and refusal to discard current or historical observations."""
import os
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine,text

@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'),reason='TEST_DATABASE_URL not configured')
def test_barcode_upgrade_preserves_rows_and_downgrade_preserves_evidence():
    engine=create_engine(os.environ['TEST_DATABASE_URL']);config=Config('alembic.ini');cid=uuid4();eid=uuid4()
    command.downgrade(config,'0010_brand_default')
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO owned_copies(id,provisional_title) VALUES (:id,'Synthetic migration find')"),{'id':cid})
            before=dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one())
        command.upgrade(config,'head')
        with engine.begin() as db:
            actual=dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one())
            assert actual.pop('barcode')=={} and actual==before
            db.execute(text('UPDATE owned_copies SET barcode=\'{"value":"012345678905","format":"UPC_A"}\' WHERE id=:id'),{'id':cid})
        with pytest.raises(RuntimeError,match='Refusing barcode downgrade'):command.downgrade(config,'0010_brand_default')
        with engine.begin() as db:
            assert db.scalar(text('SELECT version_num FROM alembic_version'))=='0011_copy_barcodes'
            assert db.scalar(text("SELECT barcode->>'value' FROM owned_copies WHERE id=:id"),{'id':cid})=='012345678905'
            db.execute(text("UPDATE owned_copies SET barcode='{}' WHERE id=:id"),{'id':cid})
            db.execute(text('''INSERT INTO copy_detail_events(id,owned_copy_id,before_title,after_title,before_barcode,after_barcode,identification_revision,before_revision,after_revision)
                VALUES (:eid,:id,'Synthetic migration find','Synthetic migration find','{"value":"012345678905","format":"UPC_A"}','{}',0,0,1)'''),{'eid':eid,'id':cid})
        with pytest.raises(RuntimeError,match='Refusing barcode downgrade'):command.downgrade(config,'0010_brand_default')
        with engine.begin() as db:db.execute(text('DELETE FROM copy_detail_events WHERE id=:id'),{'id':eid})
        command.downgrade(config,'0010_brand_default')
        with engine.connect() as db:
            # Direct update timestamps change deliberately; all original data stays.
            actual=dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':cid}).mappings().one())
            assert actual==before
    finally:
        command.upgrade(config,'head')
        with engine.begin() as db:
            db.execute(text('DELETE FROM copy_detail_events WHERE id=:id'),{'id':eid})
            db.execute(text('DELETE FROM owned_copies WHERE id=:id'),{'id':cid})
        engine.dispose()
