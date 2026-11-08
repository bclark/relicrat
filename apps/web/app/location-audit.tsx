import {useEffect,useState} from 'react';
import {api,ApiError,errorText,jsonSave,type Location,type RunSave} from '../lib/inventory-client';

import AuditResolution,{type Finding,type Resolution} from './audit-resolution';

type Copy = {id:string;title:string;edition:string|null};
type RecordedResolution = {action:Resolution['action'];title:string;location_name:string;copy_id:string};
type Result = {id:string;created_at:string;copies:(Copy & {found:boolean})[];extras:string[];resolutions:Record<string,RecordedResolution>};
type Preview = {copies:Copy[];snapshot:string;latest:Result|null};
type Submission = {request_id:string;snapshot:string;found_ids:string[];extras:string[]};

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
  const [step,setStep]=useState<'check'|'review'|'saved'>('check');
  const [found,setFound]=useState<string[]>([]);
  const [extras,setExtras]=useState<string[]>([]);
  const [extra,setExtra]=useState('');
  const [error,setError]=useState('');
  const [refresh,setRefresh]=useState(0);
  const [retry,setRetry]=useState<Submission|null>(null);
  useEffect(()=>{
    const controller=new AbortController();
    api<Preview>(path,{signal:controller.signal}).then(result=>{
      if(!controller.signal.aborted){setPreview(result);setLatest(result.latest);}
    }).catch(problem=>{if(!controller.signal.aborted)setError(errorText(problem));});
    return()=>controller.abort();
  },[path,refresh]);

  function reset(){
    setPreview(null);setFound([]);setExtras([]);setExtra('');setStep('check');
    setError('');setFinding(null);setResolutionError('');setRetry(null);setRefresh(value=>value+1);
  }

  async function save(){
    if(!preview||busy)return;
    setError('');
    const submission=retry??{request_id:crypto.randomUUID(),snapshot:preview.snapshot,found_ids:found,extras};
    setRetry(submission);
    try{
      const saved=await runSave(()=>api<Result>(path,jsonSave(submission)));
      if(saved){setLatest(saved);setStep('saved');}
      setRetry(null);
    }catch(problem){
      if(problem instanceof ApiError&&!problem.uncertain)setRetry(null);
      setError(errorText(problem));
    }
  }

  async function resolve(action:Resolution){
    if(!latest||busy)return;
    setResolutionError('');
    try{
      const saved=await runSave(()=>api<Result>(`${path}/${latest.id}/resolutions`,jsonSave(action)));
      if(saved){
        setLatest(saved);setFinding(null);changed();
        setRefresh(value=>value+1);
      }
    }catch(problem){setResolutionError(errorText(problem));}
  }

  function resolutionControl(key:string,item:Finding){
    const resolved=latest?.resolutions[key];
    if(resolved)return <p>Resolved · {resolutionLabel(resolved)}</p>;
    return <button type="button" disabled={busy} onClick={()=>{setResolutionError('');setFinding(item);}}>Resolve {item.title}</button>;
  }

  const missing=preview?.copies.filter(copy=>!found.includes(copy.id))??[];
  return <section aria-label="Check location contents" className="item-section">
    <h3>Check contents</h3>
    {latest&&<details open={step==='saved'||undefined}>
      <summary>Last checked · {new Date(latest.created_at).toLocaleString()} · {latest.copies.filter(copy=>copy.found).length} found · {latest.copies.filter(copy=>!copy.found).length} missing · {latest.extras.length} extra</summary>
      <h4>Original findings</h4>
      <h5>Missing copies ({latest.copies.filter(copy=>!copy.found).length})</h5>
      <ul>{latest.copies.filter(copy=>!copy.found).map(copy=><li key={copy.id}>{copyLabel(copy)}
        {resolutionControl(`missing:${copy.id}`,{kind:'missing',id:copy.id,title:copy.title})}
      </li>)}</ul>
      <h5>Extra items ({latest.extras.length})</h5>
      <ul>{latest.extras.map((title,index)=><li key={index}><span>{title}</span>
        {resolutionControl(`extra:${index}`,{kind:'extra',index,title})}
      </li>)}</ul>
      {finding&&<AuditResolution key={finding.kind==='missing'?finding.id:finding.index} finding={finding}
        box={box} expected={new Set([...latest.copies.map(copy=>copy.id),...Object.values(latest.resolutions).map(value=>value.copy_id)])}
        busy={busy} confirm={resolve} cancel={()=>{setFinding(null);setResolutionError('');}}/>}
      {resolutionError&&<p role="alert" className="error">{resolutionError}</p>}
    </details>}
    {error&&<p role="alert" className="error">{error}</p>}
    {!preview&&!error&&<p role="status">Loading expected copies…</p>}
    {step==='check'&&preview&&<>
      <p>Mark each copy you found in this location. Unchecked copies will be recorded as missing.</p>
      <fieldset disabled={busy}>
        <legend>Expected copies</legend>
        {preview.copies.length?<ul>{preview.copies.map(copy=><li key={copy.id}>
          <label><input type="checkbox" checked={found.includes(copy.id)} onChange={event=>{
            const checked=event.currentTarget.checked;
            setFound(ids=>checked?[...ids,copy.id]:ids.filter(id=>id!==copy.id));
          }}/> {copyLabel(copy)}</label>
        </li>)}</ul>:<p>No copies are expected here.</p>}
      </fieldset>
      <label htmlFor="location-audit-extra">Extra item</label>
      <input id="location-audit-extra" value={extra} maxLength={120} disabled={busy||extras.length>=25}
        onChange={event=>setExtra(event.target.value)}/>
      <button type="button" disabled={busy||!extra.trim()||extras.length>=25} onClick={()=>{setExtras(items=>[...items,extra.trim()]);setExtra('');}}>Add extra item</button>
      {!!extras.length&&<ul aria-label="Recorded extra items">{extras.map((item,index)=><li key={index}>{item} <button type="button" aria-label={`Remove extra item ${index+1}`} disabled={busy} onClick={()=>setExtras(items=>items.filter((_,i)=>i!==index))}>Remove</button></li>)}</ul>}
      <button type="button" className="primary" disabled={busy||!!extra.trim()} onClick={()=>setStep('review')}>Review audit</button>
    </>}
    {step==='review'&&preview&&<>
      <p>{found.length} of {preview.copies.length} expected copies found. Saving records the observations. Use the copy’s location picker for storage changes.</p>
      <Discrepancies missing={missing} extras={extras}/>
      <div className="form-actions">
        <button type="button" disabled={busy||!!retry} onClick={()=>{setError('');setStep('check');}}>Back to checklist</button>
        <button type="button" className="primary" disabled={busy} onClick={()=>void save()}>{retry?'Retry same audit':'Save audit'}</button>
      </div>
    </>}
    {step==='saved'&&<p role="status">Audit saved.</p>}
    {(error||step==='saved')&&!retry&&<button type="button" disabled={busy} onClick={reset}>Start a fresh check</button>}
  </section>;
}
