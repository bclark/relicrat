import {useEffect,useState} from 'react';
import {api,ApiError,errorText,jsonSave,type RunSave} from '../lib/inventory-client';

type Copy = {id:string;title:string;edition:string|null};
type Result = {id:string;created_at:string;copies:(Copy & {found:boolean})[];extras:string[]};
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

export default function LocationAudit({id,busy,runSave}:{id:string;busy:boolean;runSave:RunSave}){
  const path=`storage-locations/${id}/audits`;
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
    setError('');setRetry(null);setRefresh(value=>value+1);
  }

  async function save(){
    if(!preview||busy)return;
    setError('');
    const submission=retry??{request_id:crypto.randomUUID(),snapshot:preview.snapshot,found_ids:found,extras};
    try{
      const saved=await runSave(()=>api<Result>(path,jsonSave(submission)));
      if(saved){setLatest(saved);setStep('saved');setRetry(null);}
    }catch(problem){
      setRetry(problem instanceof ApiError&&!problem.uncertain ? null : submission);
      setError(errorText(problem));
    }
  }

  const missing=preview?.copies.filter(copy=>!found.includes(copy.id))??[];
  return <section aria-label="Check location contents" className="item-section">
    <h3>Check contents</h3>
    {latest&&<details open={step==='saved'||undefined}>
      <summary>Last checked · {new Date(latest.created_at).toLocaleString()} · {latest.copies.filter(copy=>copy.found).length} found · {latest.copies.filter(copy=>!copy.found).length} missing · {latest.extras.length} extra</summary>
      <Discrepancies missing={latest.copies.filter(copy=>!copy.found)} extras={latest.extras}/>
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
