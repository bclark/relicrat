'use client';
import {useEffect,useRef,useState} from 'react';
import {api,ApiError,errorText,jsonSave,type InventoryCopy,type RunSave} from '../lib/inventory-client';

export type SavedCollection = {id:string;name:string;proposal:{type_definition:{label:string;title:{label:string;max_length:number};optional_fields:{id:string;label:string;max_length:number}[]};collection:{checklist:{id:string;title:string}[];completion:{eligibility:string}}}};

export default function CustomCollections({createdEvent,runSave,locked,changed,openCopy}:{createdEvent:{id:string;sequence:number};runSave:RunSave;locked:boolean;changed:()=>void;openCopy:(id:string)=>void}) {
 const [choices,setChoices]=useState<{id:string;name:string}[]>([]),[selected,setSelected]=useState(''),[collection,setCollection]=useState<SavedCollection|null>(null);
 const [copies,setCopies]=useState<InventoryCopy[]>([]),[page,setPage]=useState(0),[more,setMore]=useState(false),[loading,setLoading]=useState(false),[version,setVersion]=useState(0);
 const [title,setTitle]=useState(''),[notes,setNotes]=useState(''),[values,setValues]=useState<Record<string,string>>({}),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [review,setReview]=useState(false),[open,setOpen]=useState(false);
 const pending=useRef<{collection_id:string;payload:{request_id:string;title:string;description:string|null;custom_details:Record<string,string>}}|null>(null);
 const [listPage,setListPage]=useState(0),[listMore,setListMore]=useState(false);
 useEffect(()=>{if(!createdEvent.id)return;setOpen(true);setVersion(v=>v+1);if(pending.current||title||notes||Object.values(values).some(Boolean)){setNotice('Another collection is ready. Your figure draft is still in its original collection; finish saving it before switching.');return;}setSelected(createdEvent.id);setPage(0);},[createdEvent]);
 useEffect(()=>{
  const c=new AbortController();api<{id:string;name:string}[]>(`custom-collections?limit=51&offset=${listPage*50}`,{signal:c.signal}).then(items=>{if(!c.signal.aborted){setChoices(items.slice(0,50));setListMore(items.length>50);}}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));});return()=>c.abort();
 },[version,listPage]);
 useEffect(()=>{
  if(!selected){setCollection(null);setCopies([]);return;}
  const c=new AbortController();setLoading(true);setError('');setCollection(null);setCopies([]);
  Promise.all([api<SavedCollection>(`custom-collections/${selected}`,{signal:c.signal}),api<InventoryCopy[]>(`inventory?custom_collection_id=${selected}&limit=21&offset=${page*20}`,{signal:c.signal})]).then(([item,items])=>{if(!c.signal.aborted){setCollection(item);setCopies(items.slice(0,20));setMore(items.length>20);}}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));}).finally(()=>{if(!c.signal.aborted)setLoading(false);});return()=>c.abort();
 },[selected,page,version]);
 async function add(){
  if(!collection||locked||loading)return;
  const target=pending.current?.collection_id||selected;
  const payload=pending.current?.payload || {request_id:crypto.randomUUID(),title:title.trim(),description:notes.trim()||null,custom_details:Object.fromEntries(Object.entries(values).map(([k,v])=>[k,v.trim()]).filter(([,v])=>v))};
  pending.current={collection_id:target,payload};setError('');setNotice('');
  try{await runSave(async()=>{await api<InventoryCopy>(`custom-collections/${target}/copies`,jsonSave(payload));pending.current=null;setReview(false);setTitle('');setNotes('');setValues({});setPage(0);setVersion(v=>v+1);changed();setNotice('Figure added. Checklist completion has not been inferred.');});}
  catch(e){const uncertain=e instanceof ApiError&&(e.uncertain||e.status===409);setReview(uncertain);if(!uncertain)pending.current=null;setError(errorText(e));}
 }
 function choose(id:string){if(pending.current)return;setSelected(id);setTitle('');setNotes('');setValues({});setPage(0);setNotice('');}
 return <details className="collection-authoring" open={open} onToggle={event=>setOpen(event.currentTarget.open)}><summary>Your custom collections</summary>
  <label htmlFor="saved-collection">Collection</label><select id="saved-collection" value={selected} disabled={locked||review||!!title||!!notes||Object.values(values).some(Boolean)} onChange={e=>choose(e.target.value)}><option value="">Choose a saved collection</option>{selected&&!choices.some(c=>c.id===selected)&&<option value={selected}>{collection?.name||'Selected collection'}</option>}{choices.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>
  {!choices.length&&<p>No collections on this page. Create one from a reviewed JSON definition above.</p>}
  <button type="button" disabled={locked||loading||listPage===0} onClick={()=>setListPage(p=>p-1)}>Previous collections</button><button type="button" disabled={locked||loading||!listMore} onClick={()=>setListPage(p=>p+1)}>More collections</button>
  {error&&<p className="error" role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}{loading&&<p role="status">Loading collection…</p>}
  {collection&&<section aria-label={`Saved collection: ${collection.name}`}><h2>{collection.name}</h2><p>This saved checklist describes your collecting goal. It does not say which figures you own.</p>
   <details><summary>Checklist — {collection.proposal.collection.checklist.length} goals</summary><p>{collection.proposal.collection.completion.eligibility}</p><ul>{collection.proposal.collection.checklist.map(c=><li key={c.id}>{c.title}</li>)}</ul><p>Completion and original-release eligibility are not evaluated automatically.</p></details>
   <h3>Add a figure you own</h3><form onSubmit={e=>{e.preventDefault();void add();}}><fieldset disabled={locked||loading||review}>
    <label>{collection.proposal.type_definition.title.label} (required)<input required maxLength={collection.proposal.type_definition.title.max_length} value={title} onChange={e=>setTitle(e.target.value)} /></label>
    {collection.proposal.type_definition.optional_fields.map(f=><label key={f.id}>{f.label} (optional)<input maxLength={f.max_length} value={values[f.id]||''} onChange={e=>setValues(v=>({...v,[f.id]:e.target.value}))} /></label>)}
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
