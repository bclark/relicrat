"""Typed observations, compatible append-only control revisions and retained legacy data."""
import copy,json,uuid,os
from pathlib import Path
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_inventory_api import client
from test_custom_collections import proposal,activate
pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='TEST_DATABASE_URL not configured')


def typed_proposal():
    value=proposal();value['type_definition']['optional_fields']=[
        {'id':'head','label':'Head Variant','input':'radio','max_length':50,'options':['Soft','Hard']},
        {'id':'packaging','label':'Packaging','input':'select','max_length':50,'options':['Loose','Carded']},
        {'id':'signed','label':'Signed','input':'checkbox','max_length':50},
        {'id':'accessories','label':'Accessories','input':'checkboxes','max_length':50,'options':['Sword','Belt']},
        {'id':'condition','label':'Condition','input':'text','max_length':1000}]
    return value


def add(api,cid,details,**extra):
    return api.post(f'/api/v1/custom-collections/{cid}/copies',json={'request_id':str(uuid.uuid4()),'title':'Synthetic figure','custom_details':details}|extra)


def test_typed_values_and_unknowns_roundtrip_and_history(client):
    api,db=client;c=activate(api,typed_proposal());cid=c['id']
    unknown=add(api,cid,{});assert unknown.status_code==200,unknown.text
    assert unknown.json()['custom_details']=={}
    details={'head':'Soft','packaging':'Loose','signed':False,'accessories':[]}
    result=add(api,cid,details,expected_type_revision=0);assert result.status_code==200,result.text
    assert result.json()['custom_details']==details
    copy=result.json();edit={'title':copy['title'],'edition_label':None,'expected_details_revision':0,'expected_identification_revision':0,'expected_type_revision':0,'custom_details':{'head':'Hard','signed':True,'accessories':['Sword','Belt']}}
    saved=api.post(f"/api/v1/inventory/{copy['id']}/details",json=edit);assert saved.status_code==200,saved.text
    event=api.get(f"/api/v1/inventory/{copy['id']}/detail-history").json()[0]
    assert event['before_custom_details']==details and event['after_custom_details']==edit['custom_details']
    for values in [{'head':'Other'},{'head':False},{'signed':'false'},{'accessories':'Sword'},{'accessories':['Sword','Sword']},{'accessories':['Unknown']}]:
        assert add(api,cid,values).status_code==422
        with pytest.raises(IntegrityError):
            with db.begin_nested():db.execute(text('UPDATE owned_copies SET custom_details=CAST(:details AS jsonb) WHERE id=:id'),{'id':copy['id'],'details':json.dumps(values)})


def test_revision_preserves_copies_and_original_import_and_shared_collections(client):
    api,db=client;raw=proposal();raw['type_definition']['optional_fields']=[{'id':'head','label':'Head Variant','input':'text','max_length':50}]
    c=activate(api,raw);cid=c['id'];copy=add(api,cid,{'head':'Soft'}).json()
    second=copy_json(raw);second['collection']['id']='another-goal';c2=activate(api,second)
    definition=copy_json(raw['type_definition']);definition['optional_fields'][0].update(input='radio',options=['Soft','Hard'])
    payload={'expected_revision':0,'definition':definition}
    preview=api.post(f'/api/v1/custom-collections/{cid}/definition-preview',json=payload);assert preview.status_code==200,preview.text
    assert preview.json()['affected_collections']==2
    saved=api.post(f'/api/v1/custom-collections/{cid}/definition',json=payload);assert saved.status_code==200,saved.text
    assert saved.json()['type_revision']==1
    assert api.get(f"/api/v1/custom-collections/{c2['id']}").json()['type_revision']==1
    assert api.get(f"/api/v1/inventory/{copy['id']}").json()==copy
    assert api.post('/api/v1/custom-collections',json=raw).json()['id']==cid
    assert api.post(f'/api/v1/custom-collections/{cid}/definition',json=payload).status_code==409
    assert add(api,cid,{'head':'Soft'},expected_type_revision=0).status_code==412
    history=api.get(f'/api/v1/custom-collections/{cid}/definition-history').json()
    assert [h['revision'] for h in history]==[1,0] and history[1]['definition']==raw['type_definition']
    with pytest.raises(IntegrityError):
        with db.begin_nested():db.execute(text('UPDATE custom_type_revisions SET definition=definition'))
    with pytest.raises(IntegrityError):
        with db.begin_nested():db.execute(text('INSERT INTO custom_type_revisions(type_id,revision,definition) VALUES (:type,3,CAST(:definition AS jsonb))'),{'type':raw['type_definition']['id'],'definition':json.dumps(definition)})


def copy_json(value):return json.loads(json.dumps(value))


def test_incompatible_revision_rejected_by_service_and_database(client):
    api,db=client;raw=proposal();raw['type_definition']['optional_fields']=[{'id':'head','label':'Head Variant','input':'text','max_length':50}];c=activate(api,raw);cid=c['id']
    copy=add(api,cid,{'head':'Soft head'}).json();definition=copy_json(raw['type_definition']);definition['optional_fields'][0].update(input='radio',options=['Soft','Hard'])
    payload={'expected_revision':0,'definition':definition}
    for route in ['definition-preview','definition']:
        assert api.post(f'/api/v1/custom-collections/{cid}/{route}',json=payload).status_code==422
    with pytest.raises(IntegrityError):
        with db.begin_nested():db.execute(text('INSERT INTO custom_type_revisions(type_id,revision,definition) VALUES (:type,1,CAST(:definition AS jsonb))'),{'type':raw['type_definition']['id'],'definition':json.dumps(definition)})
    assert api.get(f"/api/v1/inventory/{copy['id']}").json()==copy
    assert api.get(f'/api/v1/custom-collections/{cid}').json()['type_revision']==0


def test_original_retry_survives_definition_revision(client):
    api,db=client;c=activate(api,typed_proposal());cid=c['id'];key=str(uuid.uuid4())
    first=add(api,cid,{'head':'Soft'},request_id=key,expected_type_revision=0).json()
    definition=copy_json(c['proposal']['type_definition']);definition['optional_fields'][0]['options'].append('Other')
    assert api.post(f'/api/v1/custom-collections/{cid}/definition',json={'expected_revision':0,'definition':definition}).status_code==200
    retry=add(api,cid,{'head':'Soft'},request_id=key,expected_type_revision=0)
    assert retry.status_code==200 and retry.json()['id']==first['id']


def test_control_revision_blocks_destructive_downgrade(client):
    import importlib.util
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    api,db=client;activate(api,typed_proposal())
    path=Path(__file__).resolve().parents[1]/'alembic/versions/0015_custom_field_controls.py'
    spec=importlib.util.spec_from_file_location('controls_migration',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.op=Operations(MigrationContext.configure(db))
    with pytest.raises(RuntimeError,match='downgrade would lose history'):module.downgrade()
