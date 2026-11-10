'use client';
import {Fragment,useEffect,useRef,useState,type MutableRefObject} from 'react';
import CollectionFilter from './collection-filter';
import { GameContentsFields } from './game-contents';
import ObservationInput from './observation-input';
import BarcodeScanner from './barcode-scanner';
import CustomField,{normalizeCustomValues,replaceCustomValue,type CustomValues} from './custom-field';
import type {SavedCollection} from './custom-collections';
import {api,ApiError,copyName,errorText,jsonSave,type BarcodeReading,type CollectionSettings,type CollectionTypeId,type CollectionTypes,type InventoryCopy,type GameContents,type RunSave} from '../lib/inventory-client';

export type IntakeStart={target:string;scope:string;name:string;entryId?:string;sequence:number};
type Candidate={id:string;title:string;description:string;source_url:string;cover_url:string|null;fields:Record<string,string>};
type Result={byTitle?:boolean;provider:string;provider_label:string;candidates:Candidate[]};
type Props={start:IntakeStart;visible:boolean;types:CollectionTypes|null;settings:CollectionSettings|null;busy:boolean;runSave:RunSave;guard:MutableRefObject<()=>boolean>;close:()=>void;saved:(copy:InventoryCopy)=>void;openCopy:(id:string)=>void};

export default function ItemIntake({start,visible,types,settings,busy,runSave,guard,close,saved,openCopy}:Props){
 const [gameContents,setGameContents]=useState<GameContents>({});
 const [target,setTarget]=useState('other'),[scope,setScope]=useState(''),[scopeName,setScopeName]=useState('All items');
 const [values,setValues]=useState<Record<string,string>>({}),[customValues,setCustomValues]=useState<CustomValues>({}),[custom,setCustom]=useState<SavedCollection|null>(null);
 const [reading,setReading]=useState<BarcodeReading|null>(null),[manual,setManual]=useState(''),[manualOpen,setManualOpen]=useState(false),[format,setFormat]=useState('UPC_A');
 const [result,setResult]=useState<Result|null>(null),[candidate,setCandidate]=useState<Candidate|null>(null),[chosen,setChosen]=useState<string[]>([]),[includeCover,setIncludeCover]=useState(false),[coverReady,setCoverReady]=useState(false),[coverFailed,setCoverFailed]=useState(false);
 const previous=useRef<Record<string,string>>({});
 const searchingTitle=useRef(false);
 const ownedRequest=useRef<AbortController|null>(null);
 const [ownedMatches,setOwnedMatches]=useState<InventoryCopy[]>([]);
 const [checkingOwned,setCheckingOwned]=useState(false);
 const [ownedError,setOwnedError]=useState(false);
 function resetOwnedCheck(){
  ownedRequest.current?.abort();
  setOwnedMatches([]);
  setCheckingOwned(false);
  setOwnedError(false);
 }
 const [definitionVersion,setDefinitionVersion]=useState(0),[loading,setLoading]=useState(false),[lookupBusy,setLookupBusy]=useState(false),[error,setError]=useState(''),[lookupError,setLookupError]=useState(''),[uncertain,setUncertain]=useState(false),[completed,setCompleted]=useState<InventoryCopy|null>(null);
 const pending=useRef<{target:string;payload:unknown}|null>(null),heading=useRef<HTMLHeadingElement>(null),lookupRequest=useRef<AbortController|null>(null),lastStart=useRef(0),destinationChosen=useRef(false),submitting=useRef(false);
 const customId=target.startsWith('custom:')?target.slice(7):'';
 const definition=customId?null:types?.[target as CollectionTypeId];
 const name=customId?custom?.name||'Selected collection':definition?.plural_label||'Selected collection';
 const dirty=Object.keys(gameContents).length>0||!!reading||Object.values(values).some(v=>v.trim())||Object.keys(normalizeCustomValues(customValues)).length>0;
 const locked=busy||uncertain||loading;
 function canReplace(){return !uncertain&&!busy&&(!dirty||window.confirm('Discard this unfinished item and start in another collection?'));}
 guard.current=()=>!busy;
 function clear(){lookupRequest.current?.abort();resetOwnedCheck();setLookupBusy(false);searchingTitle.current=false;setValues({});setGameContents({});setCustomValues({});setReading(null);setManual('');setManualOpen(false);setResult(null);setCandidate(null);setChosen([]);setIncludeCover(false);setCoverReady(false);setCoverFailed(false);setError('');setLookupError('');pending.current=null;setCompleted(null);}
 useEffect(()=>{
  if(!types||!settings||!visible||!start.sequence||lastStart.current===start.sequence)return;
  const first=lastStart.current===0;lastStart.current=start.sequence;const next=start.target||(first?settings!.default_type:target);
  if(next!==target&&!canReplace()){close();return;}
  if(next!==target){clear();setTarget(next);}
  setScope(start.scope);setScopeName(start.name);setCompleted(null);
  requestAnimationFrame(()=>heading.current?.focus());
 },[start.sequence,visible,settings,types]);
 useEffect(()=>{
  setCustom(null);setLoading(false);if(!customId)return;
  const c=new AbortController();setLoading(true);setError('');
  api<SavedCollection>(`custom-collections/${customId}`,{signal:c.signal}).then(value=>{if(c.signal.aborted)return;setCustom(value);if(start.entryId&&start.target===target){const entry=value.proposal.collection.checklist.find(e=>e.id===start.entryId);if(entry&&entry.title.length<=value.proposal.type_definition.title.max_length)setValues(old=>({...old,title:old.title||entry.title}));else setError('The checklist entry is unavailable or its title is too long. Enter a title and review the checklist after saving.');}}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));}).finally(()=>{if(!c.signal.aborted)setLoading(false);});return()=>c.abort();
 },[customId,start.sequence,definitionVersion]);
 useEffect(()=>{if(visible&&!start.scope&&!start.target&&!scope&&!dirty&&!destinationChosen.current&&settings)setTarget(settings.default_type);},[settings?.default_type]);
 useEffect(()=>{if(!visible){lookupRequest.current?.abort();setLookupBusy(false);}return()=>lookupRequest.current?.abort();},[visible]);
 useEffect(()=>()=>ownedRequest.current?.abort(),[]);
 function changeTarget(next:string){destinationChosen.current=true;if(!next||next===target||!canReplace())return;clear();setTarget(next);}
 function edit(key:string,value:string){
  if(key==='title'){
   if(result?.byTitle)setResult(null);
   if(searchingTitle.current){lookupRequest.current?.abort();searchingTitle.current=false;setLookupBusy(false);}
  }setValues(old=>({...old,[key]:value}));setChosen(old=>old.filter(v=>v!==key));previous.current[key]=value;}
 async function lookup(value:BarcodeReading|string){
  lookupRequest.current?.abort();const c=new AbortController();lookupRequest.current=c;setLookupError('');setResult(null);setLookupBusy(true);
  const byTitle=typeof value==='string';searchingTitle.current=byTitle;
  try{
   const response=await api<Result>(byTitle?'title-lookups/game':`barcode-lookups/${definition!.id}`,
    {...jsonSave(byTitle?{title:value}:value),signal:c.signal});
   if(!c.signal.aborted)setResult({...response,byTitle});
  }catch(e){if(!c.signal.aborted)setLookupError(errorText(e)+' Your draft is still here; enter details manually or try again.');}finally{if(!c.signal.aborted){searchingTitle.current=false;setLookupBusy(false);}}
 }
 async function observe(value:BarcodeReading){
  lookupRequest.current?.abort();
  searchingTitle.current=false;
  setLookupBusy(false);setLookupError('');
  resetOwnedCheck();
  setReading(value);setResult(null);setCandidate(null);setIncludeCover(false);setCoverReady(false);setCoverFailed(false);
  if(definition?.id==='game'){
   const request=new AbortController();
   ownedRequest.current=request;
   setCheckingOwned(true);
   const query=new URLSearchParams({collection_type:'game',barcode:value.value,barcode_format:value.format,limit:'10'});
   try{
    const copies=await api<InventoryCopy[]>(`inventory?${query}`,{signal:AbortSignal.any([request.signal,AbortSignal.timeout(10000)])});
    if(request.signal.aborted)return;
    if(copies.length){setOwnedMatches(copies);return;}
   }catch{
    if(request.signal.aborted)return;
    setOwnedError(true);
   }finally{
    if(!request.signal.aborted)setCheckingOwned(false);
   }
  }
  if(definition?.lookup)void lookup(value);
 }
 function addAnotherCopy(){
  setOwnedMatches([]);
  document.getElementById('find-title')?.focus();
  if(reading&&definition?.lookup)void lookup(reading);
 }
 function choose(value:Candidate){previous.current={...values};const keys=definition!.entry_order.filter(k=>value.fields[k]&&(result?.byTitle||!values[k]?.trim()));setValues(old=>({...old,...Object.fromEntries(keys.map(k=>[k,value.fields[k]]))}));setChosen(keys);setCandidate(value);setResult(null);setIncludeCover(false);setCoverReady(false);setCoverFailed(false);}
 function toggleField(key:string,on:boolean){setValues(old=>({...old,[key]:on?candidate!.fields[key]:previous.current[key]||''}));setChosen(old=>on?[...old.filter(v=>v!==key),key]:old.filter(v=>v!==key));}
 async function submit(retry=false){
  if(submitting.current||busy||loading||checkingOwned||ownedMatches.length>0||(!retry&&uncertain)||!values.title?.trim()||(!customId&&!definition)||(customId&&!custom))return;
  const payload=customId?{request_id:crypto.randomUUID(),title:values.title.trim(),description:values.notes?.trim()||null,custom_details:normalizeCustomValues(customValues),expected_type_revision:custom!.type_revision}:{title:values.title.trim(),description:values.notes?.trim()||null,collection_type:definition!.id,...(definition!.id==='game'?{game_contents:gameContents}:{}),barcode:reading,edition_label:values.edition?.trim()||null,record_details:definition!.id==='record'?{artist:values.artist?.trim()||null,format:values.format?.trim()||null}:{},comic_details:definition!.id==='comic'?{issue_number:values.issue_number?.trim()||null,publisher:values.publisher?.trim()||null}:{},movie_details:definition!.id==='movie'?{media_format:values.media_format?.trim()||null,studio:values.studio?.trim()||null}:{},catalog_cover:includeCover&&coverReady&&candidate?{provider:definition!.lookup!.provider,candidate_id:candidate.id}:null};
  const request=retry?pending.current:{target,payload};if(!request)return;submitting.current=true;lookupRequest.current?.abort();setLookupBusy(false);
  try{await runSave(async()=>{pending.current=request;setError('');const copy=await api<InventoryCopy>(request.target.startsWith('custom:')?`custom-collections/${request.target.slice(7)}/copies`:'inventory',jsonSave(request.payload));pending.current=null;setUncertain(false);clear();setCompleted(copy);saved(copy);requestAnimationFrame(()=>heading.current?.focus());});}catch(e){setError(errorText(e));const unknown=e instanceof ApiError&&(e.uncertain||(customId&&e.status===409));setUncertain(!!unknown);if(!unknown)pending.current=null;}finally{submitting.current=false;}
 }
 function input(key:string){
  if(key==='title')return <Fragment key={key}><label htmlFor="find-title">{customId?custom?.proposal.type_definition.title.label:definition?.title.label||'Title'}</label>{definition?.id==='game'?<ObservationInput id="find-title" required field={definition.title} suggestionsPath="collection-settings/game-suggestions/title" value={values.title||''} change={value=>edit('title',value)}/>:<input id="find-title" required maxLength={custom?.proposal.type_definition.title.max_length||definition?.title.max_length||500} value={values.title||''} onChange={e=>edit('title',e.target.value)}/>}{definition?.title_lookup&&<><button type="button" disabled={locked||lookupBusy||checkingOwned||ownedMatches.length>0||(values.title||'').trim().length<2} onClick={()=>void lookup(values.title.trim())}>Search online by title</button><p className="hint">Sends the title you entered to the configured game catalog.</p></>}{result?.byTitle&&matches(result)}{suggestion(key)}</Fragment>;
  const field=definition?.fields.find(f=>f.key===key);if(!field)return null;
  const visibleFields=definition!.id==='record'?settings?.record_fields:definition!.id==='comic'?settings?.comic_fields:definition!.id==='movie'?settings?.movie_fields:undefined;
  if(visibleFields&&!visibleFields.includes(key as never)&&!values[key]&&!candidate?.fields[key])return null;
  return <Fragment key={key}><label htmlFor={`find-${key}`}>{field.label} (optional)</label>{key==='notes'?<textarea id="find-notes" rows={3} maxLength={field.max_length} value={values.notes||''} onChange={e=>edit('notes',e.target.value)}/>:<ObservationInput id={`find-${key}`} field={field} value={values[key]||''} change={value=>edit(key,value)}/ >}{suggestion(key)}</Fragment>;
 }
 function matches(result:Result){
  if(!result.byTitle&&!result.candidates.length&&definition?.title_lookup){
   return <div className="intake-barcode">
    <p role="status">No match for this barcode. It stays in your draft.</p>
    <button type="button" disabled={locked}
     onClick={()=>document.getElementById('find-title')?.focus()}>
     Continue with title search
    </button>
   </div>;
  }
  return <section aria-label="Possible matches">
   <h3>Possible matches from {result.provider_label}</h3>
   {result.candidates.length ? <>
    <p className="hint">{result.byTitle?'Choose a title to use in this draft.':'Choose a release to review. A barcode does not confirm the edition.'}</p>
    <ul className="barcode-matches">{result.candidates.map(match=><li key={match.id}>
     <button type="button" disabled={locked} onClick={()=>choose(match)}>
      <strong>{match.title}</strong><span>{match.description}</span>
      <span>{result.byTitle?'Use this title':'Review this match'}</span>
     </button>
    </li>)}</ul>
   </> : <p role="status">{result.byTitle?'No matching titles found. You can enter the title manually.':'No matching releases found. Keep the barcode and enter details manually.'}</p>}
  </section>;
 }
 function suggestion(key:string){return candidate?.fields[key]?<label className="lookup-field"><input type="checkbox" checked={chosen.includes(key)} onChange={e=>toggleField(key,e.target.checked)}/><span>Use catalog suggestion: {candidate.fields[key]}</span></label>:null;}
 return <section className="item-intake" hidden={!visible} aria-labelledby="add-find">
 <button type="button" className="text-button" disabled={busy} onClick={close}>Back to {scope&&scope===target?name:scopeName}</button>
 <h2 id="add-find" ref={heading} tabIndex={-1}>{completed?`${completed.title||'Item'} added.`:scope?`Add to ${name}`:'Add an item'}</h2>
 {completed?<><p role="status">Saved in {name}.</p><div className="intake-actions"><button type="button" className="primary" onClick={()=>{setCompleted(null);heading.current?.focus();}}>Add another item</button><button type="button" onClick={()=>openCopy(completed.id)}>View item</button></div><p className="hint">Photos, storage and any checklist match can be reviewed from the saved item.</p></>:<>
 <p>Start with a title. Everything else is optional.</p>
 {visible&&!scope&&<div className="intake-destination"><CollectionFilter compact value={target} change={changeTarget} types={types} busy={locked} refresh={start.sequence}/></div>}
 {loading&&<p role="status">Loading collection fields…</p>}{types&&!customId&&!definition&&<p role="alert">Collection fields are unavailable. Reload settings or choose Other to use generic entry.</p>}
 {definition&&!!definition.barcode_formats?.length&&<><BarcodeScanner disabled={locked||!visible} formats={definition.barcode_formats} onUse={observe} onLookup={definition.lookup?observe:undefined}/><button type="button" className="text-button" disabled={locked} onClick={()=>setManualOpen(v=>!v)}>Type a barcode instead</button>
 {manualOpen&&<form aria-label="Type barcode" onSubmit={e=>{e.preventDefault();observe({value:manual,format,supplement:null});setManualOpen(false);}}><label htmlFor="typed-barcode">Barcode</label><input id="typed-barcode" inputMode="numeric" maxLength={14} required value={manual} onChange={e=>setManual(e.target.value)}/><label htmlFor="typed-barcode-format">Barcode format</label><select id="typed-barcode-format" value={format} onChange={e=>setFormat(e.target.value)}>{definition.barcode_formats.map(v=><option key={v} value={v}>{v.replaceAll('_','-')}</option>)}</select><button disabled={locked} type="submit">Use barcode</button></form>}</>}
 {reading&&<div className="intake-barcode"><p>Barcode {reading.value} · {reading.format.replaceAll('_','-')}{reading.supplement?` · Supplement ${reading.supplement}`:''}</p><button type="button" disabled={locked} onClick={()=>{lookupRequest.current?.abort();setReading(null);resetOwnedCheck();searchingTitle.current=false;setCandidate(null);setIncludeCover(false);setResult(null);setLookupBusy(false);}}>Remove barcode from draft</button>{!definition?.lookup&&<p className="hint">Barcode kept. No catalog lookup is configured; enter the details below.</p>}{definition?.lookup&&!ownedMatches.length&&<button type="button" disabled={locked||lookupBusy||checkingOwned} onClick={()=>void lookup(reading)}>{definition.lookup.action_label}</button>}</div>}
 {checkingOwned&&<p role="status">Checking your collection for this barcode…</p>}
 {ownedError&&<p role="status">Couldn’t check your collection for this barcode.</p>}
 {!!ownedMatches.length&&<section className="intake-barcode" aria-labelledby="owned-barcode-title">
  <h3 id="owned-barcode-title">Already in your collection</h3>
  <ul>{ownedMatches.map(copy=><li key={copy.id}>
   <strong>{copyName(copy)}</strong>
   <p>{copy.storage_location_name||'No location assigned'}</p>
   <button type="button" disabled={locked} onClick={()=>openCopy(copy.id)}>View copy</button>
  </li>)}</ul>
  <button type="button" disabled={locked} onClick={addAnotherCopy}>Add another copy</button>
 </section>}
 {lookupBusy&&<p role="status">Looking for possible matches… You can still type below.</p>}{lookupError&&<p role="alert" className="error">{lookupError}</p>}
 {result&&!result.byTitle&&matches(result)}
 {candidate&&<p className="hint">Review the catalog suggestions below. Only Save item adds a physical copy.</p>}
 {candidate?.cover_url&&definition?.lookup?.cover_art&&<div className="intake-cover"><img src={candidate.cover_url} alt={`Catalog cover for ${candidate.title}`} width={112} height={112} onLoad={()=>setCoverReady(true)} onError={()=>{setCoverReady(false);setIncludeCover(false);setCoverFailed(true);}}/><label className="lookup-field"><input type="checkbox" disabled={locked||!coverReady} checked={includeCover} onChange={e=>setIncludeCover(e.target.checked)}/><span>Include catalog cover{coverFailed&&<small>Cover preview unavailable. You can save without artwork.</small>}<small>Optional artwork, not a photo of your physical copy. <a href={candidate.source_url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">View source</a></small></span></label></div>}
 <form aria-label="Add an item" onSubmit={e=>{e.preventDefault();void submit();}}><fieldset disabled={locked||(!definition&&!custom)}>
 {customId?<>{input('title')}{custom?.proposal.type_definition.optional_fields.map(field=><CustomField key={field.id} field={field} value={customValues[field.id]} change={value=>setCustomValues(old=>replaceCustomValue(old,field.id,value))}/>)}<label htmlFor="custom-intake-notes">Notes (optional)</label><textarea id="custom-intake-notes" maxLength={10000} rows={3} value={values.notes||''} onChange={e=>edit('notes',e.target.value)}/></>:<>{definition?.entry_order.filter(key=>key!=='notes'&&key!=='edition').map(input)}<details><summary>More details (optional)</summary>{definition?.id==='game'&&<GameContentsFields value={gameContents} change={setGameContents}/>}{definition?.entry_order.filter(key=>key==='notes'||key==='edition').map(input)}</details></>}
 <div className="intake-actions"><button className="primary" type="submit" disabled={!values.title?.trim()||checkingOwned||ownedMatches.length>0}>{busy?'Saving…':'Save item'}</button><p className="hint">Adds one physical copy to {name}.</p></div><p className="hint">Photos and storage can be added after saving.</p></fieldset></form>
 {uncertain&&<p role="status">Saving needs confirmation. Inspect the collection before creating another copy. {customId?<button type="button" disabled={busy||loading} onClick={()=>void submit(true)}>Retry same save</button>:<button type="button" disabled={busy} onClick={close}>Check collection</button>} {!customId&&<button type="button" disabled={busy} onClick={()=>{if(window.confirm('Only clear this draft after inspecting the collection for the original save. Clear the inspected draft?')){setUncertain(false);clear();}}}>Clear inspected draft</button>}</p>}
 </>}{error&&<p role="alert" className="error">{error}{customId&&!uncertain&&<button type="button" disabled={busy||loading} onClick={()=>setDefinitionVersion(v=>v+1)}>Reload field controls</button>}</p>}
 </section>;
}
