"""Physical-copy edits run as real PostgreSQL transactions, separate from catalog."""
import io
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, delete, event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auth_helpers import sign_in
from relicrat.copy_details import DetailError, save_details
from relicrat.database import get_db
from relicrat.main import app
from relicrat.models import Category, CatalogItem, CopyDetailEvent, MediaAsset, OwnedCopy, Release

URL = os.getenv('TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='TEST_DATABASE_URL not configured')
BASE = '/api/v1/inventory'


@pytest.fixture
def context(tmp_path, monkeypatch):
    monkeypatch.setenv('MEDIA_ROOT', str(tmp_path))
    engine = create_engine(URL)
    ids = []
    def override():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as api:
            sign_in(api)
            def create(**values):
                response = api.post(BASE, json={'title': 'Harbor Lights - blue vinyl', **values})
                assert response.status_code == 201, response.text
                record = response.json(); ids.append(UUID(record['id'])); return record
            yield api, engine, create
    finally:
        app.dependency_overrides.pop(get_db, None)
        with engine.begin() as connection:
            for model in [CopyDetailEvent, MediaAsset]:
                connection.execute(delete(model).where(model.owned_copy_id.in_(ids)))
            connection.execute(delete(OwnedCopy).where(OwnedCopy.id.in_(ids)))
        engine.dispose()


def edit(api, copy, **values):
    return api.post(f"{BASE}/{copy['id']}/details", json={
        'title': copy['title'], 'edition_label': copy['edition_label'],
        'expected_details_revision': copy['details_revision'],
        'expected_identification_revision': copy['identification_revision'], **values})


def test_atomic_labels_noop_literal_search_and_no_catalog_changes(context):
    api, engine, create = context
    original = create(description='Synthetic original notes')
    with engine.connect() as connection:
        catalog_before = {table: connection.scalar(text(f'SELECT count(*) FROM {table}')) for table in ['categories', 'catalog_items', 'releases']}
    first = edit(api, original, title='  Harbor Lights  ', edition_label='  Blue % vinyl_  ')
    assert first.status_code == 200, first.text
    saved = first.json()
    assert saved['title'] == 'Harbor Lights' and saved['edition_label'] == 'Blue % vinyl_'
    for key in ['id', 'created_at', 'description', 'catalog_item_id', 'release_id', 'identification_revision', 'storage_location_id', 'storage_revision', 'ownership_status']:
        assert saved[key] == original[key]
    assert saved['details_revision'] == 1
    assert edit(api, saved).json() == saved
    assert edit(api, original, title='Stale change').status_code == 409
    history = api.get(f"{BASE}/{saved['id']}/detail-history").json()
    assert len(history) == 1
    assert history[0]['before_title'] == original['title'] and history[0]['after_title'] == saved['title']
    assert history[0]['before_edition_label'] is None and history[0]['after_edition_label'] == saved['edition_label']
    assert history[0]['identification_revision'] == 0
    assert api.get(f"{BASE}/{saved['id']}/detail-history?limit=0").status_code == 422
    assert api.get(f"{BASE}/{saved['id']}/detail-history?offset=-1").status_code == 422
    other = create(title='Another record')
    result = api.get(BASE, params={'q': '% vinyl_'}).json()
    assert saved['id'] in {copy['id'] for copy in result} and other['id'] not in {copy['id'] for copy in result}
    with engine.connect() as connection:
        assert {table: connection.scalar(text(f'SELECT count(*) FROM {table}')) for table in catalog_before} == catalog_before


@pytest.mark.parametrize('value', [{'title':'x'*501}, {'title':'bad\x00title'}, {'edition_label':'x'*501}, {'edition_label':'bad\x00edition'}, {'expected_details_revision':True}, {'expected_details_revision':-1}, {'expected_details_revision':1.5}, {'expected_identification_revision':False}, {'expected_identification_revision':2147483647}, {'unexpected':True}])
def test_edit_validation_never_writes(context, value):
    api, _, create = context; original = create()
    assert edit(api, original, **value).status_code == 422
    assert api.get(f"{BASE}/{original['id']}").json() == original
    assert api.get(f"{BASE}/{original['id']}/detail-history").json() == []


def test_meaningful_copy_and_exact_photo_survive(context):
    api, _, create = context; original = create()
    assert edit(api, original, title=' ').status_code == 422
    output = io.BytesIO(); Image.new('RGB',(2,2),(22,44,66)).save(output,'PNG'); data=output.getvalue()
    photo = api.post(f"{BASE}/{original['id']}/photos", files={'file':('synthetic.png',data,'image/png')}).json()
    response = edit(api, original, title='', edition_label='')
    assert response.status_code == 200, response.text
    saved=response.json(); assert saved['title'] is None and saved['edition_label']==''
    assert saved['id']==original['id'] and saved['created_at']==original['created_at']
    assert api.get(f"{BASE}/{original['id']}/photos/{photo['id']}").content==data
    notes = create(description='A useful handwritten label')
    assert edit(api, notes, title=None).status_code==200


def test_manual_label_retains_shared_match_and_stale_match_is_rejected(context):
    api, engine, create=context; copy=create()
    category_id,item_id,release_id=uuid4(),uuid4(),uuid4()
    try:
        with Session(engine) as db:
            db.add(Category(id=category_id,slug=uuid4().hex,name='Synthetic albums'));db.flush()
            db.add(CatalogItem(id=item_id,category_id=category_id,identity_key=uuid4().hex,canonical_name='Shared Harbor Lights'));db.flush()
            db.add(Release(id=release_id,catalog_item_id=item_id,release_key=uuid4().hex,name='Blue pressing'));db.flush()
            record=db.get(OwnedCopy,UUID(copy['id']));record.catalog_item_id=item_id;record.release_id=release_id;record.identification_revision=1;record.identification_status='identified';record.ownership_status='sold';db.commit()
        assert edit(api,copy,title='Read before matching').status_code==409
        copy=api.get(f"{BASE}/{copy['id']}").json()
        response=edit(api,copy,title='My album',edition_label='Hand-numbered blue vinyl')
        assert response.status_code==200,response.text
        saved=response.json()
        for key in ['catalog_item_id','release_id','identification_revision','ownership_status']:assert saved[key]==copy[key]
        with Session(engine) as db:assert db.get(Release,release_id).name=='Blue pressing'
        assert api.get(f"{BASE}/{copy['id']}/detail-history").json()[0]['identification_revision']==1
        # Explicit blank differs from NULL: unknown label vs following a linked release.
        blank=edit(api,saved,edition_label='').json();assert blank['edition_label']=='' and blank['release_id']==str(release_id)
        restored=edit(api,blank,edition_label=None).json();assert restored['edition_label'] is None
    finally:
        with engine.begin() as connection:
            connection.execute(text('UPDATE owned_copies SET release_id=NULL,catalog_item_id=NULL WHERE id=:id'),{'id':copy['id']})
            connection.execute(delete(Release).where(Release.id==release_id));connection.execute(delete(CatalogItem).where(CatalogItem.id==item_id));connection.execute(delete(Category).where(Category.id==category_id))


def test_concurrent_edits_one_wins_and_commit_failure_rolls_back(context):
    api, engine, create=context; copy=create(); gate=Barrier(2)
    def attempt(title):
        with Session(engine,expire_on_commit=False) as db:
            gate.wait()
            try:return save_details(db,UUID(copy['id']),title,'Blue vinyl',0,0).details_revision
            except DetailError as error:return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(attempt,['First editor','Second editor']))==[1,409]
    saved=api.get(f"{BASE}/{copy['id']}").json()
    assert len(api.get(f"{BASE}/{copy['id']}/detail-history").json())==1
    def fail(connection,cursor,statement,parameters,context,executemany):
        if statement.startswith('INSERT INTO copy_detail_events'):raise RuntimeError('Synthetic history failure')
    event.listen(engine,'before_cursor_execute',fail)
    try:
        with Session(engine) as db,pytest.raises(RuntimeError,match='Synthetic history failure'):
            save_details(db,UUID(copy['id']),'Must roll back','Copper',1,0)
    finally:event.remove(engine,'before_cursor_execute',fail)
    assert api.get(f"{BASE}/{copy['id']}").json()==saved
    assert len(api.get(f"{BASE}/{copy['id']}/detail-history").json())==1


def test_missing_deleted_and_database_constraints(context):
    api, engine, create=context; copy=create()
    assert api.post(f'{BASE}/{uuid4()}/details',json={'title':'Missing','edition_label':None,'expected_details_revision':0,'expected_identification_revision':0}).status_code==404
    with engine.begin() as connection:connection.execute(text('UPDATE owned_copies SET deleted_at=now() WHERE id=:id'),{'id':copy['id']})
    assert edit(api,copy,title='Deleted').status_code==404
    assert api.get(f"{BASE}/{copy['id']}/detail-history").status_code==404
    with pytest.raises(DBAPIError),engine.begin() as connection:connection.execute(text('UPDATE owned_copies SET details_revision=-1 WHERE id=:id'),{'id':copy['id']})
    values={'id':uuid4(),'copy':copy['id']}
    with pytest.raises(DBAPIError),engine.begin() as connection:
        connection.execute(text("INSERT INTO copy_detail_events (id,owned_copy_id,before_title,after_title,identification_revision,before_revision,after_revision) VALUES (:id,:copy,'Before','After',0,0,2)"),values)

    # The database also rejects duplicate audit revisions independently of the service.
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO copy_detail_events (id,owned_copy_id,before_title,after_title,identification_revision,before_revision,after_revision) VALUES (:id,:copy,'Before','After',0,0,1)"),{'id':uuid4(),'copy':copy['id']})
    with pytest.raises(DBAPIError),engine.begin() as connection:
        connection.execute(text("INSERT INTO copy_detail_events (id,owned_copy_id,before_title,after_title,identification_revision,before_revision,after_revision) VALUES (:id,:copy,'After','Another',0,0,1)"),{'id':uuid4(),'copy':copy['id']})
