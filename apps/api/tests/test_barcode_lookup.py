"""Generated provider responses only; never contact a provider or use owner data."""
import copy,io,json,os,threading
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session
from PIL import Image
from auth_helpers import sign_in
from relicrat import musicbrainz
from relicrat.barcodes import BarcodeReading
from relicrat.barcode_providers import PROVIDERS
from relicrat.collection_types import COLLECTION_TYPES,CollectionType
from relicrat.database import get_db
from relicrat.main import app

READING={'value':'012345678905','format':'UPC_A'}
ID='11111111-1111-4111-8111-111111111111'


def release(**values):
    return {'id':ID,'title':'Synthetic album','barcode':READING['value'],
            'artist-credit':[{'name':'Synthetic artist','joinphrase':' & '},{'artist':{'name':'Other artist'}}],
            'media':[{'format':'12" Vinyl'}],'date':'2020','country':'GB',
            'label-info':[{'label':{'name':'Synthetic label'},'catalog-number':'TEST-1'}],**values}


@pytest.fixture(autouse=True)
def isolated_rate(monkeypatch):
    monkeypatch.setattr(musicbrainz,'_last_request',float('-inf'))
    monkeypatch.setattr(musicbrainz,'_gate',threading.Lock())


def test_parse_exact_matches_unknowns_leading_zeroes_and_hostile_metadata():
    reading=BarcodeReading(**READING)
    data={'releases':[release(barcode='wrong'),release(id='not-a-uuid'),release(barcode='0'+READING['value']),release()]}
    rows=musicbrainz.parse_releases(data,reading,5)
    assert len(rows)==1 and rows[0]['fields']['artist']=='Synthetic artist & Other artist'
    assert rows[0]['fields']['format']=='12" Vinyl' and rows[0]['fields']['catalog_number']=='TEST-1'
    assert rows[0]['source_url']=='https://musicbrainz.org/release/'+ID
    row=release(**{'artist-credit':None,'media':None,'label-info':None,'country':'bad\x00country','date':None,'title':'<script>literal</script>'})
    assert musicbrainz.parse_releases({'releases':[row]},reading,5)[0]['fields']=={'title':'<script>literal</script>'}
    for data in ([],{}, {'releases':None}):
        with pytest.raises(musicbrainz.LookupUnavailable):musicbrainz.parse_releases(data,reading,5)
    assert musicbrainz.barcode_variants(BarcodeReading(value='0012345678905',format='EAN_13'))=={'0012345678905','012345678905'}
    assert musicbrainz.barcode_variants(BarcodeReading(value='01234565',format='UPC_E'))=={'01234565'}


def test_request_is_bounded_fixed_origin_and_rate_limited(monkeypatch):
    requests=[]
    def fetch(url,maximum):requests.append((url,maximum));return json.dumps({'releases':[release()]}).encode()
    monkeypatch.setattr(musicbrainz,'fetch_bytes',fetch)
    assert len(musicbrainz.search(BarcodeReading(**READING),5))==1
    assert requests[0][0].startswith('https://musicbrainz.org/ws/2/release/?') and '012345678905' in requests[0][0]
    assert requests[0][1]==1024*1024
    with pytest.raises(musicbrainz.LookupBusy):musicbrainz.search(BarcodeReading(**READING),5)
    assert len(requests)==1
    musicbrainz._gate.acquire()
    try:
        with pytest.raises(musicbrainz.LookupBusy):musicbrainz.search(BarcodeReading(**READING),5)
    finally:musicbrainz._gate.release()


@pytest.mark.parametrize('content',[b'bad',b'[]',b'{"releases":null}'])
def test_malformed_provider_does_not_become_an_empty_success(monkeypatch,content):
    monkeypatch.setattr(musicbrainz,'fetch_bytes',lambda *args:content)
    with pytest.raises(musicbrainz.LookupUnavailable):musicbrainz.search(BarcodeReading(**READING),5)


def test_transport_rejects_redirects_private_hosts_and_oversize(monkeypatch):
    observed=[];mode='ok'
    def handle(request):
        observed.append(request)
        if mode=='redirect':return httpx.Response(302,headers={'location':'http://127.0.0.1/private'})
        if mode=='large':return httpx.Response(200,content=b'x'*20)
        return httpx.Response(200,content=b'{}')
    real=httpx.Client
    def client(**kwargs):
        assert kwargs['follow_redirects'] is False and kwargs['trust_env'] is False
        assert set(kwargs['headers'])=={'User-Agent','Accept','Accept-Encoding'}
        return real(transport=httpx.MockTransport(handle),**kwargs)
    monkeypatch.setattr(musicbrainz.httpx,'Client',client)
    assert musicbrainz.fetch_bytes('https://musicbrainz.org/ws/2/release/',100)==b'{}'
    assert 'RelicRat/' in observed[0].headers['User-Agent'] and not observed[0].headers.get('Authorization')
    mode='redirect'
    with pytest.raises(musicbrainz.LookupUnavailable):musicbrainz.fetch_bytes('https://musicbrainz.org/ws/2/release/',100)
    with pytest.raises(musicbrainz.LookupUnavailable):musicbrainz.fetch_bytes('https://coverartarchive.org/release/'+ID+'/front-250',100,cover=True)
    assert len(observed)==3  # Redirect destination was never contacted.
    for url in ('https://127.0.0.1/a','http://musicbrainz.org/a','https://musicbrainz.org:444/a','https://user@musicbrainz.org/a'):
        with pytest.raises(musicbrainz.LookupUnavailable):musicbrainz.fetch_bytes(url,100)
    mode='large'
    with pytest.raises(musicbrainz.LookupUnavailable):musicbrainz.fetch_bytes('https://musicbrainz.org/ws/2/release/',10)


def test_cover_is_transcoded_and_never_accepts_arbitrary_identifiers(monkeypatch):
    image=io.BytesIO();Image.new('RGB',(8,8),'blue').save(image,format='PNG')
    calls=[]
    def fetch(url,maximum,**kwargs):calls.append(url);return image.getvalue()
    monkeypatch.setattr(musicbrainz,'fetch_bytes',fetch)
    assert musicbrainz.cover(ID).startswith(b'\xff\xd8')
    with pytest.raises(musicbrainz.LookupUnavailable):musicbrainz.cover('../private')
    assert calls==['https://coverartarchive.org/release/'+ID+'/front-250']
    monkeypatch.setattr(musicbrainz,'fetch_bytes',lambda *args,**kwargs:b'<svg>bad</svg>')
    with pytest.raises(musicbrainz.LookupUnavailable):musicbrainz.cover(ID)


def test_configs_swap_installed_adapter_and_disable_without_arbitrary_urls(monkeypatch):
    data=COLLECTION_TYPES['record'].model_dump()
    monkeypatch.setitem(PROVIDERS,'synthetic',{'label':'Synthetic','fields':{'name','creator'},'source_origin':'https://catalog.invalid','search':lambda *args:[]})
    data['lookup']={'provider':'synthetic','action_label':'Find details','max_results':3,'field_mappings':{'title':'name','artist':'creator'}}
    assert CollectionType.model_validate(data).lookup.provider=='synthetic'
    data['lookup']=None;assert CollectionType.model_validate(data).lookup is None
    for patch in ({'provider':'https://private.invalid'},{'provider':'uninstalled'},{'field_mappings':{'price':'title'}},{'field_mappings':{'title':'password'}},{'max_results':0},{'max_results':True},{'url':'https://internal.invalid'},{'value_maps':{'title':{'x':'a'*501}}},{'value_maps':{'publisher':{'x':'y'}}}):
        value=copy.deepcopy(COLLECTION_TYPES['record'].model_dump());value['lookup'].update(patch)
        with pytest.raises(ValidationError):CollectionType.model_validate(value)


@pytest.fixture
def api(monkeypatch):
    url=os.getenv('TEST_DATABASE_URL')
    if not url:pytest.skip('TEST_DATABASE_URL not configured')
    engine=create_engine(url)
    def override():
        with Session(engine,expire_on_commit=False) as db:yield db
    app.dependency_overrides[get_db]=override
    try:
        with TestClient(app) as client:
            sign_in(client);yield client,engine
    finally:app.dependency_overrides.pop(get_db,None);engine.dispose()


def test_owner_only_read_only_lookup_maps_values_and_cover_without_persistence(api,monkeypatch):
    client,engine=api;calls=[]
    def search(reading,limit):calls.append((reading,limit));return musicbrainz.parse_releases({'releases':[release()]},reading,limit)
    monkeypatch.setitem(PROVIDERS['musicbrainz'],'search',search)
    monkeypatch.setitem(PROVIDERS['musicbrainz'],'cover',lambda ident:b'\xff\xd8synthetic')
    with engine.connect() as db:
        def counts():return {t:db.scalar(text('SELECT count(*) FROM '+t)) for t in ['owned_copies','catalog_items','releases','copy_detail_events','media_assets']}
        before=counts()
        result=client.post('/api/v1/barcode-lookups/record',json=READING)
        assert result.status_code==200,result.text
        row=result.json()['candidates'][0]
        assert row['fields']=={'title':'Synthetic album','artist':'Synthetic artist & Other artist','format':'Vinyl'}
        assert row['cover_url']=='/api/v1/barcode-lookups/record/'+ID+'/cover'
        cover=client.get(row['cover_url']);assert cover.status_code==200 and cover.headers['content-type']=='image/jpeg'
        assert client.post('/api/v1/barcode-lookups/comic',json=READING).status_code==404
        assert client.post('/api/v1/barcode-lookups/record',json={**READING,'url':'https://internal.invalid'}).status_code==422
        assert client.post('/api/v1/barcode-lookups/record',json={**READING,'value':123}).status_code==422
        assert len(calls)==1 and counts()==before
    client.headers.pop('Authorization')
    assert client.post('/api/v1/barcode-lookups/record',json=READING).status_code==401
    assert client.get(row['cover_url']).status_code==401
    assert len(calls)==1


@pytest.mark.parametrize('error,status',[(musicbrainz.LookupBusy,429),(musicbrainz.LookupUnavailable,503),(musicbrainz.LookupTimeout,504)])
def test_provider_failure_is_explicit_and_does_not_include_upstream_details(api,monkeypatch,error,status):
    client,_=api
    def fail(*args):raise error('untrusted upstream credentials and text')
    monkeypatch.setitem(PROVIDERS['musicbrainz'],'search',fail)
    response=client.post('/api/v1/barcode-lookups/record',json=READING)
    assert response.status_code==status and 'credentials' not in response.text


def test_cover_redirects_are_bounded_and_compression_is_rejected(monkeypatch):
    mode='valid';seen=[]
    def handle(request):
        seen.append(str(request.url))
        if mode=='encoding':return httpx.Response(200,headers={'content-encoding':'br'},content=b'not-brotli')
        if mode=='loop':return httpx.Response(307,headers={'location':str(request.url)})
        if request.url.host=='coverartarchive.org':return httpx.Response(307,headers={'location':'https://archive.org/download/test.jpg'})
        return httpx.Response(200,content=b'synthetic image bytes')
    real=httpx.Client
    monkeypatch.setattr(musicbrainz.httpx,'Client',lambda **kwargs:real(transport=httpx.MockTransport(handle),**kwargs))
    assert musicbrainz.fetch_bytes('https://coverartarchive.org/release/'+ID+'/front-250',100,cover=True)==b'synthetic image bytes'
    assert len(seen)==2 and seen[-1]=='https://archive.org/download/test.jpg'
    seen.clear();mode='loop'
    with pytest.raises(musicbrainz.LookupUnavailable):musicbrainz.fetch_bytes('https://coverartarchive.org/release/'+ID+'/front-250',100,cover=True)
    assert len(seen)==4
    mode='encoding'
    with pytest.raises((musicbrainz.LookupUnavailable,httpx.DecodingError)):musicbrainz.fetch_bytes('https://musicbrainz.org/ws/2/release/',100)


@pytest.mark.parametrize('source_url',['http://musicbrainz.org/release/x','https://musicbrainz.org:bad/x','https://private.invalid/x','https://user@musicbrainz.org/x'])
def test_untrusted_candidate_source_links_are_not_returned(api,monkeypatch,source_url):
    client,_=api;reading=BarcodeReading(**READING)
    row=musicbrainz.parse_releases({'releases':[release()]},reading,5)[0];row['source_url']=source_url
    monkeypatch.setitem(PROVIDERS['musicbrainz'],'search',lambda *args:[row])
    result=client.post('/api/v1/barcode-lookups/record',json=READING)
    assert result.status_code==200 and result.json()['candidates']==[]


def test_transport_allows_slower_reads_but_rejects_exhausted_redirect_budget(monkeypatch):
    clock=[0.0];seen=[];mode='slow'
    monkeypatch.setattr(musicbrainz.time,'monotonic',lambda:clock[0])
    def handle(request):
        seen.append(request.extensions['timeout'])
        if mode=='slow':clock[0]+=6;return httpx.Response(200,content=b'{}')
        if len(seen)==1:clock[0]+=9;return httpx.Response(307,headers={'location':'https://archive.org/test.jpg'})
        clock[0]+=4;return httpx.Response(200,content=b'not accepted after deadline')
    real=httpx.Client
    monkeypatch.setattr(musicbrainz.httpx,'Client',lambda **kwargs:real(transport=httpx.MockTransport(handle),**kwargs))
    assert musicbrainz.fetch_bytes('https://musicbrainz.org/ws/2/release/',100)==b'{}'
    assert seen[0]['read']==8 and seen[0]['connect']==3
    clock[0]=0;seen.clear();mode='redirect'
    with pytest.raises(musicbrainz.LookupTimeout):musicbrainz.fetch_bytes('https://coverartarchive.org/release/'+ID+'/front-250',100,cover=True)
    assert len(seen)==2 and seen[1]['read']==3 and seen[1]['connect']==3


def test_body_deadline_is_checked_after_each_chunk(monkeypatch):
    clock=[0.0];monkeypatch.setattr(musicbrainz.time,'monotonic',lambda:clock[0])
    class SlowBody(httpx.SyncByteStream):
        def __iter__(self):clock[0]=13;yield b'late'
    real=httpx.Client
    monkeypatch.setattr(musicbrainz.httpx,'Client',lambda **kwargs:real(transport=httpx.MockTransport(lambda request:httpx.Response(200,stream=SlowBody())),**kwargs))
    with pytest.raises(musicbrainz.LookupTimeout):musicbrainz.fetch_bytes('https://musicbrainz.org/ws/2/release/',100)


def test_upstream_throttle_is_busy_and_timeout_diagnostics_never_log_inputs(monkeypatch,caplog):
    # Alembic migration tests can disable existing loggers in this shared process.
    monkeypatch.setattr(musicbrainz.logger,'disabled',False)
    caplog.set_level('WARNING',logger=musicbrainz.__name__)
    real=httpx.Client;mode='busy'
    def handle(request):
        if mode=='busy':return httpx.Response(429,content=b'untrusted provider body')
        raise httpx.ReadTimeout('untrusted provider body '+READING['value'])
    monkeypatch.setattr(musicbrainz.httpx,'Client',lambda **kwargs:real(transport=httpx.MockTransport(handle),**kwargs))
    with pytest.raises(musicbrainz.LookupBusy):musicbrainz.search(BarcodeReading(**READING),5)
    musicbrainz._last_request=float('-inf');mode='timeout'
    with pytest.raises(musicbrainz.LookupTimeout):musicbrainz.search(BarcodeReading(**READING),5)
    assert 'Catalog search timeout' in caplog.text
    assert READING['value'] not in caplog.text and 'untrusted provider body' not in caplog.text
