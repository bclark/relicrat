'use client';
import {useEffect,useRef,useState} from 'react';
import type {CustomTypeDefinition} from './custom-field';
import CustomDefinitionEditor from './custom-definition-editor';
import ChecklistProgress from './checklist-progress';
import CollectionDefinitionExport from './collection-definition-export';
import {api,errorText,type InventoryCopy,type RunSave} from '../lib/inventory-client';

export type SavedCollection = {id:string;name:string;type_revision:number;proposal:{type_definition:CustomTypeDefinition;collection:{checklist:{id:string;title:string}[];completion:{eligibility:string}}}};

export type CollectionIntakeEvent={id:string;sequence:number;entryId?:string};

export default function CustomCollections({createdEvent,runSave,locked,changed,openCopy,refresh,onIntake}:{createdEvent:CollectionIntakeEvent;runSave:RunSave;locked:boolean;changed:()=>void;openCopy:(id:string)=>void;refresh:number;onIntake:(id:string,entryId?:string)=>void}) {
 const [choices,setChoices]=useState<{id:string;name:string}[]>([]),[selected,setSelected]=useState(''),[collection,setCollection]=useState<SavedCollection|null>(null);
 const [copies,setCopies]=useState<InventoryCopy[]>([]),[page,setPage]=useState(0),[more,setMore]=useState(false),[loading,setLoading]=useState(false),[version,setVersion]=useState(0);
 const [notice,setNotice]=useState(''),[error,setError]=useState(''),[open,setOpen]=useState(false);
 const handledCreation=useRef(0);
 const [listPage,setListPage]=useState(0),[listMore,setListMore]=useState(false);
 function startFigure(id:string,entryId?:string){onIntake(id,entryId);}
 useEffect(()=>{if(createdEvent.id&&!locked&&createdEvent.sequence!==handledCreation.current){handledCreation.current=createdEvent.sequence;setSelected(createdEvent.id);setOpen(true);startFigure(createdEvent.id,createdEvent.entryId);}},[createdEvent,locked]);
 useEffect(()=>{
  const c=new AbortController();api<{id:string;name:string}[]>(`custom-collections?limit=51&offset=${listPage*50}`,{signal:c.signal}).then(items=>{if(!c.signal.aborted){setChoices(items.slice(0,50));setListMore(items.length>50);}}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));});return()=>c.abort();
 },[version,listPage,createdEvent.sequence]);
 useEffect(()=>{
  if(!selected){setCollection(null);setCopies([]);return;}
  const c=new AbortController();setLoading(true);setError('');setCollection(null);setCopies([]);
  Promise.all([api<SavedCollection>(`custom-collections/${selected}`,{signal:c.signal}),api<InventoryCopy[]>(`inventory?custom_collection_id=${selected}&limit=21&offset=${page*20}`,{signal:c.signal})]).then(([item,items])=>{if(!c.signal.aborted){setCollection(item);setCopies(items.slice(0,20));setMore(items.length>20);}}).catch(e=>{if(!c.signal.aborted){setError(errorText(e));}}).finally(()=>{if(!c.signal.aborted)setLoading(false);});return()=>c.abort();
 },[selected,page,version,refresh]);
 function choose(id:string){setSelected(id);setPage(0);setNotice('');}
 return <details className="collection-authoring" open={open} onToggle={event=>setOpen(event.currentTarget.open)}><summary>Your custom collections</summary>
  <label htmlFor="saved-collection">Collection</label><select id="saved-collection" value={selected} disabled={locked} onChange={e=>choose(e.target.value)}><option value="">Choose a saved collection</option>{selected&&!choices.some(c=>c.id===selected)&&<option value={selected}>{collection?.name||'Selected collection'}</option>}{choices.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>
  {!choices.length&&<p>No collections on this page. Create one from a reviewed JSON definition above.</p>}
  <button type="button" disabled={locked||loading||listPage===0} onClick={()=>setListPage(p=>p-1)}>Previous collections</button><button type="button" disabled={locked||loading||!listMore} onClick={()=>setListPage(p=>p+1)}>More collections</button>
  {error&&<p className="error" role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}{loading&&<p role="status">Loading collection…</p>}
  {collection&&<section aria-label={`Saved collection: ${collection.name}`}><h2>{collection.name}</h2><p>This checklist describes your collecting goal. Progress uses only your reviewed matches to owned figures.</p>
   <CollectionDefinitionExport key={collection.id} collectionId={collection.id} locked={locked||loading} />
   <ChecklistProgress collectionId={collection.id} refresh={refresh} locked={locked||loading} addFigure={entryId=>startFigure(collection.id,entryId)} />
   <CustomDefinitionEditor key={collection.id+'-'+collection.type_revision} collection={collection} locked={locked} runSave={runSave} saved={next=>{setCollection(next);setVersion(v=>v+1);setNotice('Field controls updated. Existing figures were preserved.');}} />
   <button type="button" disabled={locked||loading} onClick={async()=>{try{setCollection(await api<SavedCollection>(`custom-collections/${selected}`));setError('');}catch(e){setError(errorText(e));}}}>Reload field controls</button>
   <button type="button" disabled={locked||loading} onClick={()=>onIntake(selected)}>Add an item to this collection</button>
   <h3>Your saved figures</h3><p>Photos, storage and edit history are available when you open a figure.</p>
   <ul>{copies.map(copy=><li key={copy.id}><button type="button" disabled={locked} onClick={()=>openCopy(copy.id)}>{copy.title||'Untitled figure'}</button></li>)}</ul>{!copies.length&&<p>No figures on this page.</p>}
   <button type="button" disabled={locked||loading||page===0} onClick={()=>setPage(v=>v-1)}>Previous figures</button><button type="button" disabled={locked||loading||!more} onClick={()=>setPage(v=>v+1)}>More figures</button>
  </section>}
 </details>;
}
