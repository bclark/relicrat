'use client';

import {useEffect,useId,useState} from 'react';
import CollectionRows from './collection-rows';
import {api,ApiError,copyName,errorText,jsonSave,type CollectionTypes,type InventoryCopy,type Location,type RunSave} from '../lib/inventory-client';

type Props={items:InventoryCopy[];busy:boolean;runSave:RunSave;types:CollectionTypes|null;selected:string|null;open:(id:string)=>void;reload:()=>void;close:()=>void;done:(message:string)=>void};

export default function BulkMoveCopies({items,busy,runSave,types,selected,open,reload,close,done}:Props){
 const id=useId();
 const [copies,setCopies]=useState<InventoryCopy[]>([]);
 const [locations,setLocations]=useState<Location[]>([]);
 const [offset,setOffset]=useState(0),[version,setVersion]=useState(0),[more,setMore]=useState(false);
 const [loading,setLoading]=useState(true),[readError,setReadError]=useState('');
 const [destination,setDestination]=useState('');
 const [review,setReview]=useState(false),[confirmed,setConfirmed]=useState(false);
 const [error,setError]=useState(''),[blocked,setBlocked]=useState(false);
 const ids=new Set(copies.map(copy=>copy.id));
 useEffect(()=>{
  const controller=new AbortController();setLoading(true);setReadError('');
  api<Location[]>(`storage-locations?limit=100&offset=${offset}`,{signal:controller.signal})
   .then(result=>{if(!controller.signal.aborted){setLocations(old=>offset?[...old,...result]:result);setMore(result.length===100);}})
   .catch(problem=>{if(!controller.signal.aborted)setReadError(errorText(problem));})
   .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
  return()=>controller.abort();
 },[offset,version]);
 function path(place:Location){
  const names=[place.name],seen=new Set([place.id]);let parent=place.parent_id;
  while(parent&&!seen.has(parent)){seen.add(parent);const ancestor=locations.find(l=>l.id===parent);if(!ancestor){names.unshift('…');break;}names.unshift(ancestor.name);parent=ancestor.parent_id;}
  return names.join(' / ');
 }
 function toggle(copy:InventoryCopy){setCopies(old=>old.some(c=>c.id===copy.id)?old.filter(c=>c.id!==copy.id):[...old,copy]);setError('');}
 async function move(){
  if(!review||!confirmed||blocked||!copies.length)return;
  try{
   await runSave(async()=>{
    const result=await api<{moved_count:number;unchanged_count:number}>(`storage-locations/${destination}/move-copies`,jsonSave({copies:copies.map(copy=>({id:copy.id,expected_storage_revision:copy.storage_revision}))}));
    done(`Moved ${result.moved_count} ${result.moved_count===1?'copy':'copies'} to ${path(locations.find(l=>l.id===destination)!)}.${result.unchanged_count?` ${result.unchanged_count} already there; no extra history added.`:''}`);
   });
  }catch(problem){
   setError(errorText(problem));setConfirmed(false);
   if(problem instanceof ApiError&&(problem.status===409||problem.status===404||problem.uncertain))setBlocked(true);
  }
 }
 return <section className="bulk-move" aria-label="Move selected copies">
  <div className="bulk-move-actions"><h3>{copies.length} {copies.length===1?'copy':'copies'} selected</h3><button type="button" disabled={busy} onClick={close}>Cancel selection</button></div>
  {!review?<>
   <p>Select individual copies on this page. Changing the search, filters or page clears the selection.</p>
   <div className="bulk-move-actions"><button type="button" disabled={busy||copies.length===items.length} onClick={()=>setCopies(items)}>Select all copies on this page</button><button type="button" disabled={busy||!copies.length} onClick={()=>setCopies([])}>Clear selection</button></div>
   <CollectionRows items={items} busy={busy} selected={selected} open={open} types={types} selection={{ids,toggle}}/>
   <label htmlFor={id+'-destination'}>Move selected copies to</label>
   <select id={id+'-destination'} value={destination} disabled={busy||loading||!!readError} onChange={e=>setDestination(e.target.value)}><option value="">Choose a box or shelf</option>{locations.map(place=><option key={place.id} value={place.id}>{path(place)}</option>)}</select>
   {loading&&<p role="status">Loading destinations…</p>}
   {readError&&<p className="error" role="alert">{readError} <button type="button" disabled={busy||loading} onClick={()=>setVersion(v=>v+1)}>Reload destinations</button></p>}
   {more&&<button type="button" disabled={busy||loading||!!readError} onClick={()=>setOffset(offset+100)}>Load more destinations</button>}
   <button type="button" className="primary" disabled={busy||loading||!!readError||!copies.length||!destination} onClick={()=>{setReview(true);setConfirmed(false);setError('');}}>Review move</button>
  </>:<>
   <h4>Review move to {path(locations.find(l=>l.id===destination)!)}</h4>
   <ul className="bulk-move-review">{copies.map(copy=><li key={copy.id}><strong>{copyName(copy)}</strong><span>{copy.edition_label||'Edition not entered'} · Copy {copy.id.slice(0,8)}</span><span>From {copy.storage_location_name||(copy.storage_location_id?'assigned location':'Unassigned')}{copy.storage_location_id===destination?' · Already at destination':''}</span></li>)}</ul>
   <p>Each moved copy keeps its own history. If any selection has changed, none will move.</p>
   <label><input type="checkbox" checked={confirmed} disabled={busy||blocked} onChange={e=>setConfirmed(e.target.checked)}/> I reviewed these copies and their destination.</label>
   <div className="bulk-move-actions"><button type="button" disabled={busy||blocked} onClick={()=>{setReview(false);setConfirmed(false);setError('');}}>Change selection</button><button type="button" className="primary" disabled={busy||blocked||!confirmed} onClick={()=>void move()}>Move {copies.length} {copies.length===1?'copy':'copies'}</button></div>
  </>}
  {busy&&<p role="status">Saving move… Keep this page open.</p>}
  {error&&<p className="error" role="alert">{error}</p>}
  {blocked&&<><p>Reload and inspect the copies before reviewing a new selection. An unconfirmed save is never retried automatically.</p><button type="button" disabled={busy} onClick={reload}>Reload copies to review</button></>}
 </section>;
}
