"""Generated GTINHub replies only; never use owner barcodes or contact providers."""
import json,threading
import httpx
import pytest
from sqlalchemy import text
from test_inventory_api import client
from relicrat import gtinhub
from relicrat.barcodes import BarcodeReading
from relicrat.barcode_errors import LookupBusy,LookupTimeout,LookupUnavailable
from relicrat.barcode_providers import PROVIDERS
from relicrat.collection_types import COLLECTION_TYPES,CollectionType

READING=BarcodeReading(value='012345678905',format='UPC_A')
def payload(**changes):
    return {'found':True,'product':{'gtin':'0012345678905','name':'Synthetic film [4K]',
        'brand':'Brand is not studio','category':'DVDs & Videos',
        'raw_data':{'product':{'ean':123,'imageUrl':'http://127.0.0.1/private'}},**changes}}

@pytest.fixture(autouse=True)
def isolated_rate(monkeypatch):
    monkeypatch.setattr(gtinhub,'_last_request',float('-inf'))
    monkeypatch.setattr(gtinhub,'_gate',threading.Lock())

def test_exact_gtin_unknowns_and_bounded_title_only_mapping():
    rows=gtinhub.parse_product(payload(),READING,5)
    assert len(rows)==1 and rows[0]['id']=='0012345678905'
    assert rows[0]['fields']=={'title':'Synthetic film [4K]'}
    assert rows[0]['source_url']=='https://gtinhub.com/product/0012345678905'
    assert 'Brand is not studio' in rows[0]['description']
    assert gtinhub.parse_product(payload(gtin=READING.value),READING,5)==rows
    assert gtinhub.parse_product(payload(),BarcodeReading(value='0012345678905',format='EAN_13'),5)==rows
    assert gtinhub.parse_product(payload(),BarcodeReading(value='01234565',format='UPC_E'),5)==[]
    assert gtinhub.parse_product({'found':False},READING,5)==[]

@pytest.mark.parametrize('changes',[{'gtin':123},{'gtin':'1234567890128'},{'gtin':'00012345678905'},
    {'gtin':' 0012345678905'},{'gtin':None},{'gtin':'../private'},
    {'name':''},{'name':'x'*501},{'name':'bad\x00title'},{'name':7}])
def test_rejects_fuzzy_numeric_packaging_or_hostile_candidates(changes):
    assert gtinhub.parse_product(payload(**changes),READING,5)==[]

@pytest.mark.parametrize('data',[[],{}, {'found':'true','product':{}},{'found':True,'product':None},
    {'found':False,'product':{'gtin':'0012345678905'}}])
def test_malformed_response_is_unavailable(data):
    with pytest.raises(LookupUnavailable):gtinhub.parse_product(data,READING,5)

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
        if mode=='notfound':return httpx.Response(404,json={'found':False})
        if mode=='wrong404':return httpx.Response(404,json={'code':'WRONG_ENDPOINT'})
        if mode=='redirect':return httpx.Response(302,headers={'location':'http://127.0.0.1/private'})
        if mode=='encoding':headers['Content-Encoding']='gzip'
        if mode=='html':headers['Content-Type']='text/html'
        body=b'x'*(1024*1024+1) if mode=='large' else b'bad' if mode=='badjson' else json.dumps(payload()).encode()
        # Keep the compressed stream raw so the adapter checks headers before decoding.
        return httpx.Response(200,headers=headers,stream=httpx.ByteStream(body))
    real=httpx.Client
    def client(**kwargs):
        assert kwargs['follow_redirects'] is False and kwargs['trust_env'] is False
        assert set(kwargs['headers'])=={'User-Agent','Accept','Accept-Encoding'}
        return real(transport=httpx.MockTransport(handle),**kwargs)
    monkeypatch.setattr(gtinhub.httpx,'Client',client)
    if expected:
        with pytest.raises(expected):gtinhub.search(READING,5)
    else:
        result=gtinhub.search(READING,5);assert len(result)==(0 if mode=='notfound' else 1)
    assert len(requests)==1
    request=requests[0]
    assert str(request.url)=='https://gtinhub.com/api/v1/product/012345678905'
    assert request.headers['accept-encoding']=='identity'
    assert 'authorization' not in request.headers and 'cookie' not in request.headers
    assert 'user_key' not in request.headers


def test_sustained_rate_concurrency_and_provider_cooldown(monkeypatch):
    clock=[0.0];calls=[]
    monkeypatch.setattr(gtinhub.time,'monotonic',lambda:clock[0])
    def fetch(reading):calls.append(reading);return {'found':False}
    monkeypatch.setattr(gtinhub,'fetch',fetch)
    gtinhub.search(READING,5)
    clock[0]=9.9
    with pytest.raises(LookupBusy) as error:gtinhub.search(READING,5)
    assert error.value.retry_after==10 and len(calls)==1
    clock[0]=10;gtinhub.search(READING,5);assert len(calls)==2
    gtinhub._gate.acquire()
    try:
        with pytest.raises(LookupBusy):gtinhub.search(READING,5)
    finally:gtinhub._gate.release()
    def busy(reading):raise LookupBusy(retry_after=60)
    clock[0]=20;monkeypatch.setattr(gtinhub,'fetch',busy)
    with pytest.raises(LookupBusy):gtinhub.search(READING,5)
    assert gtinhub._last_request==70
    clock[0]=79
    with pytest.raises(LookupBusy):gtinhub.search(READING,5)
    monkeypatch.setattr(gtinhub,'fetch',fetch);clock[0]=80;gtinhub.search(READING,5)


def test_elapsed_headers_and_chunk_deadlines(monkeypatch):
    clock=[0.0];monkeypatch.setattr(gtinhub.time,'monotonic',lambda:clock[0]);real=httpx.Client
    def handle(request):clock[0]=13;return httpx.Response(200,json={'found':False})
    monkeypatch.setattr(gtinhub.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(handle),**kw))
    with pytest.raises(LookupTimeout):gtinhub.search(READING,5)
    gtinhub._last_request=float('-inf');clock[0]=0
    class Slow(httpx.SyncByteStream):
        def __iter__(self):
            clock[0]=13;yield b'x'*16384
    monkeypatch.setattr(gtinhub.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-type':'application/json'},stream=Slow())),**kw))
    with pytest.raises(LookupTimeout):gtinhub.search(READING,5)


def test_config_selected_provider_is_private_read_only_swappable_and_can_be_disabled(client,monkeypatch):
    api,db=client;calls=[]
    def search(reading,limit):calls.append(reading);return gtinhub.parse_product(payload(),reading,limit)
    monkeypatch.setitem(PROVIDERS['gtinhub'],'search',search)
    definition=COLLECTION_TYPES['movie'].model_dump();assert definition['lookup']['provider']=='gtinhub'
    assert definition['lookup']['field_mappings']=={'title':'title'} and not definition['lookup']['cover_art']
    swapped={**definition,'lookup':{**definition['lookup'],'provider':'upcitemdb'}}
    assert CollectionType.model_validate(swapped).lookup.provider=='upcitemdb'
    assert CollectionType.model_validate({**definition,'lookup':None}).lookup is None
    tables=['owned_copies','catalog_items','releases','media_assets','copy_detail_events']
    before={t:db.scalar(text('SELECT count(*) FROM '+t)) for t in tables}
    result=api.post('/api/v1/barcode-lookups/movie',json=READING.model_dump());assert result.status_code==200
    row=result.json()['candidates'][0];assert result.json()['provider_label']=='GTINHub'
    assert row['fields']=={'title':'Synthetic film [4K]'} and row['cover_url'] is None
    assert api.get('/api/v1/barcode-lookups/movie/0012345678905/cover').status_code==404
    assert {t:db.scalar(text('SELECT count(*) FROM '+t)) for t in tables}==before
    api.headers.pop('Authorization')
    assert api.post('/api/v1/barcode-lookups/movie',json=READING.model_dump()).status_code==401
    assert len(calls)==1
