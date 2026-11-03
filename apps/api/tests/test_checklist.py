"""Explicit qualifying matches, distinct progress and retained review history."""
import importlib.util,json,os,uuid
from pathlib import Path
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_inventory_api import client
from test_custom_collections import activate,proposal
pytestmark=pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='TEST_DATABASE_URL not configured')


def add(api,cid,title='Synthetic figure'):
    response=api.post(f'/api/v1/custom-collections/{cid}/copies',json={'request_id':str(uuid.uuid4()),'title':title,'custom_details':{}})
    assert response.status_code==200,response.text
    return response.json()['id']


def match(api,cid,copy,entry='leonardo',confirmed=True,revision=0):
    return api.post(f'/api/v1/custom-collections/{cid}/copies/{copy}/checklist-match',json={'entry_id':entry,'confirmed':confirmed,'expected_revision':revision})


def test_only_explicit_confirmed_owned_matches_count_once(client):
    api,db=client;cid=activate(api)['id'];a=add(api,cid,'Leonardo');b=add(api,cid,'Duplicate Leonardo');c=add(api,cid,'Donatello')
    url=f'/api/v1/custom-collections/{cid}/progress'
    initial=api.get(url).json();assert initial['completed']==0 and initial['total']==10 and initial['unassigned_copies']==3
    assert match(api,cid,a,confirmed=False).status_code==200
    pending=api.get(url).json();assert pending['completed']==0 and pending['entries'][0]['pending_copies']==1
    assert match(api,cid,a,revision=1).status_code==200
    assert match(api,cid,b).status_code==200
    progress=api.get(url).json();assert progress['completed']==1 and progress['entries'][0]['confirmed_copies']==2
    assert progress['unassigned_copies']==1
    assert match(api,cid,c,'donatello').status_code==200
    assert api.get(url).json()['completed']==2
    for status in ['sold','traded','lost']:
        db.execute(text('UPDATE owned_copies SET ownership_status=:status WHERE id=:id'),{'id':c,'status':status})
        assert api.get(url).json()['completed']==1
    db.execute(text("UPDATE owned_copies SET ownership_status='owned',deleted_at=now() WHERE id=:id"),{'id':c})
    assert api.get(url).json()['completed']==1
    db.execute(text('UPDATE owned_copies SET deleted_at=NULL WHERE id=:id'),{'id':c})
    assert api.get(url).json()['completed']==2


def test_reassignment_clear_history_noop_and_stale_review(client):
    api,db=client;cid=activate(api)['id'];copy=add(api,cid)
    path=f'/api/v1/custom-collections/{cid}/copies/{copy}'
    assert api.get(path+'/checklist-match').json()['revision']==0
    assert match(api,cid,copy,None,False).json()['revision']==0
    assert api.get(path+'/checklist-history').json()==[]
    assert match(api,cid,copy).json()['revision']==1
    assert match(api,cid,copy,revision=1).json()['revision']==1
    assert len(api.get(path+'/checklist-history').json())==1
    assert match(api,cid,copy,'donatello',False,1).json()['revision']==2
    assert api.get(f'/api/v1/custom-collections/{cid}/progress').json()['completed']==0
    assert match(api,cid,copy,None,False,2).json()['revision']==3
    assert match(api,cid,copy,'leonardo',True,2).status_code==409
    rows=api.get(path+'/checklist-history?limit=1&offset=1').json();assert len(rows)==1 and rows[0]['revision']==2 and rows[0]['before_entry_id']=='leonardo' and rows[0]['after_entry_id']=='donatello' and rows[0]['before_confirmed'] and not rows[0]['after_confirmed']
    assert api.get(path+'/checklist-match').json()['entry_id'] is None
    assert len(api.get(path+'/checklist-history').json())==3
    with pytest.raises(IntegrityError):
        with db.begin_nested():db.execute(text('UPDATE checklist_match_events SET after_confirmed=false'))
    with pytest.raises(IntegrityError):
        with db.begin_nested():db.execute(text('DELETE FROM checklist_matches'))


def test_invalid_cross_collection_and_inactive_matches_rejected(client):
    api,db=client;cid=activate(api)['id'];copy=add(api,cid)
    other=proposal();other['collection']['id']='second-goal';othercid=activate(api,other)['id']
    assert match(api,othercid,copy).status_code==404
    assert match(api,cid,copy,'not-in-checklist').status_code==422
    assert match(api,cid,copy,None,True).status_code==422
    for bad in [{'confirmed':1},{'expected_revision':True},{'expected_revision':-1},{'owned':True}]:
        payload={'entry_id':'leonardo','confirmed':True,'expected_revision':0}|bad
        assert api.post(f'/api/v1/custom-collections/{cid}/copies/{copy}/checklist-match',json=payload).status_code==422
    db.execute(text("UPDATE owned_copies SET ownership_status='sold' WHERE id=:id"),{'id':copy})
    assert match(api,cid,copy).status_code==422
    assert api.get(f'/api/v1/custom-collections/{cid}/progress').json()['completed']==0
    assert db.execute(text('SELECT count(*) FROM checklist_match_events')).scalar()==0


def test_database_enforces_membership_entry_revision_and_audits_direct_sql(client):
    api,db=client;cid=activate(api)['id'];copy=add(api,cid)
    other=proposal();other['collection']['id']='other-goal';othercid=activate(api,other)['id']
    sql='INSERT INTO checklist_matches(owned_copy_id,collection_id,entry_id,confirmed,revision) VALUES (:copy,:collection,:entry,:confirmed,:revision)'
    base={'copy':copy,'collection':cid,'entry':'leonardo','confirmed':True,'revision':1}
    for bad in [{'collection':othercid},{'entry':'unknown'},{'revision':2},{'entry':None}]:
        with pytest.raises(IntegrityError):
            with db.begin_nested():db.execute(text(sql),base|bad)
    db.execute(text(sql),base)
    row=db.execute(text('SELECT before_entry_id,after_entry_id,before_confirmed,after_confirmed,revision FROM checklist_match_events')).one()
    assert tuple(row)==(None,'leonardo',False,True,1)
    for sql in ["UPDATE checklist_matches SET entry_id='donatello'",'UPDATE checklist_matches SET revision=revision+1']:
        with pytest.raises(IntegrityError):
            with db.begin_nested():db.execute(text(sql))
    db.execute(text("UPDATE checklist_matches SET entry_id=NULL,confirmed=false,revision=revision+1"))
    assert db.execute(text('SELECT count(*) FROM checklist_match_events')).scalar()==2
    db.execute(text("UPDATE owned_copies SET ownership_status='lost' WHERE id=:id"),{'id':copy})
    with pytest.raises(IntegrityError):
        with db.begin_nested():db.execute(text("UPDATE checklist_matches SET entry_id='leonardo',confirmed=true,revision=revision+1"))
    assert db.execute(text('SELECT count(*) FROM checklist_match_events')).scalar()==2


def test_progress_is_whole_collection_and_never_creates_catalog_or_copies(client):
    api,db=client;cid=activate(api)['id']
    for i in range(23):match(api,cid,add(api,cid,f'Synthetic duplicate {i}'))
    assert len(api.get(f'/api/v1/inventory?custom_collection_id={cid}&limit=1').json())==1
    p=api.get(f'/api/v1/custom-collections/{cid}/progress').json()
    assert p['completed']==1 and p['entries'][0]['confirmed_copies']==23
    assert db.execute(text('SELECT count(*) FROM owned_copies')).scalar()==23
    assert db.execute(text('SELECT count(*) FROM catalog_items')).scalar()==0
    assert db.execute(text('SELECT count(*) FROM releases')).scalar()==0


def test_populated_checklist_downgrade_refused(client):
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    api,db=client;cid=activate(api)['id'];match(api,cid,add(api,cid))
    path=Path(__file__).resolve().parents[1]/'alembic/versions/0016_checklist_progress.py'
    spec=importlib.util.spec_from_file_location('checklist_migration',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.op=Operations(MigrationContext.configure(db))
    with pytest.raises(RuntimeError,match='downgrade would lose review history'):module.downgrade()
