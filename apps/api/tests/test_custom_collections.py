"""Synthetic custom definitions, retry safety, DB invariants and personal history."""
import json,uuid,os
from pathlib import Path
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_inventory_api import client

pytestmark=pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"),reason="TEST_DATABASE_URL not configured")


def proposal():
    return json.loads((Path(__file__).with_name('fixtures')/'tmnt-original-1988.json').read_text())


def activate(api,value=None):
    response=api.post('/api/v1/custom-collections',json=value or proposal())
    assert response.status_code==200,response.text
    return response.json()


def test_activation_is_empty_immutable_and_exact_retry_safe(client):
    api,db=client;before=api.get('/api/v1/inventory').json();value=activate(api)
    assert api.get('/api/v1/inventory').json()==before
    assert activate(api)['id']==value['id']
    assert api.get('/api/v1/custom-collections').json()==[{'id':value['id'],'name':value['name']}]
    assert api.get('/api/v1/custom-collections/'+value['id']).json()==value
    changed=proposal();changed['collection']['name']='Different name'
    assert api.post('/api/v1/custom-collections',json=changed).status_code==409
    changed=proposal();changed['type_definition']['title']['label']='Different field'
    assert api.post('/api/v1/custom-collections',json=changed).status_code==409
    second=proposal();second['collection']['id']='second-goal';second['collection']['name']='Another goal'
    assert activate(api,second)['id']!=value['id']
    assert db.execute(text('SELECT count(*) FROM custom_collection_types')).scalar()==1
    for sql in ["UPDATE custom_collection_types SET definition=definition", "DELETE FROM custom_collections"]:
        with pytest.raises(IntegrityError):
            with db.begin_nested():db.execute(text(sql))


def test_explicit_intake_retry_edit_history_filter_and_search(client):
    api,db=client;c=activate(api);cid=c['id'];request=str(uuid.uuid4())
    payload={'request_id':request,'title':'Leonardo','custom_details':{'accessories':'Two synthetic swords','condition':'Unknown'},'description':'Synthetic figure'}
    response=api.post(f'/api/v1/custom-collections/{cid}/copies',json=payload);assert response.status_code==200,response.text
    figure=response.json();assert figure['id']==request and figure['custom_collection_id']==cid and figure['catalog_item_id'] is None
    assert api.post(f'/api/v1/custom-collections/{cid}/copies',json=payload).json()['id']==request
    assert len(api.get('/api/v1/inventory',params={'custom_collection_id':cid}).json())==1
    assert api.get('/api/v1/inventory?q=synthetic%20swords').json()[0]['id']==request
    assert api.post(f'/api/v1/custom-collections/{cid}/copies',json=payload|{'title':'Different'}).status_code==409
    edit={'title':'Leonardo','edition_label':None,'expected_details_revision':0,'expected_identification_revision':0,'custom_details':{'condition':'Paint wear'}}
    response=api.post(f'/api/v1/inventory/{request}/details',json=edit);assert response.status_code==200,response.text
    assert response.json()['custom_details']=={'condition':'Paint wear'}
    history=api.get(f'/api/v1/inventory/{request}/detail-history').json()[0]
    assert history['before_custom_details']==payload['custom_details'] and history['after_custom_details']==edit['custom_details']
    assert api.post(f'/api/v1/inventory/{request}/details',json=edit).status_code==409
    # Retry the original create after a later edit returns this same current copy, never overwrites it.
    assert api.post(f'/api/v1/custom-collections/{cid}/copies',json=payload).json()['custom_details']=={'condition':'Paint wear'}
    edit['expected_details_revision']=1;edit['collection_type']='record'
    assert api.post(f'/api/v1/inventory/{request}/details',json=edit).status_code==422
    edit.pop('collection_type');edit.pop('custom_details')
    assert api.post(f'/api/v1/inventory/{request}/details',json=edit).json()['custom_details']=={'condition':'Paint wear'}
    with pytest.raises(IntegrityError):
        with db.begin_nested():db.execute(text("UPDATE owned_copies SET custom_details='{"+'"unexpected":"value"'+"}'::jsonb WHERE id=:id"),{'id':request})
    with pytest.raises(IntegrityError):
        with db.begin_nested():db.execute(text('UPDATE owned_copies SET custom_collection_id=NULL WHERE id=:id'),{'id':request})


@pytest.mark.parametrize('change',[
    {'title':' '},{'title':'x'*501},{'custom_details':{'price':'10'}},{'custom_details':{'condition':'x'*1001}},
    {'custom_details':{'condition':42}},{'custom_details':{'condition':' '}},
])
def test_invalid_intake_never_creates_ownership(client,change):
    api,db=client;c=activate(api)
    value={'request_id':str(uuid.uuid4()),'title':'Synthetic figure','custom_details':{}}|change
    assert api.post(f"/api/v1/custom-collections/{c['id']}/copies",json=value).status_code==422
    assert api.get('/api/v1/inventory').json()==[]


def test_builtins_cannot_store_unbound_custom_observations(client):
    api,db=client;copy=api.post('/api/v1/inventory',json={'title':'Generic'}).json()
    r=api.post(f"/api/v1/inventory/{copy['id']}/details",json={'title':'Generic','edition_label':None,'expected_details_revision':0,'expected_identification_revision':0,'custom_details':{'condition':'new'}})
    assert r.status_code==422


def test_populated_custom_collection_blocks_destructive_downgrade(client):
    import importlib.util
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    api,db=client;activate(api)
    path=Path(__file__).resolve().parents[1]/'alembic/versions/0014_custom_collections.py'
    spec=importlib.util.spec_from_file_location('custom_migration',path)
    revision=importlib.util.module_from_spec(spec);spec.loader.exec_module(revision)
    revision.op=Operations(MigrationContext.configure(db))
    with pytest.raises(RuntimeError,match='downgrade would lose history'):
        revision.downgrade()
    assert api.get('/api/v1/custom-collections').json()
