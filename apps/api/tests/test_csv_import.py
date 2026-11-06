"""Synthetic CSVs only: ownership, original evidence, atomicity and retry safety."""
import csv,io,os,hashlib,uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine,select,func,text
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from relicrat.csv_import import parse_csv,commit_import
from relicrat.models import ImportBatch,ImportCopy,OwnedCopy
from test_inventory_api import client


def encoded(source,rows):
    fields=['Series','Issue','Publisher','Quantity','Collection Status','Notes','Core ComicID','Storage Box','Variant Description'] if source=='clz' else ['Title','Artist','Format','release_id','Collection Notes','CollectionFolder']
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
    for row in rows:
        default={'Series':'Synthetic series','Issue':'1A','Publisher':'Test press','Quantity':'1','Collection Status':'In Collection','Notes':'A note, with commas\nand a second line','Core ComicID':'shared','Storage Box':'Test Box','Variant Description':'Copper cover'} if source=='clz' else {'Title':'Synthetic album','Artist':'Test band','Format':'CD, Album, Reissue','release_id':'shared','Collection Notes':'=not a formula to execute','CollectionFolder':'Synthetic folder'}
        writer.writerow(default|row)
    return ('\ufeff'+stream.getvalue()).encode()


def post(api,path,raw,source='clz',**params):
    return api.post('/api/v1/imports/'+path,params={'source':source,**params},content=raw,headers={'content-type':'text/csv'})


def test_preview_commit_retry_provenance_and_existing_inventory(client):
    api,connection=client
    original=api.post('/api/v1/inventory',json={'title':'Keep this copy'}).json()
    raw=encoded('clz',[{'Quantity':'2'},{'Series':'Another synthetic series'}]);digest=hashlib.sha256(raw).hexdigest()
    p=post(api,'preview',raw).json()
    assert p['copy_count']==3 and p['repeated_external_ids']==1 and not p['errors']
    assert len(api.get('/api/v1/inventory').json())==1 and api.get('/api/v1/imports').json()==[]
    assert post(api,'commit',raw,reviewed_sha256='0'*64).status_code==409
    r=post(api,'commit',raw,reviewed_sha256=digest);assert r.status_code==200,r.text
    batch=r.json()['batch'];assert not r.json()['already_imported']
    assert post(api,'commit',raw,reviewed_sha256=digest).json()['already_imported']
    assert post(api,'preview',raw).json()['existing_batch']['id']==batch['id']
    copies=api.get('/api/v1/inventory').json();assert len(copies)==4
    assert api.get('/api/v1/inventory/'+original['id']).json()==original
    imported=[c for c in copies if c['id']!=original['id']]
    assert all(c['comic_details']['issue_number']=='1A' and c['catalog_item_id'] is None and c['storage_location_id'] is None for c in imported)
    rows=api.get('/api/v1/imports/'+batch['id']+'/rows').json();assert len(rows)==3
    assert rows[0]['source']['Notes']=='A note, with commas\nand a second line'
    assert rows[0]['source']['Storage Box']=='Test Box'
    assert rows[0]['copy_id']!=rows[1]['copy_id'] and rows[0]['source']==rows[1]['source']
    assert api.get('/api/v1/imports/'+batch['id']+'/rows?limit=1&offset=2').json()==rows[2:]
    assert api.get('/api/v1/imports').json()==[batch]
    assert api.get('/api/v1/imports/'+str(uuid.uuid4())+'/rows').status_code==404
    api.cookies.clear();api.headers.pop('authorization',None);assert post(api,'preview',b'malformed').status_code==401
    assert api.get('/api/v1/imports').status_code==401


def test_invalid_rows_never_partially_import(client):
    api,connection=client
    for row in ({'Collection Status':'Wish List'},{'Collection Status':'Sold'},{'Quantity':'0'},{'Quantity':'1.5'},{'Series':''},{'Issue':'x'*101}):
        raw=encoded('clz',[{},row]);p=post(api,'preview',raw).json();assert p['errors']
        assert post(api,'commit',raw,reviewed_sha256=p['sha256']).status_code==422
    assert api.get('/api/v1/inventory').json()==[] and api.get('/api/v1/imports').json()==[]
    assert post(api,'preview',b'x'* (4*1024*1024+1)).status_code==413
    assert api.post('/api/v1/imports/preview?source=clz',json={}).status_code==415
    assert post(api,'preview',encoded('clz',[{}]),source='unknown').status_code==422


@pytest.mark.parametrize('raw',[b'',b'\xff',b'a,a\n1,2',b'Series\nhello',b'a\x00,b\n1,2',b'"unterminated',b'a,b\n1,2,3'])
def test_parser_rejects_malformed_without_echoing_contents(raw):
    with pytest.raises(HTTPException):parse_csv('clz',raw)


def test_parser_limits_and_no_truncation():
    with pytest.raises(HTTPException):parse_csv('clz',encoded('clz',[{}]*5001))
    with pytest.raises(HTTPException):parse_csv('clz',encoded('clz',[{'Quantity':'10000'},{}]))
    p=parse_csv('discogs',encoded('discogs',[{},{}]));assert p['copy_count']==2 and p['repeated_external_ids']==1
    assert p['rows'][0][2].record_details.format=='CD, Album, Reissue'
    assert p['rows'][0][1]['Collection Notes']=='=not a formula to execute'


def test_synthetic_1915_copy_volume_and_type_pages(client):
    api,connection=client
    for source,count in [('clz',1450),('discogs',465)]:
        rows=[{'Series':f'Synthetic comic {i}','Core ComicID':str(i)} if source=='clz' else {'Title':f'Synthetic album {i}','release_id':str(i)} for i in range(count)]
        raw=encoded(source,rows);p=post(api,'preview',raw,source).json();assert p['copy_count']==count and not p['errors']
        r=post(api,'commit',raw,source,reviewed_sha256=p['sha256']);assert r.status_code==200,r.text
        assert r.json()['batch']['copy_count']==count
    with Session(bind=connection) as db:
        assert db.scalar(select(func.count()).select_from(OwnedCopy))==1915
        assert db.scalar(select(func.count()).select_from(ImportCopy))==1915
        assert db.scalar(select(func.count()).select_from(ImportBatch))==2
    for kind,count in [('comic',1450),('record',465)]:
        first=api.get(f'/api/v1/inventory?collection_type={kind}&limit=20').json()
        last=api.get(f'/api/v1/inventory?collection_type={kind}&limit=20&offset={count-5}').json()
        assert len(first)==20 and len(last)==5
        assert not set(c['id'] for c in first)&set(c['id'] for c in last)
        assert all(c['collection_type']==kind for c in first+last)


def test_failure_rolls_back_whole_batch(client,monkeypatch):
    from relicrat import csv_import
    api,_=client;original=csv_import.stage_copy;calls=0
    def fail(db,payload):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('synthetic failure')
        return original(db,payload)
    monkeypatch.setattr(csv_import,'stage_copy',fail)
    raw=encoded('clz',[{},{}])
    with pytest.raises(RuntimeError,match='synthetic failure'):post(api,'commit',raw,reviewed_sha256=hashlib.sha256(raw).hexdigest())
    assert api.get('/api/v1/inventory').json()==[] and api.get('/api/v1/imports').json()==[]


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'),reason='Requires disposable PostgreSQL')
def test_concurrent_imports_create_one_batch_and_guard_downgrade():
    engine=create_engine(os.environ['TEST_DATABASE_URL']);raw=encoded('clz',[{},{}]);digest=hashlib.sha256(raw).hexdigest();barrier=Barrier(2)
    def run():
        with Session(engine) as db:
            barrier.wait();return commit_import('clz',raw,digest,db)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:run(),range(2)))
        assert sorted(r['already_imported'] for r in results)==[False,True]
        assert len({r['batch']['id'] for r in results})==1
        config=Config('alembic.ini')
        with engine.connect() as db: original_revision=db.scalar(text('SELECT version_num FROM alembic_version'))
        with pytest.raises(RuntimeError,match='Import provenance exists'):command.downgrade(config,'0008_appearance')
        with engine.connect() as db:
            assert db.scalar(text('SELECT count(*) FROM import_copies'))==2
            assert db.scalar(text('SELECT version_num FROM alembic_version'))==original_revision
    finally:
        with engine.begin() as db:
            # Disposable test records only. Real application has no hard-delete API.
            ids=list(db.execute(text('SELECT owned_copy_id FROM import_copies')).scalars())
            db.execute(text('DELETE FROM import_copies'));db.execute(text('DELETE FROM import_batches'))
            for ident in ids:db.execute(text('DELETE FROM owned_copies WHERE id=:id'),{'id':ident})
        engine.dispose()


def test_provenance_constraints_and_restrictive_references(client):
    from sqlalchemy.exc import DBAPIError
    api,connection=client;raw=encoded('discogs',[{}]);digest=hashlib.sha256(raw).hexdigest()
    result=post(api,'commit',raw,'discogs',reviewed_sha256=digest).json();batch=result['batch']['id']
    copy=api.get('/api/v1/imports/'+batch+'/rows').json()[0]['copy_id']
    statements=[
        ("UPDATE import_batches SET source='unknown' WHERE id=:id",batch),
        ("UPDATE import_batches SET sha256='invalid' WHERE id=:id",batch),
        ('UPDATE import_batches SET parser_version=2 WHERE id=:id',batch),
        ('UPDATE import_batches SET row_count=0 WHERE id=:id',batch),
        ('UPDATE import_batches SET copy_count=10001 WHERE id=:id',batch),
        ("UPDATE import_copies SET source_row='[]'::jsonb WHERE owned_copy_id=:id",copy),
        ('UPDATE import_copies SET row_number=1 WHERE owned_copy_id=:id',copy),
        ('UPDATE import_copies SET copy_number=0 WHERE owned_copy_id=:id',copy),
        ('DELETE FROM import_batches WHERE id=:id',batch),
        ('DELETE FROM owned_copies WHERE id=:id',copy),
    ]
    for statement,ident in statements:
        with pytest.raises(DBAPIError):
            with connection.begin_nested():connection.execute(text(statement),{'id':ident})
    assert api.get('/api/v1/imports/'+batch+'/rows').json()[0]['copy_id']==copy


def test_possible_duplicates_use_same_source_across_batches_and_keep_copy_identity(client):
    api, connection = client

    def import_rows(source, rows):
        raw = encoded(source, rows)
        response = post(api, 'commit', raw, source, reviewed_sha256=hashlib.sha256(raw).hexdigest())
        assert response.status_code == 200, response.text
        return response.json()['batch']['id']

    earlier = import_rows('clz', [{'Variant Description': 'Silver cover'}])
    selected = import_rows('clz', [
        {'Core ComicID': ' shared ', 'Quantity': '2'},
        {'Core ComicID': ''},
        {'Core ComicID': 'only-in-this-file', 'Quantity': '2'},
    ])
    other_source = import_rows('discogs', [{}])
    earlier_copy = api.get(f'/api/v1/imports/{earlier}/rows').json()[0]['copy_id']
    unrelated = api.get(f'/api/v1/imports/{other_source}/rows').json()[0]['copy_id']
    shelf = api.post('/api/v1/storage-locations', json={'name': 'Test shelf'}).json()
    move = api.post(f'/api/v1/inventory/{earlier_copy}/location', json={
        'storage_location_id': shelf['id'], 'expected_storage_revision': 0,
    })
    assert move.status_code == 200, move.text

    path = f'/api/v1/imports/{selected}/possible-duplicates'
    response = api.get(path)
    assert response.status_code == 200, response.text
    group, = response.json()
    assert (group['selected_count'], group['other_count']) == (2, 1)
    assert api.get(path, params={'limit': 1, 'offset': 1}).json() == []
    assert api.get(path, params={'anchor': unrelated}).status_code == 404

    copies = api.get(path, params={'anchor': group['anchor']}).json()
    assert [copy['selected_import'] for copy in copies] == [True, True, False]
    assert len({copy['copy_id'] for copy in copies}) == 3
    assert copies[2]['copy_id'] == earlier_copy
    assert copies[2]['edition'] == 'Silver cover'
    assert copies[2]['storage'] == 'Test shelf'
    assert api.get(path, params={'anchor': group['anchor'], 'offset': 2, 'limit': 1}).json() == copies[2:]
    with Session(bind=connection) as db:
        assert db.scalar(select(func.count()).select_from(OwnedCopy)) == 7
    api.cookies.clear()
    api.headers.pop('authorization', None)
    assert api.get(path).status_code == 401


def test_duplicate_decisions_are_pair_scoped_retry_safe_and_reversible(client, tmp_path, monkeypatch):
    from test_media_api import png_bytes

    api, connection = client
    monkeypatch.setenv('MEDIA_ROOT', str(tmp_path / 'media'))

    def import_batch(edition, quantity='1'):
        raw = encoded('clz', [{'Variant Description': edition, 'Quantity': quantity}])
        response = post(api, 'commit', raw, reviewed_sha256=hashlib.sha256(raw).hexdigest())
        assert response.status_code == 200, response.text
        return response.json()['batch']['id']

    prior = import_batch('Silver')
    current = import_batch('Copper', '2')
    review = f'/api/v1/imports/{current}/possible-duplicates'
    decisions = f'/api/v1/imports/{current}/duplicate-decisions'
    other_history = f'/api/v1/imports/{prior}/duplicate-decisions'
    group, = api.get(review).json()
    a, b, older = api.get(review, params={'anchor': group['anchor']}).json()

    def payload(first, second, archive_id=None):
        return {'request_id': str(uuid.uuid4()), 'first_id': first['copy_id'], 'second_id': second['copy_id'],
                'first_updated_at': first['updated_at'], 'second_updated_at': second['updated_at'],
                'archive_id': archive_id}

    assert api.post(decisions, json=payload(a, b)).status_code == 422
    assert api.post(decisions, json=payload(a, older, str(uuid.uuid4()))).status_code == 422
    first = payload(a, older)
    response = api.post(decisions, json=first)
    assert response.status_code == 200, response.text
    assert api.post(decisions, json=first).json() == response.json()
    assert api.post(decisions, json=first | {'archive_id': older['copy_id']}).status_code == 409
    assert len(api.get(review).json()) == 1
    second = payload(b, older)
    assert api.post(decisions, json=second).status_code == 200
    assert api.get(review).json() == []
    assert len(api.get('/api/v1/inventory').json()) == 3

    def undo(request):
        return api.post(f"{other_history}/{request['request_id']}/undo")

    assert len(api.get(other_history).json()) == 2
    assert undo(first).status_code == 200
    assert len(api.get(review).json()) == 1

    photo_path = f"/api/v1/inventory/{older['copy_id']}/photos"
    photo = api.post(photo_path, files={'file': ('synthetic.png', png_bytes(), 'image/png')})
    assert photo.status_code == 201, photo.text
    photo_url = f"{photo_path}/{photo.json()['id']}"
    before = api.get('/api/v1/inventory/'+older['copy_id']).json()
    archive = payload(a, older, older['copy_id'])
    stale = archive | {'first_updated_at': '2000-01-01T00:00:00Z'}
    assert api.post(decisions, json=stale).status_code == 409
    saved = api.post(decisions, json=archive)
    assert saved.status_code == 200, saved.text
    assert api.post(decisions, json=archive).json() == saved.json()
    assert api.get('/api/v1/inventory/'+older['copy_id']).status_code == 404
    assert api.get(photo_url).status_code == 404
    assert api.get('/api/v1/inventory/'+a['copy_id']).status_code == 200
    assert api.get(review).json() == []
    assert undo(archive).status_code == undo(archive).status_code == 200
    restored = api.get('/api/v1/inventory/'+older['copy_id']).json()
    assert restored | {'updated_at': before['updated_at']} == before
    assert api.get(photo_url).content == png_bytes()
    assert api.get(f'/api/v1/imports/{prior}/rows').json()[0]['copy_id'] == older['copy_id']
    assert len(api.get(review).json()) == 1
    assert api.post(decisions, json=archive).json()['undone_at']
    with Session(bind=connection) as db:
        assert db.scalar(select(func.count()).select_from(OwnedCopy)) == 3


def test_preview_choices_skip_only_reviewed_rows_and_require_fresh_evidence(client):
    api, _ = client
    original = encoded('clz', [{'Variant Description': 'Silver cover'}])
    prior = post(api, 'commit', original, reviewed_sha256=hashlib.sha256(original).hexdigest()).json()['batch']
    existing, = api.get(f"/api/v1/imports/{prior['id']}/rows").json()

    changed = encoded('clz', [
        {'Variant Description': 'Copper cover', 'Quantity': '2'},
        {'Variant Description': 'Gold cover'},
        {'Core ComicID': 'new', 'Series': 'New series'},
    ])
    preview = post(api, 'preview', changed).json()
    review = preview['duplicate_review']
    assert [(row['row'], row['quantity']) for row in review['rows']] == [(2, 2), (3, 1)]
    assert review['groups'][0]['copies'][0]['edition'] == 'Silver cover'
    assert len(api.get('/api/v1/inventory').json()) == 1

    params = {'reviewed_sha256': preview['sha256'], 'duplicate_digest': review['digest']}
    assert post(api, 'commit', changed, **params).status_code == 422
    assert post(api, 'commit', changed, **params, skip_mask='04'+'00'*624).status_code == 422
    shelf = api.post('/api/v1/storage-locations', json={'name': 'Comparison shelf'}).json()
    assert api.post(f"/api/v1/inventory/{existing['copy_id']}/location", json={
        'storage_location_id': shelf['id'], 'expected_storage_revision': 0,
    }).status_code == 200
    assert post(api, 'commit', changed, **params, skip_mask='01'+'00'*624).status_code == 409
    refreshed = post(api, 'preview', changed).json()['duplicate_review']
    assert refreshed['groups'][0]['copies'][0]['storage'] == 'Comparison shelf'
    params.update(duplicate_digest=refreshed['digest'], skip_mask='01'+'00'*624)
    response = post(api, 'commit', changed, **params)
    assert response.status_code == 200, response.text
    batch = response.json()['batch']
    assert (batch['row_count'], batch['copy_count']) == (2, 2)
    rows = api.get(f"/api/v1/imports/{batch['id']}/rows").json()
    assert [row['row'] for row in rows] == [3, 4]
    assert rows[0]['source']['Variant Description'] == 'Gold cover'
    assert post(api, 'commit', changed, **params).json()['already_imported']
    assert post(api, 'preview', changed).json()['existing_batch']['id'] == batch['id']
    assert len(api.get('/api/v1/inventory').json()) == 3

    all_skipped = encoded('clz', [{'Variant Description': 'Another cover'}])
    empty_preview = post(api, 'preview', all_skipped).json()
    assert post(api, 'commit', all_skipped, reviewed_sha256=empty_preview['sha256'],
                duplicate_digest=empty_preview['duplicate_review']['digest'],
                skip_mask='01'+'00'*624).status_code == 422
    assert post(api, 'preview', all_skipped).json()['existing_batch'] is None
