'use client';
import {useEffect,useRef,useState} from 'react';
import CustomField,{normalizeCustomValues,replaceCustomValue,type CustomValues,type CustomTypeDefinition} from './custom-field';
import CustomDefinitionEditor from './custom-definition-editor';
import ChecklistProgress from './checklist-progress';
import {api,ApiError,errorText,jsonSave,type InventoryCopy,type RunSave} from '../lib/inventory-client';

export type SavedCollection = {id:string;name:string;type_revision:number;proposal:{type_definition:CustomTypeDefinition;collection:{checklist:{id:string;title:string}[];completion:{eligibility:string}}}};

export type CollectionIntakeEvent={id:string;sequence:number;entryId?:string};

export default function CustomCollections({createdEvent,runSave,locked,changed,openCopy,refresh}:{createdEvent:CollectionIntakeEvent;runSave:RunSave;locked:boolean;changed:()=>void;openCopy:(id:string)=>void;refresh:number}) {
 const [choices,setChoices]=useState<{id:string;name:string}[]>([]),[selected,setSelected]=useState(''),[collection,setCollection]=useState<SavedCollection|null>(null);
 const [copies,setCopies]=useState<InventoryCopy[]>([]),[page,setPage]=useState(0),[more,setMore]=useState(false),[loading,setLoading]=useState(false),[version,setVersion]=useState(0);
 const [title,setTitle]=useState(''),[notes,setNotes]=useState(''),[values,setValues]=useState<CustomValues>({}),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [review,setReview]=useState(false),[open,setOpen]=useState(false);
 const titleInput=useRef<HTMLInputElement>(null);
 const [requestedEntry,setRequestedEntry]=useState<{collectionId:string;entryId:string}|null>(null);
 const pending=useRef<{collection_id:string;payload:{request_id:string;title:string;description:string|null;custom_details:CustomValues;expected_type_revision:number}}|null>(null);
 const [listPage,setListPage]=useState(0),[listMore,setListMore]=useState(false);
 function startFigure(id:string,entryId?:string){
  setOpen(true);requestAnimationFrame(()=>{const heading=document.getElementById('saved-collection')?.closest('details')?.querySelector('summary');heading?.focus();heading?.scrollIntoView({block:'nearest'});});
  if(pending.current||title||notes||Object.keys(normalizeCustomValues(values)).length>0){setNotice('Your figure draft is still in its original collection. Finish saving it or clear its fields before starting another figure.');return;}
  setCollection(null);setSelected(id);setPage(0);setVersion(v=>v+1);setNotice('');
  setRequestedEntry(entryId?{collectionId:id,entryId}:null);
 }
 useEffect(()=>{if(createdEvent.id)startFigure(createdEvent.id,createdEvent.entryId);},[createdEvent]);
 useEffect(()=>{
  if(!requestedEntry||loading||collection?.id!==requestedEntry.collectionId)return;
  const entry=collection.proposal.collection.checklist.find(e=>e.id===requestedEntry.entryId);setRequestedEntry(null);
  if(!entry){setNotice('That checklist entry is unavailable. Review the current checklist before adding a figure.');return;}
  if(entry.title.length>collection.proposal.type_definition.title.max_length){setNotice('The checklist name is longer than this collection allows. Enter a shorter figure name before saving.');return;}
  setTitle(entry.title);setNotice(`Draft started for ${entry.title}. Review the details, then choose Add figure. Review its checklist match after saving.`);
  requestAnimationFrame(()=>{titleInput.current?.focus();titleInput.current?.scrollIntoView({block:'nearest'});});
 },[collection,loading,requestedEntry]);
 useEffect(()=>{
  const c=new AbortController();api<{id:string;name:string}[]>(`custom-collections?limit=51&offset=${listPage*50}`,{signal:c.signal}).then(items=>{if(!c.signal.aborted){setChoices(items.slice(0,50));setListMore(items.length>50);}}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));});return()=>c.abort();
 },[version,listPage,createdEvent.sequence]);
 useEffect(()=>{
  if(!selected){setCollection(null);setCopies([]);return;}
  const c=new AbortController();setLoading(true);setError('');setCollection(null);setCopies([]);
  Promise.all([api<SavedCollection>(`custom-collections/${selected}`,{signal:c.signal}),api<InventoryCopy[]>(`inventory?custom_collection_id=${selected}&limit=21&offset=${page*20}`,{signal:c.signal})]).then(([item,items])=>{if(!c.signal.aborted){setCollection(item);setCopies(items.slice(0,20));setMore(items.length>20);}}).catch(e=>{if(!c.signal.aborted){setRequestedEntry(null);setError(errorText(e));}}).finally(()=>{if(!c.signal.aborted)setLoading(false);});return()=>c.abort();
 },[selected,page,version]);
 async function add(){
  if(!collection||collection.id!==selected||locked||loading||requestedEntry)return;
  const target=pending.current?.collection_id||selected;
  const payload=pending.current?.payload || {request_id:crypto.randomUUID(),title:title.trim(),description:notes.trim()||null,custom_details:normalizeCustomValues(values),expected_type_revision:collection.type_revision};
  pending.current={collection_id:target,payload};setError('');setNotice('');
  try{await runSave(async()=>{await api<InventoryCopy>(`custom-collections/${target}/copies`,jsonSave(payload));pending.current=null;setReview(false);setTitle('');setNotes('');setValues({});setPage(0);setVersion(v=>v+1);changed();setNotice('Figure added. Open it to review its checklist match.');});}
  catch(e){const uncertain=e instanceof ApiError&&(e.uncertain||e.status===409);setReview(uncertain);if(!uncertain)pending.current=null;setError(errorText(e));}
 }
 function choose(id:string){if(pending.current)return;setRequestedEntry(null);setSelected(id);setTitle('');setNotes('');setValues({});setPage(0);setNotice('');}
 return <details className="collection-authoring" open={open} onToggle={event=>setOpen(event.currentTarget.open)}><summary>Your custom collections</summary>
  <label htmlFor="saved-collection">Collection</label><select id="saved-collection" value={selected} disabled={locked||review||!!title||!!notes||Object.keys(normalizeCustomValues(values)).length>0} onChange={e=>choose(e.target.value)}><option value="">Choose a saved collection</option>{selected&&!choices.some(c=>c.id===selected)&&<option value={selected}>{collection?.name||'Selected collection'}</option>}{choices.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>
  {!choices.length&&<p>No collections on this page. Create one from a reviewed JSON definition above.</p>}
  <button type="button" disabled={locked||loading||listPage===0} onClick={()=>setListPage(p=>p-1)}>Previous collections</button><button type="button" disabled={locked||loading||!listMore} onClick={()=>setListPage(p=>p+1)}>More collections</button>
  {error&&<p className="error" role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}{loading&&<p role="status">Loading collection…</p>}
  {collection&&<section aria-label={`Saved collection: ${collection.name}`}><h2>{collection.name}</h2><p>This checklist describes your collecting goal. Progress uses only your reviewed matches to owned figures.</p>
   <ChecklistProgress collectionId={collection.id} refresh={refresh} locked={locked||review||loading} addFigure={entryId=>startFigure(collection.id,entryId)} />
   <CustomDefinitionEditor key={collection.id+'-'+collection.type_revision} collection={collection} locked={locked||review||!!title||!!notes||Object.keys(normalizeCustomValues(values)).length>0} runSave={runSave} saved={next=>{setCollection(next);setVersion(v=>v+1);setNotice('Field controls updated. Existing figures were preserved.');}} />
   <button type="button" disabled={locked||review||loading} onClick={async()=>{try{setCollection(await api<SavedCollection>(`custom-collections/${selected}`));setError('');}catch(e){setError(errorText(e));}}}>Reload field controls</button>
   <h3>Add a figure you own</h3><form onSubmit={e=>{e.preventDefault();void add();}}><fieldset disabled={locked||loading||review}>
    <label>{collection.proposal.type_definition.title.label} (required)<input ref={titleInput} required maxLength={collection.proposal.type_definition.title.max_length} value={title} onChange={e=>setTitle(e.target.value)} /></label>
    {collection.proposal.type_definition.optional_fields.map(f=><CustomField key={f.id} field={f} value={values[f.id]} change={value=>setValues(v=>replaceCustomValue(v,f.id,value))} />)}
    <label>Notes (optional)<textarea maxLength={10000} rows={3} value={notes} onChange={e=>setNotes(e.target.value)} /></label>
    <button disabled={!title.trim()} type="submit">Add figure</button>
   </fieldset></form>
   {review&&<p role="status">Your save needs confirmation. The same save identifier will prevent duplicates. <button type="button" disabled={locked||loading} onClick={()=>void add()}>Retry same save</button></p>}
   <h3>Your saved figures</h3><p>Photos, storage and edit history are available when you open a figure.</p>
   <ul>{copies.map(copy=><li key={copy.id}><button type="button" disabled={locked} onClick={()=>openCopy(copy.id)}>{copy.title||'Untitled figure'}</button></li>)}</ul>{!copies.length&&<p>No figures on this page.</p>}
   <button type="button" disabled={locked||loading||page===0} onClick={()=>setPage(v=>v-1)}>Previous figures</button><button type="button" disabled={locked||loading||!more} onClick={()=>setPage(v=>v+1)}>More figures</button>
  </section>}
 </details>;
}
