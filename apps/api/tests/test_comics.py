"""Comics are bounded observations on a physical copy, with atomic retained edits."""
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_copy_details import context, edit
from relicrat.copy_details import save_details, DetailError

BASE='/api/v1/inventory'
SETTINGS='/api/v1/collection-settings'


def test_create_edit_search_legacy_omission_and_no_identity_changes(context):
    api,engine,create=context
    copy=create(title='Batman',collection_type='comic',comic_details={'issue_number':' 001½ ','publisher':' Example Press '},edition_label='Cover B')
    assert copy['comic_details']=={'issue_number':'001½','publisher':'Example Press'}
    assert copy['catalog_item_id'] is None and copy['release_id'] is None
    assert api.get(BASE,params={'q':'001½'}).json()[0]['id']==copy['id']
    assert api.get(BASE,params={'q':'Example Press'}).json()[0]['id']==copy['id']
    updated=edit(api,copy,comic_details={'issue_number':'Annual 1','publisher':'New Press'}).json()
    assert updated['id']==copy['id'] and updated['details_revision']==1
    assert edit(api,updated).json()==updated  # Old clients omit new metadata and type.
    changed=edit(api,updated,collection_type='other').json()
    assert changed['comic_details']==updated['comic_details']
    history=api.get(BASE+'/'+copy['id']+'/detail-history').json()
    assert history[0]['before_comic_details']==copy['comic_details']
    assert history[0]['after_comic_details']==updated['comic_details']
    assert edit(api,copy,comic_details={}).status_code==409
    assert create(title='Only series',collection_type='comic')['comic_details']=={}


@pytest.mark.parametrize('payload',[
 {'comic_details':{'unknown':'x'}}, {'comic_details':{'issue_number':423}},
 {'comic_details':{'issue_number':'x'*101}}, {'comic_details':{'publisher':'x'*251}},
 {'comic_details':{'publisher':'bad\x00'}}, {'collection_type':'other','comic_details':{'publisher':'Press'}},
 {'collection_type':'comic','record_details':{'artist':'Wrong kind'}},
])
def test_invalid_comic_observations_are_rejected(context,payload):
    api,_,_=context
    response=api.post(BASE,json={'title':'Example series','collection_type':'comic',**payload})
    assert response.status_code==422


def test_comic_database_constraints(context):
    _,engine,create=context
    copy=create(title='Example series',collection_type='comic')
    for expression in ["jsonb_build_object('unknown','x')", "jsonb_build_object('issue_number',42)", "jsonb_build_object('publisher',null)", "jsonb_build_object('publisher',repeat('x',251))", "'[]'::jsonb"]:
        with engine.connect() as db:
            with pytest.raises(DBAPIError):db.execute(text('UPDATE owned_copies SET comic_details='+expression+' WHERE id=:id'),{'id':UUID(copy['id'])})
            db.rollback()
    for expression in ("default_type='comic'", "comic_fields=jsonb_build_array('price')", "comic_fields=to_jsonb('bad'::text)"):
        with engine.connect() as db:
            with pytest.raises(DBAPIError):db.execute(text('UPDATE collection_settings SET '+expression+' WHERE id=1'))
            db.rollback()


def test_comic_settings_legacy_omission_and_suggestions(context):
    api,engine,create=context
    before=api.get(SETTINGS).json()
    try:
        result=api.post(SETTINGS,json={**{k:v for k,v in before.items() if k!='revision'},'status':'configured','comics_enabled':True,'default_type':'comic','comic_fields':['issue_number','publisher'],'expected_revision':before['revision']})
        assert result.status_code==200,result.text
        current=result.json()
        assert api.post(SETTINGS,json={**{k:v for k,v in current.items() if k!='revision'},'comic_fields':['publisher','publisher'],'expected_revision':current['revision']}).status_code==422
        assert api.get(SETTINGS).json()==current
        legacy={k:v for k,v in current.items() if k not in ('revision','comics_enabled','comic_fields')}
        assert api.post(SETTINGS,json={**legacy,'expected_revision':current['revision']}).json()==current
        assert api.post(SETTINGS,json={**legacy,'comics_enabled':False,'expected_revision':current['revision']}).status_code==422
        for name in ('Example Press','example press','A%_Press','AxyPress'):
            create(title='Example series',collection_type='comic',comic_details={'publisher':name})
        assert api.get(SETTINGS+'/publisher-suggestions',params={'q':'EXAMPLE'}).json()==['Example Press']
        assert api.get(SETTINGS+'/publisher-suggestions',params={'q':'A%_'}).json()==['A%_Press']
        assert api.get(SETTINGS+'/publisher-suggestions',params={'q':'x'*251}).status_code==422
        api.headers.pop('Authorization');assert api.get(SETTINGS+'/publisher-suggestions').status_code==401
    finally:
        with engine.begin() as db:
            db.execute(text("UPDATE collection_settings SET comics_enabled=false,default_type='other',comic_fields='[\"issue_number\",\"publisher\",\"edition\",\"notes\"]'::jsonb WHERE id=1"))


def test_concurrent_comic_edits_share_the_existing_copy_lock(context):
    _,engine,create=context
    copy=create(title='Example series',collection_type='comic');gate=Barrier(2)
    def save(issue):
        with Session(engine,expire_on_commit=False) as db:
            gate.wait()
            try:
                save_details(db,UUID(copy['id']),copy['title'],None,0,0,comic_details={'issue_number':issue})
                return 200
            except DetailError as error:return error.status_code
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(save,['1','2']))==[200,409]
