"""Synthetic barcode observations preserve copy identity and auditability."""
import os
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from auth_helpers import sign_in
from relicrat.barcodes import BarcodeReading
from relicrat.database import get_db
from relicrat.main import app
from relicrat.models import CopyDetailEvent, OwnedCopy

READING = {'value':'012345678905','format':'UPC_A'}

@pytest.mark.parametrize('bad', [
    {'value':12345678905,'format':'UPC_A'},
    {'value':'01234567890','format':'UPC_A'},
    {'value':'０１２３４５６７８９０５','format':'UPC_A'},
    {'value':'012345678905','format':'QR_CODE'},
    {**READING,'supplement':'1'}, {**READING,'supplement':12345},
    {**READING,'supplement':'00001\n'}, {**READING,'url':'https://invalid.test'},
    {'value':'012345678905\n','format':'UPC_A'},
])
def test_reject_untrusted_reading(bad):
    with pytest.raises(ValidationError): BarcodeReading(**bad)


def test_all_lengths_and_leading_zeroes():
    for value,format in [('012345678905','UPC_A'),('01234565','UPC_E'),('01234565','EAN_8'),('0012345678905','EAN_13')]:
        assert BarcodeReading(value=value,format=format,supplement='00001').value == value


@pytest.fixture
def context():
    url=os.getenv('TEST_DATABASE_URL')
    if not url:pytest.skip('TEST_DATABASE_URL not configured')
    engine=create_engine(url); ids=[]
    def override():
        with Session(engine,expire_on_commit=False) as db:yield db
    app.dependency_overrides[get_db]=override
    try:
        with TestClient(app) as api:
            sign_in(api)
            def create(**values):
                r=api.post('/api/v1/inventory',json={'title':'Synthetic barcode find',**values})
                assert r.status_code==201,r.text
                copy=r.json();ids.append(UUID(copy['id']));return copy
            yield api,engine,create
    finally:
        app.dependency_overrides.pop(get_db,None)
        with engine.begin() as db:
            db.execute(delete(CopyDetailEvent).where(CopyDetailEvent.owned_copy_id.in_(ids)))
            db.execute(delete(OwnedCopy).where(OwnedCopy.id.in_(ids)))
        engine.dispose()


def edit(api,copy,**changes):
    return api.post(f"/api/v1/inventory/{copy['id']}/details",json={
        'title':copy['title'],'edition_label':copy['edition_label'],
        'expected_details_revision':copy['details_revision'],
        'expected_identification_revision':copy['identification_revision'],**changes})


def test_optional_barcode_creation_search_duplicates_edit_history_and_stale(context):
    api,engine,create=context
    old=create();assert old['barcode']=={}
    copy=create(collection_type='record',barcode={**READING,'supplement':'00001'})
    duplicate=create(barcode=READING)  # Same product barcode may label many physical copies.
    matches=api.get('/api/v1/inventory',params={'q':READING['value']}).json()
    assert {c['id'] for c in matches}=={copy['id'],duplicate['id']}
    assert edit(api,copy,title='Renamed synthetic find').json()['barcode']==copy['barcode']
    current=api.get('/api/v1/inventory/'+copy['id']).json()
    response=edit(api,current,barcode={'value':'0012345678905','format':'EAN_13'})
    assert response.status_code==200,response.text
    changed=response.json()
    for key in ['id','catalog_item_id','release_id','storage_location_id','identification_revision','storage_revision','ownership_status','created_at']:
        assert changed[key]==copy[key]
    assert edit(api,current,barcode=None).status_code==409
    assert edit(api,changed,barcode=changed['barcode']).json()==changed
    cleared=edit(api,changed,barcode=None).json();assert cleared['barcode']=={}
    events=api.get(f"/api/v1/inventory/{copy['id']}/detail-history").json()
    assert len(events)==3 and events[-1]['before_barcode']==changed['barcode'] and events[-1]['after_barcode']=={}
    assert edit(api,cleared,collection_type='other').json()['barcode']=={}
    bad=api.post('/api/v1/inventory',json={'barcode':READING})
    assert bad.status_code==422  # A code alone never substitutes for a meaningful find.
    assert api.post('/api/v1/inventory',json={'title':'Invalid','barcode':{**READING,'value':12}}).status_code==422
    assert edit(api,cleared,barcode={**READING,'supplement':'123'}).status_code==422
    with engine.connect() as db:
        assert db.scalar(select(OwnedCopy.id).where(OwnedCopy.id==UUID(old['id'])))
    api.cookies.clear();api.headers.pop('Authorization',None)
    assert api.get('/api/v1/inventory',params={'q':READING['value']}).status_code==401
    assert api.post('/api/v1/inventory',json={'title':'Guest','barcode':READING}).status_code==401


@pytest.mark.parametrize('bad', [None, [], 'text', {'value':'123','format':'UPC_A'}, {'value':'012345678905'}, {**READING,'value':12}, {**READING,'format':'QR'}, {**READING,'supplement':None}, {**READING,'supplement':'123'}, {**READING,'extra':'x'}])
def test_database_rejects_invalid_barcode(context,bad):
    import json
    _,engine,create=context;copy=create()
    with pytest.raises(IntegrityError),engine.begin() as db:
        db.execute(text('UPDATE owned_copies SET barcode=CAST(:value AS jsonb) WHERE id=:id'),{'value':json.dumps(bad),'id':copy['id']})
