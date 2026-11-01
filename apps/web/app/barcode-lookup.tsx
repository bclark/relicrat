'use client';

import {useEffect,useRef,useState} from 'react';
import {api,jsonSave,type BarcodeReading,type CollectionType,type CatalogCover} from '../lib/inventory-client';

type Candidate={id:string;title:string;description:string;source_url:string;fields:Record<string,string>;cover_url:string|null};
type Result={provider:string;provider_label:string;candidates:Candidate[]};
type Props={definition:CollectionType;reading:BarcodeReading;values:Record<string,string>;apply:(fields:Record<string,string>,cover?:CatalogCover)=>void;locked:boolean;requested:number};

export default function BarcodeLookup({definition,reading,values,apply,locked,requested}:Props){
 const config=definition.lookup!;
 const [result,setResult]=useState<Result|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [selected,setSelected]=useState<Candidate|null>(null),[base,setBase]=useState(''),[chosen,setChosen]=useState<string[]>([]),[coverFailed,setCoverFailed]=useState(false);
 const [includeCover,setIncludeCover]=useState(false),[coverReady,setCoverReady]=useState(false);
 const searchBase=useRef('');
 const controller=useRef<AbortController|null>(null),heading=useRef<HTMLHeadingElement>(null),review=useRef<HTMLHeadingElement>(null),button=useRef<HTMLButtonElement>(null);
 const labels=Object.fromEntries([definition.title,...definition.fields].map(field=>[field.key,field.label]));
 const snapshot=JSON.stringify(values),stale=!!selected&&snapshot!==base;
 useEffect(()=>()=>controller.current?.abort(),[]);
 useEffect(()=>{if(locked){controller.current?.abort();setBusy(false);}},[locked]);
 useEffect(()=>{if(result&&snapshot===searchBase.current)heading.current?.focus();},[result]);
 async function search(){
  if(locked)return;
  controller.current?.abort();const request=new AbortController();controller.current=request;
  searchBase.current=snapshot;setBusy(true);setError('');setNotice('');setResult(null);setSelected(null);
  try{
   const value=await api<Result>(`barcode-lookups/${definition.id}`,{...jsonSave(reading),signal:request.signal});
   if(!request.signal.aborted)setResult(value);
  }catch{if(!request.signal.aborted)setError('Lookup is unavailable. You can try again or enter details manually. Your draft is still here.');}
  finally{if(!request.signal.aborted)setBusy(false);}
 }
 // A deferred effect avoids duplicate requests from development Strict Mode.
 useEffect(()=>{if(requested){const timer=setTimeout(()=>void search(),0);return()=>clearTimeout(timer);}},[requested]);
 function choose(candidate:Candidate){const from=document.activeElement;setSelected(candidate);setBase(snapshot);setChosen(definition.entry_order.filter(key=>candidate.fields[key]&&!values[key]?.trim()));setCoverFailed(false);setCoverReady(false);setIncludeCover(false);setNotice('');requestAnimationFrame(()=>{if(document.activeElement===from || !document.body.contains(from))review.current?.focus();});}
 function useDetails(){
  if(!selected||locked||stale||(!chosen.length&&!includeCover))return;
  const fields=Object.fromEntries(chosen.map(key=>[key,selected.fields[key]]));
  const cover=includeCover&&coverReady&&selected.cover_url?{provider:result!.provider,candidate_id:selected.id,title:selected.title,cover_url:selected.cover_url,source_url:selected.source_url,provider_label:result!.provider_label}:undefined;
  setSelected(null);setResult(null);setNotice('Selection added to this draft. Review the form, then save.');apply(fields,cover);
 }
 return <section className="barcode-lookup" aria-label="Barcode lookup">
  <p className="hint">Search the configured catalog ({config.provider}) using this barcode. Photos stay on your device.</p>
  <button ref={button} type="button" disabled={locked||busy} onClick={()=>void search()}>{busy?'Looking up…':config.action_label}</button>
  {busy&&<p role="status">Looking for possible matches… You can still enter details manually.</p>}
  {error&&<p role="alert" className="error">{error}</p>}
  {result&&<div>
   <h3 ref={heading} tabIndex={-1}>Possible matches from {result.provider_label}</h3>
   <p className="hint">A shared barcode can describe several editions. Choose a match to review; nothing is saved.</p>
   {!result.candidates.length?<p role="status">No matching releases found. Keep the barcode and enter details manually.</p>:<ul className="barcode-matches">{result.candidates.map(candidate=><li key={candidate.id}>
    <button type="button" disabled={locked} aria-pressed={candidate.id===selected?.id} onClick={()=>choose(candidate)}><strong>{candidate.title}</strong><span>{candidate.description}</span><span>Review this match</span></button>
   </li>)}</ul>}
   {selected&&<div className="barcode-match-review">
    <h4 ref={review} tabIndex={-1}>Review details to fill</h4>
    {selected.cover_url&&!coverFailed?<img className="lookup-cover" src={selected.cover_url} alt={`Cover preview for ${selected.title}`} width={120} height={120} onLoad={()=>setCoverReady(true)} onError={()=>{setCoverFailed(true);setCoverReady(false);setIncludeCover(false);}}/>:<p className="hint">Cover preview unavailable.</p>}
    <p><a href={selected.source_url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">View release on {result.provider_label}</a></p>
    <p className="hint">Select the fields to fill. Existing text is unchecked so you can keep your changes. You can optionally keep catalog artwork separately from photos of your physical copy.</p>
    <fieldset disabled={locked||stale}>{selected.cover_url&&!coverFailed&&<label className="lookup-field"><input type="checkbox" checked={includeCover} disabled={!coverReady} onChange={event=>setIncludeCover(event.target.checked)}/><span><strong>Include catalog cover</strong><small>Saved with the final form, with its source. This is artwork, not a photo of your physical copy.</small></span></label>}{definition.entry_order.filter(key=>selected.fields[key]).map(key=>{const value=selected.fields[key];return <label className="lookup-field" key={key}>
     <input type="checkbox" checked={chosen.includes(key)} onChange={event=>setChosen(old=>event.target.checked?[...old,key]:old.filter(field=>field!==key))}/>
     <span><strong>{labels[key as keyof typeof labels]||key}</strong><span>{value}</span><small>Current: {values[key]||'Not entered'}</small></span>
    </label>;})}</fieldset>
    {stale&&<p role="status">Your draft changed. <button type="button" disabled={locked} onClick={()=>choose(selected)}>Review this match again</button></p>}
    <button type="button" className="primary" disabled={locked||stale||(!chosen.length&&!includeCover)} onClick={useDetails}>Use these details</button>
    <button type="button" disabled={locked} onClick={()=>{setSelected(null);button.current?.focus();}}>Cancel review</button>
   </div>}
  </div>}
  <p className="notice" role="status">{notice}</p>
 </section>;
}
