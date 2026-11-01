"""Generated retail responses only; no provider traffic or owner inventory."""
import json
import threading
import httpx
import pytest
from sqlalchemy import text
from test_inventory_api import client
from relicrat import upcitemdb
from relicrat.barcodes import BarcodeReading
from relicrat.barcode_errors import LookupBusy, LookupTimeout, LookupUnavailable
from relicrat.barcode_providers import PROVIDERS
from relicrat.collection_types import COLLECTION_TYPES, CollectionType

READING = BarcodeReading(value='012345678905', format='UPC_A')


def item(**changes):
    return {'ean':'0012345678905', 'upc':READING.value, 'title':'Synthetic movie [DVD]',
            'brand':'Synthetic retailer brand', 'category':'Media > DVDs & Videos',
            'images':['http://127.0.0.1/private'], 'offers':[{'price':100}], **changes}


@pytest.fixture(autouse=True)
def isolated_rate(monkeypatch):
    monkeypatch.setattr(upcitemdb, '_last_request', float('-inf'))
    monkeypatch.setattr(upcitemdb, '_gate', threading.Lock())


def test_exact_movie_candidate_preserves_identifiers_and_never_infers_studio_format_or_price():
    rows=upcitemdb.parse_items({'code':'OK','items':[item(upc='999999999999'),item(),item(ean=''),item()]},READING,5)
    assert len(rows)==1
    assert rows[0]['fields']=={'title':'Synthetic movie [DVD]'}
    assert rows[0]['id']=='0012345678905'
    assert rows[0]['source_url']=='https://www.upcitemdb.com/upc/0012345678905'
    assert 'Brand: Synthetic retailer brand' in rows[0]['description']
    assert 'confirm the movie and edition' in rows[0]['description']
    assert upcitemdb.parse_items({'code':'OK','items':[]},READING,5)==[]
    assert upcitemdb.parse_items({'code':'OK','items':[item()]},BarcodeReading(value='0012345678905',format='EAN_13'),5)==rows
    assert upcitemdb.parse_items({'code':'OK','items':[item()]},BarcodeReading(value='01234565',format='UPC_E'),5)==[]


@pytest.mark.parametrize('changes',[
    {'ean':123}, {'ean':'1234567890128'}, {'ean':' 0012345678905'},
    {'ean':'../private'}, {'ean':None,'upc':None,'gtin':'00012345678905'},
    {'title':''}, {'title':'x'*501}, {'title':'bad\x00title'}, {'title':9},
])
def test_unsafe_conflicting_or_missing_fields_are_not_candidates(changes):
    assert upcitemdb.parse_items({'code':'OK','items':[item(**changes)]},READING,5)==[]


@pytest.mark.parametrize('data',[[],{}, {'code':'OK','items':None}, {'code':'SERVER_ERR','items':[]}])
def test_malformed_success_is_an_unavailable_result(data):
    with pytest.raises(LookupUnavailable):upcitemdb.parse_items(data,READING,5)


@pytest.mark.parametrize('mode,expected',[
    ('ok',None),('notfound',None),('redirect',LookupUnavailable),('encoding',LookupUnavailable),
    ('html',LookupUnavailable),('large',LookupUnavailable),('badjson',LookupUnavailable),
    ('wrong404',LookupUnavailable),('timeout',LookupTimeout),('busy',LookupBusy),
])
def test_pinned_transport_bounds_and_errors(monkeypatch,mode,expected):
    requests=[]
    def handle(request):
        requests.append(request)
        headers={'Content-Type':'application/json'}
        if mode=='timeout':raise httpx.ReadTimeout('private upstream details',request=request)
        if mode=='busy':return httpx.Response(429,json={'code':'EXCEED_LIMIT','message':'private upstream details'})
        if mode=='notfound':return httpx.Response(404,json={'code':'NOT_FOUND'})
        if mode=='wrong404':return httpx.Response(404,json={'code':'WRONG_ENDPOINT'})
        if mode=='redirect':return httpx.Response(302,headers={'location':'http://127.0.0.1/private'})
        if mode=='encoding':headers['Content-Encoding']='gzip'
        if mode=='html':headers['Content-Type']='text/html'
        body=b'x'*(1024*1024+1) if mode=='large' else b'bad' if mode=='badjson' else json.dumps({'code':'OK','items':[item()]}).encode()
        # Keep the compressed stream raw so the adapter checks headers before decoding.
        return httpx.Response(200,headers=headers,stream=httpx.ByteStream(body))
    real=httpx.Client
    def client(**kwargs):
        assert kwargs['follow_redirects'] is False and kwargs['trust_env'] is False
        assert set(kwargs['headers'])=={'User-Agent','Accept','Accept-Encoding'}
        return real(transport=httpx.MockTransport(handle),**kwargs)
    monkeypatch.setattr(upcitemdb.httpx,'Client',client)
    if expected:
        with pytest.raises(expected):upcitemdb.search(READING,5)
    else:
        result=upcitemdb.search(READING,5);assert len(result)==(0 if mode=='notfound' else 1)
    assert len(requests)==1
    request=requests[0]
    assert str(request.url)=='https://api.upcitemdb.com/prod/trial/lookup?upc=012345678905'
    assert request.headers['accept-encoding']=='identity'
    assert 'authorization' not in request.headers and 'cookie' not in request.headers
    assert 'user_key' not in request.headers


def test_sustained_rate_concurrency_and_provider_cooldown(monkeypatch):
    clock=[0.0];calls=[]
    monkeypatch.setattr(upcitemdb.time,'monotonic',lambda:clock[0])
    def fetch(reading):calls.append(reading);return {'code':'OK','items':[]}
    monkeypatch.setattr(upcitemdb,'fetch',fetch)
    upcitemdb.search(READING,5)
    clock[0]=9.9
    with pytest.raises(LookupBusy) as error:upcitemdb.search(READING,5)
    assert error.value.retry_after==10 and len(calls)==1
    clock[0]=10;upcitemdb.search(READING,5);assert len(calls)==2
    upcitemdb._gate.acquire()
    try:
        with pytest.raises(LookupBusy):upcitemdb.search(READING,5)
    finally:upcitemdb._gate.release()
    def busy(reading):raise LookupBusy(retry_after=60)
    clock[0]=20;monkeypatch.setattr(upcitemdb,'fetch',busy)
    with pytest.raises(LookupBusy):upcitemdb.search(READING,5)
    assert upcitemdb._last_request==70
    clock[0]=79
    with pytest.raises(LookupBusy):upcitemdb.search(READING,5)
    monkeypatch.setattr(upcitemdb,'fetch',fetch);clock[0]=80;upcitemdb.search(READING,5)


def test_elapsed_headers_and_chunk_deadlines(monkeypatch):
    clock=[0.0];monkeypatch.setattr(upcitemdb.time,'monotonic',lambda:clock[0]);real=httpx.Client
    def handle(request):clock[0]=13;return httpx.Response(200,json={'code':'OK','items':[]})
    monkeypatch.setattr(upcitemdb.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(handle),**kw))
    with pytest.raises(LookupTimeout):upcitemdb.search(READING,5)
    upcitemdb._last_request=float('-inf');clock[0]=0
    class Slow(httpx.SyncByteStream):
        def __iter__(self):
            clock[0]=13;yield b'x'*16384
    monkeypatch.setattr(upcitemdb.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-type':'application/json'},stream=Slow())),**kw))
    with pytest.raises(LookupTimeout):upcitemdb.search(READING,5)


def test_movie_config_is_swappable_and_lookup_cannot_create_inventory(client,monkeypatch):
    api,db=client;calls=[]
    def search(reading,limit):calls.append(reading);return upcitemdb.parse_items({'code':'OK','items':[item()]},reading,limit)
    monkeypatch.setitem(PROVIDERS['upcitemdb'],'search',search)
    definition=COLLECTION_TYPES['movie'].model_dump();definition['lookup']['provider']='upcitemdb'
    monkeypatch.setitem(COLLECTION_TYPES,'movie',CollectionType.model_validate(definition))
    assert definition['lookup']['field_mappings']=={'title':'title'} and not definition['lookup']['cover_art']
    disabled={**definition,'lookup':None};assert CollectionType.model_validate(disabled).lookup is None
    swapped={**definition,'lookup':{**definition['lookup'],'provider':'musicbrainz'}}
    assert CollectionType.model_validate(swapped).lookup.provider=='musicbrainz'
    tables=['owned_copies','catalog_items','releases','media_assets','copy_detail_events']
    before={t:db.scalar(text('SELECT count(*) FROM '+t)) for t in tables}
    result=api.post('/api/v1/barcode-lookups/movie',json=READING.model_dump())
    assert result.status_code==200,result.text
    candidate=result.json()['candidates'][0]
    assert result.json()['provider_label']=='UPCitemdb' and candidate['cover_url'] is None
    assert candidate['fields']=={'title':'Synthetic movie [DVD]'}
    assert api.get('/api/v1/barcode-lookups/movie/0012345678905/cover').status_code==404
    assert api.post('/api/v1/barcode-lookups/movie',json={**READING.model_dump(),'url':'http://internal'}).status_code==422
    assert {t:db.scalar(text('SELECT count(*) FROM '+t)) for t in tables}==before
    def busy(*args):raise LookupBusy('untrusted secret',retry_after=60)
    monkeypatch.setitem(PROVIDERS['upcitemdb'],'search',busy)
    response=api.post('/api/v1/barcode-lookups/movie',json=READING.model_dump());assert response.status_code==429
    assert response.headers['Retry-After']=='60' and 'secret' not in response.text
    api.headers.pop('Authorization')
    assert api.post('/api/v1/barcode-lookups/movie',json=READING.model_dump()).status_code==401
    assert len(calls)==1
