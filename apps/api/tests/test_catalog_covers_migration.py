import os
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine,text
from sqlalchemy.exc import IntegrityError

@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'),reason='TEST_DATABASE_URL not configured')
def test_cover_upgrade_preserves_photos_constraints_and_refuses_lossy_downgrade():
    engine=create_engine(os.environ['TEST_DATABASE_URL']);config=Config('alembic.ini');cid=uuid4();photo=uuid4();cover=uuid4()
    command.downgrade(config,'0011_copy_barcodes')
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO owned_copies(id,provisional_title) VALUES (:id,'Synthetic cover migration')"),{'id':cid})
            db.execute(text("INSERT INTO media_assets(id,owned_copy_id,storage_key,content_type,byte_size) VALUES (:id,:cid,'synthetic/migration.jpg','image/jpeg',8)"),{'id':photo,'cid':cid})
            before=dict(db.execute(text('SELECT * FROM media_assets WHERE id=:id'),{'id':photo}).mappings().one())
        command.upgrade(config,'head')
        with engine.begin() as db:
            actual=dict(db.execute(text('SELECT * FROM media_assets WHERE id=:id'),{'id':photo}).mappings().one())
            for key in ['source_provider','source_id','source_url']:assert actual.pop(key) is None
            assert actual==before
        with pytest.raises(IntegrityError),engine.begin() as db:
            db.execute(text("INSERT INTO media_assets(id,owned_copy_id,storage_key,content_type,byte_size,role) VALUES (:id,:cid,'synthetic/invalid.jpg','image/jpeg',8,'catalog_cover')"),{'id':cover,'cid':cid})
        with engine.begin() as db:
            db.execute(text("INSERT INTO media_assets(id,owned_copy_id,storage_key,content_type,byte_size,role,source_provider,source_id,source_url) VALUES (:id,:cid,'synthetic/cover.jpg','image/jpeg',8,'catalog_cover','synthetic','edition-1','https://catalog.invalid/edition-1')"),{'id':cover,'cid':cid})
        with pytest.raises(IntegrityError),engine.begin() as db:
            db.execute(text("INSERT INTO media_assets(id,owned_copy_id,storage_key,content_type,byte_size,role,source_provider,source_id,source_url) VALUES (:id,:cid,'synthetic/duplicate.jpg','image/jpeg',8,'catalog_cover','synthetic','edition-1','https://catalog.invalid/edition-1')"),{'id':uuid4(),'cid':cid})
        with pytest.raises(RuntimeError,match='Refusing catalog cover downgrade'):command.downgrade(config,'0011_copy_barcodes')
        with engine.begin() as db:db.execute(text('DELETE FROM media_assets WHERE id=:id'),{'id':cover})
        command.downgrade(config,'0011_copy_barcodes')
        with engine.begin() as db:assert dict(db.execute(text('SELECT * FROM media_assets WHERE id=:id'),{'id':photo}).mappings().one())==before
    finally:
        command.upgrade(config,'head')
        with engine.begin() as db:
            db.execute(text('DELETE FROM media_assets WHERE owned_copy_id=:id'),{'id':cid});db.execute(text('DELETE FROM owned_copies WHERE id=:id'),{'id':cid})
        engine.dispose()
