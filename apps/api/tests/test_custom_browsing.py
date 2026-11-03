"""Custom goals remain distinct identities in shared inventory browsing."""
import uuid
from sqlalchemy import text
from test_inventory_api import client
from test_custom_collections import activate,proposal


def custom(api,cid,title):
    r=api.post(f'/api/v1/custom-collections/{cid}/copies',json={'request_id':str(uuid.uuid4()),'title':title,'custom_details':{}})
    assert r.status_code==200,r.text
    return r.json()


def test_group_overview_keeps_custom_collections_out_of_other_and_names_separate(client):
    api,db=client;raw=proposal();raw['collection']['name']='Comics';first=activate(api,raw)
    raw['collection']['id']='second-goal';second=activate(api,raw)
    a=custom(api,first['id'],'Synthetic first');b=custom(api,second['id'],'Synthetic second')
    generic=api.post('/api/v1/inventory',json={'title':'Generic','collection_type':'other'}).json()
    comic=api.post('/api/v1/inventory',json={'title':'Comic','collection_type':'comic'}).json()
    groups=api.get('/api/v1/collection-groups?split_custom=true').json();assert len(groups)==4
    goals=[g for g in groups if g.get('custom_collection_id')]
    assert {g['custom_collection_id'] for g in goals}=={first['id'],second['id']}
    assert all(g['label']=='Comics' and g['copy_count']==1 and g['collection_type']=='other' for g in goals)
    assert next(g for g in groups if g['collection_type']=='other' and not g.get('custom_collection_id'))['copy_count']==1
    legacy=api.get('/api/v1/collection-groups').json();assert len(legacy)==2 and next(g for g in legacy if g['collection_type']=='other')['copy_count']==3
    paged=[api.get('/api/v1/collection-groups',params={'limit':1,'offset':i,'split_custom':True}).json()[0] for i in range(4)]
    assert paged==groups
    assert a['custom_collection_name']=='Comics' and b['custom_collection_name']=='Comics' and generic['custom_collection_name'] is None
    assert api.get('/api/v1/inventory/'+a['id']).json()==a
    assert db.execute(text('SELECT count(*) FROM copy_detail_events')).scalar()==0


def test_custom_filter_composes_with_search_storage_and_pagination(client):
    api,db=client;cid=activate(api)['id'];rows=[custom(api,cid,f'Synthetic {i}') for i in range(23)]
    target=custom(api,cid,'Literal %_\\ <script>');location=api.post('/api/v1/storage-locations',json={'name':'Synthetic storage'}).json()['id']
    db.execute(text('UPDATE owned_copies SET storage_location_id=:location WHERE id=:id'),{'location':location,'id':target['id']})
    first=api.get('/api/v1/inventory',params={'custom_collection_id':cid,'limit':20}).json();last=api.get('/api/v1/inventory',params={'custom_collection_id':cid,'limit':20,'offset':20}).json()
    assert len(first)==20 and len(last)==4 and {r['id'] for r in first+last}=={r['id'] for r in rows+[target]}
    filtered=api.get('/api/v1/inventory',params={'custom_collection_id':cid,'q':'%_\\','storage_location_id':location}).json();assert [r['id'] for r in filtered]==[target['id']]
    assert len(api.get('/api/v1/inventory',params={'custom_collection_id':cid,'unassigned':True}).json())==23
    assert api.get('/api/v1/inventory',params={'custom_collection_id':cid,'exclude_custom':True}).status_code==422
    assert api.get('/api/v1/inventory?custom_collection_id=invalid').status_code==422
    assert api.get('/api/v1/inventory',params={'custom_collection_id':str(uuid.uuid4())}).json()==[]
    db.execute(text('UPDATE owned_copies SET deleted_at=now() WHERE id=:id'),{'id':target['id']})
    overview=api.get('/api/v1/collection-groups?split_custom=true').json();assert len(overview)==1 and overview[0]['copy_count']==23
    assert len(api.get('/api/v1/collection-groups',params={'storage_location_id':location}).json())==0


def test_other_filter_can_explicitly_exclude_custom_without_changing_legacy_default(client):
    api,db=client;cid=activate(api)['id'];figure=custom(api,cid,'Synthetic custom');generic=api.post('/api/v1/inventory',json={'title':'Synthetic generic'}).json()
    assert len(api.get('/api/v1/inventory?collection_type=other').json())==2
    assert [r['id'] for r in api.get('/api/v1/inventory?collection_type=other&exclude_custom=true').json()]==[generic['id']]
    assert figure['collection_type']=='other' and figure['custom_collection_id']==cid
    assert 'custom_collection_name' not in __import__('relicrat.models',fromlist=['OwnedCopy']).OwnedCopy.__table__.c
