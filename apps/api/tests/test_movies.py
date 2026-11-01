"""Generated Movie observations and CSV rows; never use a private export."""
import csv,io,json,uuid
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_inventory_api import client
from test_csv_import import post
from relicrat.csv_import import parse_csv
from relicrat.collection_types import COLLECTION_TYPES

FIELDS=['Title','Studio','Country code','UPC','EAN','Product ID','Release date','Slipcover','Casing','Memorabilia','Blu-ray discs','DVD discs','Digital copy','Date added','Watched','Comment','Retailer','Price','Price comment']

def encoded(rows):
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader()
    for row in rows:writer.writerow(dict.fromkeys(FIELDS,'')|{'Title':'Synthetic movie set','Studio':'Example studio','UPC':'012345678905','EAN':'0012345678905','Product ID':'synthetic-shared','Casing':'SteelBook','Blu-ray discs':'20','DVD discs':'0'}|row)
    return ('\ufeff'+stream.getvalue()).encode()


def test_movie_create_edit_history_old_client_omission_search_grouping_and_type_changes(client):
    api,db=client
    result=api.post('/api/v1/inventory',json={'title':'Synthetic movie','collection_type':'movie','movie_details':{'studio':' Example studio ','media_format':' Blu-ray '}})
    assert result.status_code==201,result.text
    copy=result.json();cid=copy['id'];assert copy['movie_details']=={'studio':'Example studio','media_format':'Blu-ray'}
    assert copy['catalog_item_id'] is None and copy['release_id'] is None
    for term in ('Example studio','Blu-ray'):
        assert [c['id'] for c in api.get('/api/v1/inventory',params={'q':term,'collection_type':'movie'}).json()]==[cid]
    assert api.get('/api/v1/collection-groups?collection_type=movie').json()[0]['copy_count']==1
    payload={'title':copy['title'],'edition_label':None,'expected_details_revision':0,'expected_identification_revision':0,'movie_details':{'media_format':'DVD','studio':'Different studio'}}
    update=api.post(f'/api/v1/inventory/{cid}/details',json=payload);assert update.status_code==200,update.text
    event=api.get(f'/api/v1/inventory/{cid}/detail-history').json()[0]
    assert event['before_movie_details']==copy['movie_details'] and event['after_movie_details']['media_format']=='DVD'
    assert api.post(f'/api/v1/inventory/{cid}/details',json=payload).status_code==409
    payload.pop('movie_details');payload['expected_details_revision']=1;payload['collection_type']='other'
    updated=api.post(f'/api/v1/inventory/{cid}/details',json=payload).json()
    assert updated['movie_details']=={'media_format':'DVD','studio':'Different studio'} and updated['id']==cid
    assert api.get('/api/v1/collection-settings/studio-suggestions').json()==[]  # Reclassified copies excluded.
    for values in ({'studio':'x'*251},{'media_format':'x'*101},{'studio':2},{'year':2020}):
        assert api.post('/api/v1/inventory',json={'title':'Rejected','collection_type':'movie','movie_details':values}).status_code==422
    assert api.post('/api/v1/inventory',json={'title':'Wrong type','movie_details':{'studio':'Example'}}).status_code==422


def test_movie_definition_preferences_and_saved_studio_suggestions(client):
    api,db=client;definition=api.get('/api/v1/collection-settings/types').json()['movie']
    assert definition['lookup']['provider']=='upcitemdb' and definition['entry_order'][0]=='title'
    assert definition['fields'][0]['options']==['Blu-ray','4K UHD','DVD','Blu-ray + DVD','VHS','LaserDisc']
    settings=api.get('/api/v1/collection-settings').json();assert not settings['movies_enabled']
    original={k:settings[k] for k in ('records_enabled','record_fields','comics_enabled','comic_fields')}
    updated=api.post('/api/v1/collection-settings',json={k:v for k,v in settings.items() if k!='revision'}|{'movies_enabled':True,'default_type':'movie','movie_fields':['studio'],'expected_revision':settings['revision']})
    assert updated.status_code==200,updated.text
    assert all(updated.json()[k]==v for k,v in original.items())
    for studio in ('Example Studio','example studio','Other Studio','100% Studio'):
        api.post('/api/v1/inventory',json={'title':'Synthetic','collection_type':'movie','movie_details':{'studio':studio}})
    assert len(api.get('/api/v1/collection-settings/studio-suggestions?q=example').json())==1
    assert api.get('/api/v1/collection-settings/studio-suggestions?q=100%25').json()==['100% Studio']
    invalid=api.post('/api/v1/collection-settings',json={k:v for k,v in updated.json().items() if k!='revision'}|{'movies_enabled':False,'expected_revision':updated.json()['revision']})
    assert invalid.status_code==422


def test_bluray_preview_commit_retry_source_retention_and_unknowns(client):
    api,db=client
    raw=encoded([{'Comment':'=literal source text\nSecond line','Price':'not interpreted'}, {'EAN':'1234567890128','Product ID':'synthetic-shared'}, {'UPC':'','EAN':'','Blu-ray discs':'-1','DVD discs':'-1','Casing':''}])
    preview=post(api,'preview',raw,'bluray');assert preview.status_code==200,preview.text
    value=preview.json();assert value['copy_count']==3 and value['row_count']==3 and not value['errors']
    assert value['repeated_external_ids']==2 and len(value['warnings'])==2
    assert value['sample'][0]['movie_details']=={'media_format':'Blu-ray','studio':'Example studio'}
    assert value['sample'][0]['barcode']['value']=='012345678905'
    assert value['sample'][1]['barcode'] is None and value['sample'][2]['movie_details']=={'media_format':None,'studio':'Example studio'}
    assert api.get('/api/v1/inventory').json()==[]
    result=post(api,'commit',raw,'bluray',reviewed_sha256=value['sha256']);assert result.status_code==200,result.text
    batch=result.json()['batch'];assert batch['copy_count']==3
    assert post(api,'commit',raw,'bluray',reviewed_sha256=value['sha256']).json()['already_imported']
    copies=api.get('/api/v1/inventory?collection_type=movie').json();assert len(copies)==3 and len({c['id'] for c in copies})==3
    originals=api.get(f"/api/v1/imports/{batch['id']}/rows").json();assert originals[0]['source']['Price']=='not interpreted' and originals[0]['source']['Comment']=='=literal source text\nSecond line'
    assert all(c['catalog_item_id'] is None and c['release_id'] is None for c in copies)
    assert post(api,'commit',raw.replace(b'Synthetic movie set',b'Changed synthetic movie set'),'bluray',reviewed_sha256=value['sha256']).status_code==409


@pytest.mark.parametrize('row',[{'Title':''},{'Studio':'x'*251},{'Blu-ray discs':'-2'},{'DVD discs':'1.5'}])
def test_bluray_invalid_rows_block_whole_import(client,row):
    api,db=client;raw=encoded([{},row]);value=post(api,'preview',raw,'bluray').json();assert value['errors']
    assert post(api,'commit',raw,'bluray',reviewed_sha256=value['sha256']).status_code==422
    assert api.get('/api/v1/inventory').json()==[]


def test_bluray_barcode_checksums_and_disc_counts_do_not_guess_ownership_or_4k():
    parsed=parse_csv('bluray',encoded([{'UPC':'012345678906','EAN':'','Blu-ray discs':'0','DVD discs':'2'}, {'Blu-ray discs':'1','DVD discs':'1'}]))
    assert parsed['copy_count']==2 and parsed['rows'][0][2].barcode is None
    assert parsed['rows'][0][2].movie_details.media_format=='DVD'
    assert parsed['rows'][1][2].movie_details.media_format=='Blu-ray + DVD'
    assert len(parsed['warnings'])==1


@pytest.mark.parametrize('details',[{'studio':2},{'studio':''},{'media_format':'x'*101},{'unexpected':'field'},None])
def test_movie_direct_sql_constraints(client,details):
    api,db=client;cid=api.post('/api/v1/inventory',json={'title':'Synthetic','collection_type':'movie'}).json()['id']
    with pytest.raises(IntegrityError),db.begin_nested():db.execute(text('UPDATE owned_copies SET movie_details=cast(:value as jsonb) WHERE id=:id'),{'id':cid,'value':json.dumps(details)})
