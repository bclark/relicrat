import {useEffect,useState} from 'react';
import {api,ApiError,errorText,jsonSave,type Location,type RunSave} from '../lib/inventory-client';

import AuditResolution,{type Finding,type Resolution} from './audit-resolution';

type Copy = {id:string;title:string;edition:string|null;storage_revision:number};
type RecordedResolution = {action:Resolution['action'];title:string;location_name:string;copy_id:string};
type Result = {id:string;created_at:string;copies:(Copy & {found:boolean})[];extras:string[];resolutions:Record<string,RecordedResolution>};
type Preview = {copies:Copy[];snapshot:string;latest:Result|null};
type AuditSummary = {id:string;created_at:string;found:number;missing:number;extra:number;unresolved:number};
const HISTORY_PAGE=20;

type Submission = {request_id:string;snapshot:string;found_ids:string[];extras:string[]};

type Draft = Pick<Preview,'copies'|'snapshot'> & {
  found:string[];extras:string[];extra:string;pending?:Submission;
};

function readDraft(key:string):Draft|null{
  const raw=localStorage.getItem(key);
  if(!raw)return null;
  const value=JSON.parse(raw);
  if(!value||typeof value.snapshot!=='string'||typeof value.extra!=='string'||
    !Array.isArray(value.copies)||!Array.isArray(value.found)||!Array.isArray(value.extras))throw new Error('Unreadable audit draft');
  return value;
}

function copyChanges(before:Copy[],after:Copy[]){
  const previous=new Map(before.map(copy=>[copy.id,copy]));
  const current=new Set(after.map(copy=>copy.id));
  const removed=before.filter(copy=>!current.has(copy.id));
  const added=after.filter(copy=>!previous.has(copy.id));
  const changed=after.filter(copy=>{
    const old=previous.get(copy.id);
    return old&&(old.storage_revision!==copy.storage_revision||old.title!==copy.title||old.edition!==copy.edition);
  });
  return {removed,added,changed};
}

function copyLabel(copy:Copy){
  return [copy.title,copy.edition,`Copy ${copy.id.slice(0,8)}`].filter(Boolean).join(' · ');
}

function Discrepancies({missing,extras}:{missing:Copy[];extras:string[]}){
  return <>
    <h4>Missing copies ({missing.length})</h4>
    {missing.length?<ul>{missing.map(copy=><li key={copy.id}>{copyLabel(copy)}</li>)}</ul>:<p>No missing copies.</p>}
    <h4>Extra items ({extras.length})</h4>
    {extras.length?<ul>{extras.map((extra,index)=><li key={index}>{extra}</li>)}</ul>:<p>No extra items.</p>}
  </>;
}

function resolutionLabel(resolution:RecordedResolution){
  if(resolution.action==='found')return 'Found in this box';
  if(resolution.action==='move_missing')return `Located in ${resolution.location_name}`;
  if(resolution.action==='match_extra')return `Matched ${resolution.title} and assigned it to ${resolution.location_name}`;
  return `Added ${resolution.title} to ${resolution.location_name}`;
}

export default function LocationAudit({box,busy,runSave,changed}:{box:Location;busy:boolean;runSave:RunSave;changed:()=>void}){
  const path=`storage-locations/${box.id}/audits`;
  const [finding,setFinding]=useState<Finding|null>(null);
  const [resolutionError,setResolutionError]=useState('');

  const [preview,setPreview]=useState<Preview|null>(null);
  const [latest,setLatest]=useState<Result|null>(null);
  const [older,setOlder]=useState<Result|null>(null);
  const [openLatest,setOpenLatest]=useState(false);
  const [history,setHistory]=useState<AuditSummary[]|null>(null);
  const [historyPage,setHistoryPage]=useState(0);
  const [historyError,setHistoryError]=useState('');
  const [reading,setReading]=useState(false);
  const selected=older??latest;
  const [step,setStep]=useState<'check'|'review'|'saved'>('check');
  const draftKey=`relicrat.audit-draft.v1:${box.id}`;
  const [draft,setDraft]=useState<Draft|null>(null);
  const [draftReady,setDraftReady]=useState(false);
  const [resume,setResume]=useState(false);
  const [draftError,setDraftError]=useState('');
  const [checking,setChecking]=useState(false);
  const [error,setError]=useState('');
  const [refresh,setRefresh]=useState(0);
  const found=draft?.found??[];
  const extras=draft?.extras??[];
  const extra=draft?.extra??'';
  const retry=draft?.pending;
  const outdated=!!(draft&&preview&&draft.snapshot!==preview.snapshot);
  const changes=outdated&&draft&&preview?copyChanges(draft.copies,preview.copies):null;

  useEffect(()=>{
    try{
      const saved=readDraft(draftKey);
      setDraft(saved);setResume(!!saved);
    }catch{
      setDraftError('This browser could not read the saved draft. You can still complete an audit in this tab.');
    }
    setDraftReady(true);
  },[draftKey]);

  function persist(next:Draft|null){
    setDraft(next);
    try{
      if(next)localStorage.setItem(draftKey,JSON.stringify(next));
      else localStorage.removeItem(draftKey);
      setDraftError('');
    }catch{
      setDraftError('This browser could not update the saved draft. Keep this tab open until you save.');
    }
  }

  function edit(fields:Partial<Draft>){
    if(!preview)return;
    persist({...(draft??{snapshot:preview.snapshot,copies:preview.copies,found:[],extras:[],extra:''}),...fields});
  }

  async function review(){
    if(checking||busy||!preview||outdated)return;
    if(!draft)edit({});
    setChecking(true);setError('');
    try{
      const current=await api<Preview>(path);
      setPreview(current);setLatest(current.latest);
      if(current.snapshot===preview.snapshot)setStep('review');
    }catch(problem){setError(errorText(problem));}
    finally{setChecking(false);}
  }

  function acceptChanges(){
    if(!preview||!changes)return;
    const rejected=new Set([...changes.removed,...changes.changed].map(copy=>copy.id));
    edit({snapshot:preview.snapshot,copies:preview.copies,found:found.filter(id=>!rejected.has(id))});
    setError('');setStep('check');
  }

  useEffect(()=>{
    const controller=new AbortController();
    api<Preview>(path,{signal:controller.signal}).then(result=>{
      if(!controller.signal.aborted){setPreview(result);setLatest(result.latest);}
    }).catch(problem=>{if(!controller.signal.aborted)setError(errorText(problem));});
    return()=>controller.abort();
  },[path,refresh]);

  useEffect(()=>{
    const controller=new AbortController();
    setHistoryError('');
    api<AuditSummary[]>(`${path}/history?limit=${HISTORY_PAGE+1}&offset=${historyPage*HISTORY_PAGE}`,{signal:controller.signal})
      .then(result=>{if(!controller.signal.aborted)setHistory(result);})
      .catch(problem=>{if(!controller.signal.aborted)setHistoryError(errorText(problem));});
    return()=>controller.abort();
  },[path,refresh,historyPage]);

  function changeHistoryPage(page:number){
    if(page!==historyPage){setHistory(null);setHistoryPage(page);}
  }

  function clearFinding(){
    setFinding(null);setResolutionError('');
  }

  async function openAudit(id:string){
    if(reading||busy)return;
    clearFinding();setHistoryError('');setReading(true);
    try{setOlder(await api<Result>(`${path}/${id}`));}
    catch(problem){setHistoryError(errorText(problem));}
    finally{setReading(false);}
  }

  function reset(){
    persist(null);setResume(false);setPreview(null);setStep('check');
    setError('');clearFinding();setRefresh(value=>value+1);
  }

  async function save(){
    if(!preview||busy||(!retry&&outdated))return;
    setError('');
    const submission=retry??{request_id:crypto.randomUUID(),snapshot:preview.snapshot,found_ids:found,extras};
    edit({pending:submission});
    try{
      const saved=await runSave(()=>api<Result>(path,jsonSave(submission)));
      if(saved){
        persist(null);setLatest(saved);setOlder(null);clearFinding();
        setStep('saved');changeHistoryPage(0);setRefresh(value=>value+1);
      }
    }catch(problem){
      if(problem instanceof ApiError&&!problem.uncertain){
        edit({pending:undefined});
        if(problem.status===409){setStep('check');setPreview(null);setRefresh(value=>value+1);}
      }
      setError(errorText(problem));
    }
  }

  async function resolve(action:Resolution){
    if(!selected||busy)return;
    setResolutionError('');
    try{
      const saved=await runSave(()=>api<Result>(`${path}/${selected.id}/resolutions`,jsonSave(action)));
      if(saved){
        if(older)setOlder(saved);
        else setLatest(saved);
        setFinding(null);changed();
        setRefresh(value=>value+1);
      }
    }catch(problem){setResolutionError(errorText(problem));}
  }

  function resolutionControl(key:string,item:Finding){
    const resolved=selected?.resolutions[key];
    if(resolved)return <p>Resolved · {resolutionLabel(resolved)}</p>;
    return <button type="button" disabled={busy} onClick={()=>{setResolutionError('');setFinding(item);}}>Resolve {item.title}</button>;
  }

  const missing=preview?.copies.filter(copy=>!found.includes(copy.id))??[];
  return <section aria-label="Check location contents" className="item-section">
    <h3>Check contents</h3>
    <details>
      <summary>Audit history</summary>
      {historyError&&<p role="alert" className="error">{historyError} <button type="button" onClick={()=>setRefresh(value=>value+1)}>Retry audit history</button></p>}
      {reading&&<p role="status">Opening audit…</p>}
      {!history&&!historyError?<p role="status">Loading audit history…</p>:history?.length?<ul aria-label="Saved audits">{history.slice(0,HISTORY_PAGE).map((entry,index)=><li key={entry.id}>
        <button type="button" aria-pressed={entry.id===selected?.id} disabled={busy||reading}
          onClick={()=>{if(entry.id===latest?.id){clearFinding();setOlder(null);setOpenLatest(true);}else void openAudit(entry.id);}}>
          {historyPage===0&&index===0?'Latest audit':'Past audit'} · {new Date(entry.created_at).toLocaleString()} · {entry.found} found · {entry.missing} missing · {entry.extra} extra · {entry.unresolved} unresolved
        </button>
      </li>)}</ul>:!historyError&&<p>No saved audits on this page.</p>}
      {(historyPage>0||(history?.length??0)>HISTORY_PAGE)&&<nav aria-label="Audit history pages" className="pagination">
        <button type="button" disabled={historyPage===0} onClick={()=>changeHistoryPage(historyPage-1)}>Previous</button>
        <button type="button" disabled={!history||history.length<=HISTORY_PAGE} onClick={()=>changeHistoryPage(historyPage+1)}>Next</button>
      </nav>}
    </details>
    {older&&<button type="button" disabled={busy||reading} onClick={()=>{setOlder(null);clearFinding();setOpenLatest(true);}}>Back to latest audit</button>}
    {selected&&<details key={selected.id} open={!!older||step==='saved'||openLatest||undefined}>
      <summary>{older?'Selected audit':'Last checked'} · {new Date(selected.created_at).toLocaleString()} · {selected.copies.filter(copy=>copy.found).length} found · {selected.copies.filter(copy=>!copy.found).length} missing · {selected.extras.length} extra</summary>
      <h4>Original findings</h4>
      <h5>Missing copies ({selected.copies.filter(copy=>!copy.found).length})</h5>
      <ul>{selected.copies.filter(copy=>!copy.found).map(copy=><li key={copy.id}>{copyLabel(copy)}
        {resolutionControl(`missing:${copy.id}`,{kind:'missing',id:copy.id,title:copy.title})}
      </li>)}</ul>
      <h5>Extra items ({selected.extras.length})</h5>
      <ul>{selected.extras.map((title,index)=><li key={index}><span>{title}</span>
        {resolutionControl(`extra:${index}`,{kind:'extra',index,title})}
      </li>)}</ul>
      {finding&&<AuditResolution key={finding.kind==='missing'?finding.id:finding.index} finding={finding}
        box={box} expected={new Set([...selected.copies.map(copy=>copy.id),...Object.values(selected.resolutions).map(value=>value.copy_id)])}
        busy={busy} confirm={resolve} cancel={()=>{setFinding(null);setResolutionError('');}}/>}
      {resolutionError&&<p role="alert" className="error">{resolutionError}</p>}
    </details>}
    {error&&<p role="alert" className="error">{error}</p>}
    {!preview&&!error&&<p role="status">Loading expected copies…</p>}
    {draftError&&<p role="alert" className="error">{draftError}</p>}
    {resume&&preview&&<div className="form-actions">
      <button type="button" disabled={busy} onClick={()=>{setResume(false);if(retry)setStep('review');}}>Resume audit</button>
      {!retry&&<button type="button" disabled={busy} onClick={()=>{if(window.confirm('Discard this saved draft?'))reset();}}>Discard draft</button>}
    </div>}
    {!resume&&changes&&!retry&&<section aria-label="Review box changes">
      <h4>Box contents changed</h4>
      <p>Review the changes before saving. Checks on unchanged copies and your extras are kept.</p>
      {changes.removed.length>0&&<><p>No longer expected here</p><ul>{changes.removed.map(copy=><li key={copy.id}>{copyLabel(copy)}</li>)}</ul></>}
      {changes.added.length>0&&<><p>Newly expected here</p><ul>{changes.added.map(copy=><li key={copy.id}>{copyLabel(copy)}</li>)}</ul></>}
      {changes.changed.length>0&&<><p>Check these copies again</p><ul>{changes.changed.map(copy=><li key={copy.id}>{copyLabel(copy)}</li>)}</ul></>}
      <button type="button" disabled={busy} onClick={acceptChanges}>Review current checklist</button>
    </section>}
    {step==='check'&&preview&&draftReady&&!resume&&!outdated&&<>
      <p>Mark each copy you found in this location. Unchecked copies will be recorded as missing.</p>
      <fieldset disabled={busy||checking}>
        <legend>Expected copies</legend>
        {preview.copies.length?<ul>{preview.copies.map(copy=><li key={copy.id}>
          <label><input type="checkbox" checked={found.includes(copy.id)} onChange={event=>{
            const checked=event.currentTarget.checked;
            edit({found:checked?[...found,copy.id]:found.filter(id=>id!==copy.id)});
          }}/> {copyLabel(copy)}</label>
        </li>)}</ul>:<p>No copies are expected here.</p>}
      </fieldset>
      <label htmlFor="location-audit-extra">Extra item</label>
      <input id="location-audit-extra" value={extra} maxLength={120} disabled={busy||checking||extras.length>=25}
        onChange={event=>edit({extra:event.target.value})}/>
      <button type="button" disabled={busy||checking||!extra.trim()||extras.length>=25} onClick={()=>edit({extras:[...extras,extra.trim()],extra:''})}>Add extra item</button>
      {!!extras.length&&<ul aria-label="Recorded extra items">{extras.map((item,index)=><li key={index}>{item} <button type="button" aria-label={`Remove extra item ${index+1}`} disabled={busy||checking} onClick={()=>edit({extras:extras.filter((_,i)=>i!==index)})}>Remove</button></li>)}</ul>}
      <button type="button" className="primary" disabled={busy||checking||!!extra.trim()} onClick={()=>void review()}>Review audit</button>
    </>}
    {step==='review'&&preview&&(!outdated||retry)&&<>
      {retry?<p>Retry the original submission to confirm whether the audit was saved.</p>:<>
        <p>{found.length} of {preview.copies.length} expected copies found. Saving records the observations. Use the copy’s location picker for storage changes.</p>
        <Discrepancies missing={missing} extras={extras}/>
      </>}
      <div className="form-actions">
        <button type="button" disabled={busy||!!retry} onClick={()=>{setError('');setStep('check');}}>Back to checklist</button>
        <button type="button" className="primary" disabled={busy} onClick={()=>void save()}>{retry?'Retry same audit':'Save audit'}</button>
      </div>
    </>}
    {step==='saved'&&<p role="status">Audit saved.</p>}
    {draft&&!resume&&!retry&&<button type="button" disabled={busy||checking} onClick={()=>{if(window.confirm('Discard this saved draft?'))reset();}}>Discard draft</button>}
    {step==='saved'&&<button type="button" disabled={busy} onClick={reset}>Start a fresh check</button>}
    {error&&!retry&&<button type="button" disabled={busy||checking} onClick={()=>{setError('');setRefresh(value=>value+1);}}>Reload expected copies</button>}
  </section>;
}
