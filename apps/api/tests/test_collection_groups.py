"""Navigation groups count the full filtered inventory without merging ownership."""
from uuid import uuid4
from sqlalchemy import text
from test_inventory_api import client


def create(api,kind,title,**extra):
    r=api.post('/api/v1/inventory',json={'collection_type':kind,'title':title,**extra});assert r.status_code==201,r.text;return r.json()


def test_whole_result_counts_members_paging_and_literal_keys(client):
    api,_=client
    comics=[create(api,'comic','Shared series',comic_details={'issue_number':str(i+1)}) for i in range(25)]
    other=create(api,'other','Shared series')
    album=create(api,'record','Shared album',record_details={'artist':'Shared series'})
    groups=api.get('/api/v1/collection-groups').json();assert {g['collection_type']:g['copy_count'] for g in groups}=={'comic':25,'record':1,'other':1}
    assert api.get('/api/v1/collection-groups?collection_type=comic').json()==[{'collection_type':'comic','value':'Shared series','label':'Shared series','copy_count':25}]
    first=api.get('/api/v1/inventory',params={'collection_type':'comic','group':'Shared series','limit':20}).json()
    last=api.get('/api/v1/inventory',params={'collection_type':'comic','group':'Shared series','offset':20}).json()
    assert len(first)==20 and len(last)==5
    assert [c['comic_details']['issue_number'] for c in first[:11]]==[str(n) for n in range(1,12)]
    assert {c['id'] for c in first+last}=={c['id'] for c in comics}
    assert api.get('/api/v1/inventory',params={'collection_type':'record','group':'Shared series'}).json()==[album]
    assert api.get('/api/v1/inventory',params={'group':'Shared series'}).status_code==422
    assert api.get('/api/v1/inventory/'+other['id']).json()==other
    key='Literal %_\\ <script>'
    marked=create(api,'comic',key)
    assert api.get('/api/v1/collection-groups',params={'collection_type':'comic','q':'%_\\'}).json()[0]['value']==key
    assert [c['id'] for c in api.get('/api/v1/inventory',params={'collection_type':'comic','group':key}).json()]==[marked['id']]
    assert api.get('/api/v1/collection-groups',params={'collection_type':'comic','q':'no such text'}).json()==[]


def test_group_pagination_unknowns_case_distinctions_and_album_title_order(client):
    api,connection=client
    for i in range(23):create(api,'record',f'Test title {i}',record_details={'artist':f'Artist {i:02}'})
    unknown=create(api,'record','Unknown artist album')
    for title in ['Zulu','Alpha','Middle']:create(api,'record',title,record_details={'artist':'Sort band'})
    create(api,'record','Case separate',record_details={'artist':'sort band'})
    page1=api.get('/api/v1/collection-groups?collection_type=record&limit=20').json()
    page2=api.get('/api/v1/collection-groups?collection_type=record&limit=20&offset=20').json()
    assert len(page1)==20 and len(page2)==6
    assert page2[-1]['value'] is None and page2[-1]['label']=='Artist not recorded'
    assert len({g['value'] for g in page1+page2})==26
    assert [c['title'] for c in api.get('/api/v1/inventory',params={'collection_type':'record','group':'Sort band'}).json()]==['Alpha','Middle','Zulu']
    assert [c['id'] for c in api.get('/api/v1/inventory',params={'collection_type':'record','group':''}).json()]==[unknown['id']]
    comic=create(api,'comic','Temporary title',description='Description-only copy')
    connection.execute(text('UPDATE owned_copies SET provisional_title=NULL WHERE id=:id'),{'id':comic['id']})
    assert api.get('/api/v1/collection-groups?collection_type=comic').json()[0]['label']=='Series not recorded'
    assert api.get('/api/v1/inventory?collection_type=comic&group=').json()[0]['id']==comic['id']


def test_storage_search_counts_deleted_rows_and_no_write(client):
    api,connection=client
    location=api.post('/api/v1/storage-locations',json={'name':'Synthetic box'}).json()['id']
    left=create(api,'comic','Shared series',comic_details={'issue_number':'1','publisher':'Needle'})
    right=create(api,'comic','Shared series',comic_details={'issue_number':'2','publisher':'Other press'})
    deleted=create(api,'comic','Hidden series')
    connection.execute(text('UPDATE owned_copies SET storage_location_id=:location WHERE id=:id'),{'location':location,'id':left['id']})
    connection.execute(text('UPDATE owned_copies SET deleted_at=now() WHERE id=:id'),{'id':deleted['id']})
    for filters in ({'storage_location_id':location},{'q':'Needle'},{'unassigned':'true'}):
        groups=api.get('/api/v1/collection-groups',params={'collection_type':'comic',**filters}).json();assert len(groups)==1 and groups[0]['copy_count']==1
        members=api.get('/api/v1/inventory',params={'collection_type':'comic','group':'Shared series',**filters}).json()
        assert [c['id'] for c in members]==[right['id'] if 'unassigned' in filters else left['id']]
    assert api.get('/api/v1/collection-groups',params={'storage_location_id':location,'unassigned':True}).status_code==422
    assert api.get('/api/v1/collection-groups',params={'storage_location_id':str(uuid4())}).json()==[]
    assert api.get('/api/v1/collection-groups?storage_location_id=invalid').status_code==422
    assert api.get('/api/v1/collection-groups?limit=101').status_code==422
    assert api.get('/api/v1/collection-groups?collection_type=other').status_code==422
    assert api.get('/api/v1/collection-groups',params={'q':'\x00'}).status_code==422
    assert connection.scalar(text('SELECT count(*) FROM copy_detail_events'))==0
    assert connection.scalar(text('SELECT count(*) FROM copy_location_events'))==0
    api.headers.pop('authorization',None);api.cookies.clear()
    assert api.get('/api/v1/collection-groups').status_code==401
