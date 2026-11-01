"""Movie migration preserves older rows and refuses to discard new evidence."""
import os,uuid
import pytest
from sqlalchemy import create_engine,text
from alembic import command
from alembic.config import Config

@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'),reason='TEST_DATABASE_URL not configured')
def test_movie_migration_preserves_prior_rows_and_refuses_observations_history_preferences_and_imports():
    engine=create_engine(os.environ['TEST_DATABASE_URL']);config=Config('alembic.ini');old=uuid.uuid4();movie=uuid.uuid4();event=uuid.uuid4();batch=uuid.uuid4()
    command.downgrade(config,'0012_catalog_covers')
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO owned_copies(id,provisional_title,collection_type,record_details) VALUES (:id,'Synthetic prior album','record','{\"artist\":\"Synthetic artist\"}')"),{'id':old})
            before=dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':old}).mappings().one())
            settings=dict(db.execute(text('SELECT * FROM collection_settings WHERE id=1')).mappings().one())
        command.upgrade(config,'0013_movies')
        with engine.begin() as db:
            row=dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':old}).mappings().one());assert row.pop('movie_details')=={};assert row==before
            current=dict(db.execute(text('SELECT * FROM collection_settings WHERE id=1')).mappings().one());assert current.pop('movies_enabled') is False;assert current.pop('movie_fields')==['media_format','studio','edition','notes'];assert current==settings
            db.execute(text("INSERT INTO owned_copies(id,provisional_title,collection_type,movie_details) VALUES (:id,'Synthetic movie','movie','{\"studio\":\"Example studio\"}')"),{'id':movie})
        with pytest.raises(RuntimeError,match='Refusing Movies downgrade'):command.downgrade(config,'0012_catalog_covers')
        with engine.begin() as db:
            db.execute(text("UPDATE owned_copies SET collection_type='other',movie_details='{}' WHERE id=:id"),{'id':movie})
            db.execute(text("INSERT INTO copy_detail_events(id,owned_copy_id,before_title,after_title,before_movie_details,after_movie_details,identification_revision,before_revision,after_revision) VALUES (:event,:id,'Synthetic movie','Synthetic movie','{\"studio\":\"Example studio\"}','{}',0,0,1)"),{'event':event,'id':movie})
        with pytest.raises(RuntimeError,match='Refusing Movies downgrade'):command.downgrade(config,'0012_catalog_covers')
        with engine.begin() as db:
            db.execute(text('DELETE FROM copy_detail_events WHERE id=:id'),{'id':event});db.execute(text("UPDATE collection_settings SET movie_fields='[\"studio\"]' WHERE id=1"))
        with pytest.raises(RuntimeError,match='Refusing Movies downgrade'):command.downgrade(config,'0012_catalog_covers')
        with engine.begin() as db:
            db.execute(text("UPDATE collection_settings SET movie_fields='[\"media_format\",\"studio\",\"edition\",\"notes\"]' WHERE id=1"))
            db.execute(text("INSERT INTO import_batches(id,source,sha256,parser_version,row_count,copy_count) VALUES (:id,'bluray',:hash,1,1,1)"),{'id':batch,'hash':'f'*64})
        with pytest.raises(RuntimeError,match='Refusing Movies downgrade'):command.downgrade(config,'0012_catalog_covers')
        with engine.begin() as db:db.execute(text('DELETE FROM import_batches WHERE id=:id'),{'id':batch})
        command.downgrade(config,'0012_catalog_covers')
        with engine.connect() as db:assert dict(db.execute(text('SELECT * FROM owned_copies WHERE id=:id'),{'id':old}).mappings().one())==before
    finally:
        command.upgrade(config,'head')
        with engine.begin() as db:
            db.execute(text('DELETE FROM copy_detail_events WHERE id=:id'),{'id':event});db.execute(text('DELETE FROM import_batches WHERE id=:id'),{'id':batch});db.execute(text('DELETE FROM owned_copies WHERE id IN (:old,:movie)'),{'old':old,'movie':movie})
            db.execute(text("UPDATE collection_settings SET movies_enabled=false,movie_fields='[\"media_format\",\"studio\",\"edition\",\"notes\"]' WHERE id=1"))
        engine.dispose()
