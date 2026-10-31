"""Records preferences and copy observations are durable, private and independent."""
import os
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_copy_details import context, edit
from relicrat.copy_details import save_details, DetailError

URL=os.getenv('TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='TEST_DATABASE_URL not configured')
SETTINGS='/api/v1/collection-settings'


@pytest.fixture(autouse=True)
def preferences():
    if not URL:
        yield;return
    engine=create_engine(URL)
    def reset():
        with engine.begin() as db:
            db.execute(text("UPDATE collection_settings SET status='not_started',records_enabled=false,default_type='other',record_fields='[\"artist\",\"format\",\"edition\",\"notes\"]',revision=0 WHERE id=1"))
    reset()
    yield
    reset();engine.dispose()


def configure(api, **values):
    old=api.get(SETTINGS).json()
    return api.post(SETTINGS,json={**{k:v for k,v in old.items() if k!='revision'},'expected_revision':old['revision'],**values})


def test_preferences_skip_configure_noop_stale_and_hidden_values(context):
    api,engine,create=context
    first=api.get(SETTINGS).json();assert first['status']=='not_started' and first['default_type']=='other'
    assert configure(api,status='skipped').json()['revision']==1
    record=create(title='Example album',collection_type='record',record_details={'artist':'Example band','format':'Vinyl'})
    result=configure(api,status='configured',records_enabled=True,default_type='record',record_fields=['artist','format'])
    assert result.status_code==200 and result.json()['revision']==2
    assert configure(api).json()==result.json()
    assert configure(api,expected_revision=0,record_fields=[]).status_code==409
    assert configure(api,record_fields=[]).status_code==200
    assert api.get('/api/v1/inventory/'+record['id']).json()==record
    assert record['id'] in {row['id'] for row in api.get('/api/v1/inventory',params={'q':'Example band'}).json()}
    # Other clients see the same server preferences, not a local browser setting.
    with engine.connect() as db:
        assert db.scalar(text('SELECT revision FROM collection_settings WHERE id=1'))==3
    assert configure(api,records_enabled=False,default_type='other').status_code==200
    assert api.get('/api/v1/inventory/'+record['id']).json()==record
    api.headers.pop('Authorization');assert api.get(SETTINGS).status_code==401


@pytest.mark.parametrize('values',[{'record_fields':['price']},{'record_fields':['artist','artist']},{'record_fields':['artist']*5},{'records_enabled':False,'default_type':'record'},{'records_enabled':'true'},{'status':'finished'},{'expected_revision':True},{'unexpected':1}])
def test_invalid_preferences_never_write(context,values):
    api,_,_=context;before=api.get(SETTINGS).json()
    assert configure(api,**values).status_code==422
    assert api.get(SETTINGS).json()==before


def test_record_intake_edit_history_search_and_old_client_preservation(context):
    api,engine,create=context
    old=create();assert old['collection_type']=='other' and old['record_details']=={}
    record=create(title='Example album',collection_type='record',record_details={'artist':'  Example % band_  ','format':' Vinyl '},edition_label='Blue pressing')
    assert record['record_details']=={'artist':'Example % band_','format':'Vinyl'}
    assert record['catalog_item_id'] is None and record['release_id'] is None
    plain=create(title='Title alone',collection_type='record');assert plain['record_details']=={}
    assert record['id'] in {row['id'] for row in api.get('/api/v1/inventory',params={'q':'% band_'}).json()}
    assert plain['id'] not in {row['id'] for row in api.get('/api/v1/inventory',params={'q':'% band_'}).json()}
    edited=edit(api,record,title='Corrected album',record_details={'artist':'Another artist','format':''}).json()
    assert edited['record_details']=={'artist':'Another artist'}
    assert edited['created_at']==record['created_at'] and edited['id']==record['id']
    history=api.get('/api/v1/inventory/'+record['id']+'/detail-history').json()
    assert history[0]['before_record_details']==record['record_details']
    assert history[0]['after_record_details']==edited['record_details']
    legacy=edit(api,edited,title='Old client edits title').json()
    assert legacy['record_details']==edited['record_details'] and legacy['collection_type']=='record'
    generic=edit(api,legacy,collection_type='other').json()
    assert generic['record_details']==edited['record_details'],'Changing type must not silently clear observations'
    assert edit(api,record,record_details={}).status_code==409
    assert edit(api,generic,record_details={}).json()['record_details']=={}


@pytest.mark.parametrize('values',[{'collection_type':'comic'},{'record_details':{'artist':'x'*501}},{'record_details':{'format':'x'*101}},{'record_details':{'artist':'bad\x00value'}},{'record_details':{'price':10}},{'record_details':{'artist':3}},{'record_details':None}])
def test_invalid_record_details_never_write(context,values):
    api,_,create=context;copy=create()
    assert edit(api,copy,**values).status_code==422
    assert api.get('/api/v1/inventory/'+copy['id']).json()==copy
    assert api.get('/api/v1/inventory/'+copy['id']+'/detail-history').json()==[]


def test_record_database_constraints_and_concurrent_edits(context):
    api,engine,create=context;copy=create(collection_type='record');cid=copy['id']
    for statement in ["UPDATE owned_copies SET collection_type='comic' WHERE id=:id", "UPDATE owned_copies SET record_details='{\"unknown\":\"bad\"}' WHERE id=:id", "UPDATE owned_copies SET record_details='{\"artist\": 12}' WHERE id=:id", "UPDATE owned_copies SET record_details='{\"artist\": null}' WHERE id=:id", "UPDATE collection_settings SET default_type='record' WHERE id=1", "UPDATE collection_settings SET record_fields='[\"price\"]' WHERE id=1"]:
        with pytest.raises(DBAPIError),engine.begin() as db:db.execute(text(statement),{'id':cid})
    barrier=Barrier(2)
    def writer(artist):
        with Session(engine,expire_on_commit=False) as db:
            barrier.wait()
            try:save_details(db,UUID(cid),copy['title'],None,0,0,record_details={'artist':artist});return 200
            except DetailError as error:return error.status_code
    with ThreadPoolExecutor(2) as pool:assert sorted(pool.map(writer,['First','Second']))==[200,409]
    assert len(api.get('/api/v1/inventory/'+cid+'/detail-history').json())==1


def test_preferences_concurrency_and_transaction_failure(context):
    from sqlalchemy import event
    from relicrat.collection_settings import SaveSettings,save_settings
    from fastapi import HTTPException
    api,engine,_=context
    barrier=Barrier(2)
    def writer(status):
        with Session(engine,expire_on_commit=False) as db:
            payload=SaveSettings(status=status,records_enabled=True,default_type='record',record_fields=['artist'],expected_revision=0)
            barrier.wait()
            try:save_settings(payload,db);return 200
            except HTTPException as problem:return problem.status_code
    with ThreadPoolExecutor(2) as pool:assert sorted(pool.map(writer,['configured','skipped']))==[200,409]
    before=api.get(SETTINGS).json()
    def fail(conn,cursor,statement,parameters,context,many):
        if statement.startswith('UPDATE collection_settings'):raise RuntimeError('Injected preference update failure')
    event.listen(engine,'before_cursor_execute',fail)
    try:
        with pytest.raises(RuntimeError),Session(engine) as db:
            save_settings(SaveSettings(status='configured',records_enabled=True,default_type='record',record_fields=[],expected_revision=before['revision']),db)
    finally:event.remove(engine,'before_cursor_execute',fail)
    assert api.get(SETTINGS).json()==before


def test_type_definitions_are_owner_only_read_only_and_do_not_change_preferences(context):
    api,_,_=context
    before=api.get(SETTINGS).json()
    response=api.get(SETTINGS+'/types')
    assert response.status_code==200
    definitions=response.json()
    assert set(definitions)=={'other','record'}
    assert definitions['record']['title']['label']=='Album title'
    assert api.post(SETTINGS+'/types',json=definitions).status_code==405
    assert api.get(SETTINGS).json()==before
    api.headers.pop('Authorization')
    assert api.get(SETTINGS+'/types').status_code==401
