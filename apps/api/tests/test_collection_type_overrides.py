"""Operator configs and synthetic adapters only; no owner records or provider calls."""
import json
import os
import subprocess
import sys
import pytest
from pydantic import ValidationError
from sqlalchemy import text
from relicrat.barcode_errors import LookupUnavailable
from relicrat.barcode_providers import PROVIDERS
from relicrat.collection_types import COLLECTION_TYPES, load_types
from test_barcode_lookup import api, READING


def write_config(root, lookup):
    value=COLLECTION_TYPES['record'].model_dump();value['lookup']=lookup
    (root/'record.json').write_text(json.dumps(value))


def test_override_selects_adapter_or_disables_without_changing_bundled_types(tmp_path,monkeypatch):
    monkeypatch.setitem(PROVIDERS,'synthetic',{'label':'Synthetic catalog','fields':{'name','creator'},'source_origin':'https://catalog.invalid','search':lambda *args:[]})
    config={'provider':'synthetic','action_label':'Find album details','max_results':3,'field_mappings':{'title':'name','artist':'creator'}}
    write_config(tmp_path,config);monkeypatch.setenv('RELICRAT_COLLECTION_TYPES_DIR',str(tmp_path))
    loaded=load_types()
    assert loaded['record'].lookup.provider=='synthetic'
    assert loaded['record'].lookup.field_mappings=={'title':'name','artist':'creator'}
    assert loaded['comic']==COLLECTION_TYPES['comic'] and loaded['other']==COLLECTION_TYPES['other']
    write_config(tmp_path,None);assert load_types()['record'].lookup is None
    monkeypatch.delenv('RELICRAT_COLLECTION_TYPES_DIR');assert load_types()['record']==COLLECTION_TYPES['record']


@pytest.mark.parametrize('mode',['missing','relative','directory','empty','unknown','malformed','duplicate','large','wrong_id','secret','url','uninstalled'])
def test_invalid_mounts_and_definitions_fail_instead_of_silent_fallback(tmp_path,monkeypatch,mode):
    monkeypatch.setenv('RELICRAT_COLLECTION_TYPES_DIR',str(tmp_path))
    value=COLLECTION_TYPES['record'].model_dump();path=tmp_path/'record.json'
    if mode=='missing':monkeypatch.setenv('RELICRAT_COLLECTION_TYPES_DIR',str(tmp_path/'missing'))
    elif mode=='relative':monkeypatch.setenv('RELICRAT_COLLECTION_TYPES_DIR','relative-config')
    elif mode=='directory':path.mkdir()
    elif mode=='empty':pass
    elif mode=='unknown':(tmp_path/'albums.json').write_text('{}')
    elif mode=='malformed':path.write_text('{')
    elif mode=='duplicate':path.write_text('{"lookup":null,"lookup":null}')
    elif mode=='large':path.write_text(' '*65537)
    else:
        if mode=='wrong_id':value['id']='comic'
        elif mode=='secret':value['lookup']['token']='synthetic-never-a-secret'
        elif mode=='url':value['lookup']['url']='http://127.0.0.1/private'
        elif mode=='uninstalled':value['lookup']['provider']='uninstalled'
        path.write_text(json.dumps(value))
    with pytest.raises((ValueError,OSError,ValidationError)):load_types()


def test_mounted_adapter_reaches_definitions_and_read_only_lookup_without_ui_branches(api,tmp_path,monkeypatch):
    client,engine=api;calls=[]
    def search(reading,limit):
        calls.append((reading.value,limit))
        return [{'id':'synthetic-1','title':'Generated album','description':'Generated variant',
                 'source_url':'https://catalog.invalid/release/synthetic-1','fields':{'name':'Generated album','creator':'Generated artist'}}]
    monkeypatch.setitem(PROVIDERS,'synthetic',{'label':'Synthetic catalog','fields':{'name','creator'},'source_origin':'https://catalog.invalid','search':search})
    config={'provider':'synthetic','action_label':'Find album details','max_results':3,'field_mappings':{'title':'name','artist':'creator'}}
    write_config(tmp_path,config);monkeypatch.setenv('RELICRAT_COLLECTION_TYPES_DIR',str(tmp_path))
    monkeypatch.setitem(COLLECTION_TYPES,'record',load_types()['record'])
    definitions=client.get('/api/v1/collection-settings/types');assert definitions.status_code==200
    assert 'synthetic' in definitions.text and 'synthetic-never-a-secret' not in definitions.text
    with engine.connect() as db:
        def counts():return {table:db.scalar(text('SELECT count(*) FROM '+table)) for table in ['owned_copies','catalog_items','releases','media_assets','copy_detail_events']}
        before=counts();response=client.post('/api/v1/barcode-lookups/record',json=READING)
        assert response.status_code==200,response.text
        value=response.json();assert value['provider']=='synthetic' and value['provider_label']=='Synthetic catalog'
        assert value['candidates'][0]['fields']=={'title':'Generated album','artist':'Generated artist'}
        assert value['candidates'][0]['cover_url'] is None and counts()==before
    assert calls==[(READING['value'],3)]
    # Failures use the same safe API contract, independent of the first adapter.
    def fail(*args):raise LookupUnavailable('untrusted provider details')
    monkeypatch.setitem(PROVIDERS['synthetic'],'search',fail)
    response=client.post('/api/v1/barcode-lookups/record',json=READING)
    assert response.status_code==503 and 'untrusted' not in response.text


def test_fresh_process_loads_config_at_startup_and_refuses_invalid_provider(tmp_path,monkeypatch):
    write_config(tmp_path,None)
    monkeypatch.setenv('RELICRAT_COLLECTION_TYPES_DIR',str(tmp_path))
    code="from relicrat.collection_types import COLLECTION_TYPES;assert COLLECTION_TYPES['record'].lookup is None;assert COLLECTION_TYPES['comic'].lookup is None"
    subprocess.run([sys.executable,'-c',code],env=os.environ.copy(),check=True,capture_output=True)
    config=COLLECTION_TYPES['record'].lookup.model_dump();config['provider']='uninstalled'
    write_config(tmp_path,config)
    result=subprocess.run([sys.executable,'-c',code],env=os.environ.copy(),capture_output=True)
    assert result.returncode!=0 and b'installed adapter' in result.stderr
