"""Synthetic artwork only; no external requests or owner collection fixtures."""
import io,uuid
import pytest
from PIL import Image
from sqlalchemy import text
from sqlalchemy.orm import Session
from relicrat.barcode_providers import PROVIDERS
from relicrat.musicbrainz import LookupUnavailable
from relicrat.models import MediaAsset
from test_media_api import client

ID='abcdefab-abcd-4abc-8abc-abcdefabcdef'
COVER={'provider':'musicbrainz','candidate_id':ID}

def image():
    b=io.BytesIO();Image.new('RGB',(8,8),'purple').save(b,format='JPEG');return b.getvalue()

@pytest.fixture(autouse=True)
def provider(monkeypatch):
    monkeypatch.setitem(PROVIDERS['musicbrainz'],'cover',lambda ident:image())

def test_optional_cover_is_atomic_labelled_sourced_downloadable_and_idempotent(client):
    api,connection,root=client
    response=api.post('/api/v1/inventory',json={'title':'Synthetic optional artwork','collection_type':'record','catalog_cover':COVER})
    assert response.status_code==201,response.text
    copy=response.json();cid=copy['id'];assert copy['catalog_item_id'] is None
    photos=api.get(f'/api/v1/inventory/{cid}/photos').json();assert len(photos)==1
    art=photos[0];assert art['role']=='catalog_cover' and art['source_provider']=='musicbrainz' and art['source_id']==ID
    assert art['source_url']=='https://musicbrainz.org/release/'+ID
    assert api.get(f"/api/v1/inventory/{cid}/photos/{art['id']}").content==image()
    payload={'title':copy['title'],'edition_label':None,'expected_details_revision':0,'expected_identification_revision':0,'catalog_cover':COVER}
    for ident in [ID,ID.upper()]:
        payload['catalog_cover']={**COVER,'candidate_id':ident}
        assert api.post(f'/api/v1/inventory/{cid}/details',json=payload).status_code==200
    assert len(api.get(f'/api/v1/inventory/{cid}/photos').json())==1
    # Ordinary saves do not import art or replace existing photos.
    plain=api.post('/api/v1/inventory',json={'title':'Synthetic without artwork'}).json()
    assert api.get(f"/api/v1/inventory/{plain['id']}/photos").json()==[]

@pytest.mark.parametrize('cover,kind',[(COVER,'comic'),({'provider':'uninstalled','candidate_id':ID},'record'),({'provider':'musicbrainz','candidate_id':'not-a-uuid'},'record'),({**COVER,'url':'http://private.invalid'},'record')])
def test_invalid_cover_never_creates_a_copy(client,cover,kind):
    api,connection,root=client;before=connection.scalar(text('SELECT count(*) FROM owned_copies'))
    assert api.post('/api/v1/inventory',json={'title':'Synthetic rejected cover','collection_type':kind,'catalog_cover':cover}).status_code==422
    assert connection.scalar(text('SELECT count(*) FROM owned_copies'))==before
    assert not list(root.rglob('*.jpg'))

def test_provider_failure_rolls_back_new_copy_and_existing_details(client,monkeypatch):
    api,connection,root=client
    copy=api.post('/api/v1/inventory',json={'title':'Synthetic original','collection_type':'record'}).json()
    def fail(ident):raise LookupUnavailable()
    monkeypatch.setitem(PROVIDERS['musicbrainz'],'cover',fail)
    before=connection.scalar(text('SELECT count(*) FROM owned_copies'))
    assert api.post('/api/v1/inventory',json={'title':'Synthetic failed create','collection_type':'record','catalog_cover':COVER}).status_code==422
    assert connection.scalar(text('SELECT count(*) FROM owned_copies'))==before
    p={'title':'Must roll back','edition_label':None,'expected_details_revision':0,'expected_identification_revision':0,'catalog_cover':COVER}
    assert api.post(f"/api/v1/inventory/{copy['id']}/details",json=p).status_code==422
    assert api.get(f"/api/v1/inventory/{copy['id']}").json()['title']==copy['title']
    assert api.get(f"/api/v1/inventory/{copy['id']}/detail-history").json()==[]
    assert not list(root.rglob('*.jpg'))

def test_stale_details_do_not_fetch_or_attach_artwork(client,monkeypatch):
    api,connection,root=client;copy=api.post('/api/v1/inventory',json={'title':'Synthetic stale','collection_type':'record'}).json();calls=[]
    monkeypatch.setitem(PROVIDERS['musicbrainz'],'cover',lambda ident:calls.append(ident))
    p={'title':'Stale','edition_label':None,'expected_details_revision':1,'expected_identification_revision':0,'catalog_cover':COVER}
    assert api.post(f"/api/v1/inventory/{copy['id']}/details",json=p).status_code==409
    assert calls==[]

def test_cover_commit_failure_removes_uncommitted_file_and_copy(client,monkeypatch):
    api,connection,root=client;before=connection.scalar(text('SELECT count(*) FROM owned_copies'));original=Session.commit
    def fail(db):
        if any(isinstance(obj,MediaAsset) for obj in db.new):raise RuntimeError('Synthetic cover commit failure')
        return original(db)
    monkeypatch.setattr(Session,'commit',fail)
    with pytest.raises(RuntimeError,match='Synthetic cover commit failure'):api.post('/api/v1/inventory',json={'title':'Synthetic rollback','collection_type':'record','catalog_cover':COVER})
    assert connection.scalar(text('SELECT count(*) FROM owned_copies'))==before and not list(root.rglob('*.jpg'))

@pytest.mark.parametrize('source',['http://musicbrainz.org/release/x','https://private.invalid/x','https://user@musicbrainz.org/x','https://musicbrainz.org:bad/x'])
def test_adapter_source_must_stay_on_registered_https_origin(client,monkeypatch,source):
    api,connection,root=client;before=connection.scalar(text('SELECT count(*) FROM owned_copies'))
    monkeypatch.setitem(PROVIDERS['musicbrainz'],'source_url',lambda ident:source)
    assert api.post('/api/v1/inventory',json={'title':'Synthetic unsafe source','collection_type':'record','catalog_cover':COVER}).status_code==422
    assert connection.scalar(text('SELECT count(*) FROM owned_copies'))==before

def test_disabled_cover_and_invalid_image_do_not_save_inventory(client,monkeypatch):
    from relicrat.collection_types import COLLECTION_TYPES
    api,connection,root=client;before=connection.scalar(text('SELECT count(*) FROM owned_copies'));config=COLLECTION_TYPES['record'].lookup
    monkeypatch.setattr(config,'cover_art',False)
    payload={'title':'Synthetic disabled art','collection_type':'record','catalog_cover':COVER}
    assert api.post('/api/v1/inventory',json=payload).status_code==422
    monkeypatch.setattr(config,'cover_art',True);monkeypatch.setitem(PROVIDERS['musicbrainz'],'cover',lambda ident:b'<svg>not image bytes</svg>')
    assert api.post('/api/v1/inventory',json=payload).status_code==422
    assert connection.scalar(text('SELECT count(*) FROM owned_copies'))==before


def test_lost_commit_ack_keeps_committed_cover_and_file(tmp_path,monkeypatch):
    """Real independent commits are required; a savepoint cannot prove this case."""
    import os
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine,select
    from auth_helpers import sign_in
    from relicrat.database import get_db
    from relicrat.main import app
    from relicrat.models import OwnedCopy
    engine=create_engine(os.environ['TEST_DATABASE_URL']);monkeypatch.setenv('MEDIA_ROOT',str(tmp_path));original=Session.commit;created=[]
    def override():
        with Session(engine,expire_on_commit=False) as db:yield db
    def lost_ack(db):
        assets=[obj for obj in db.new if isinstance(obj,MediaAsset)]
        original(db)
        if assets:
            created.extend((obj.id,obj.owned_copy_id,obj.storage_key) for obj in assets)
            raise RuntimeError('Synthetic lost commit acknowledgement')
    app.dependency_overrides[get_db]=override
    try:
        with TestClient(app) as api:
            sign_in(api);monkeypatch.setattr(Session,'commit',lost_ack)
            with pytest.raises(RuntimeError,match='Synthetic lost commit acknowledgement'):
                api.post('/api/v1/inventory',json={'title':'Synthetic uncertain commit','collection_type':'record','catalog_cover':COVER})
        assert len(created)==1
        with Session(engine) as db:
            ident,cid,key=created[0];assert db.get(MediaAsset,ident) is not None and db.get(OwnedCopy,cid) is not None
            assert (tmp_path/key).read_bytes()==image()
    finally:
        monkeypatch.setattr(Session,'commit',original);app.dependency_overrides.pop(get_db,None)
        with engine.begin() as db:
            for ident,cid,key in created:
                db.execute(text('DELETE FROM media_assets WHERE id=:id'),{'id':ident});db.execute(text('DELETE FROM owned_copies WHERE id=:id'),{'id':cid})
        engine.dispose()
