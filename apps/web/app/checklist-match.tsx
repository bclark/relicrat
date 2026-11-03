'use client';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {api,ApiError,errorText,jsonSave,type RunSave} from '../lib/inventory-client';
import type {SavedCollection} from './custom-collections';
type Match={entry_id:string|null;confirmed:boolean;revision:number};
type Event={before_entry_id:string|null;after_entry_id:string|null;before_confirmed:boolean;after_confirmed:boolean;revision:number;created_at:string};
export default function ChecklistMatch({collectionId,copyId,locked,runSave,changed}:{collectionId:string;copyId:string;locked:boolean;runSave:RunSave;changed:()=>void}){
 const path=`custom-collections/${collectionId}/copies/${copyId}`;
 const [collection,setCollection]=useState<SavedCollection|null>(null),[saved,setSaved]=useState<Match|null>(null),[entry,setEntry]=useState(''),[confirmed,setConfirmed]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[review,setReview]=useState(false),[busy,setBusy]=useState(false),[version,setVersion]=useState(0);
 const [history,setHistory]=useState<Event[]>([]),[historyOpen,setHistoryOpen]=useState(false),[historyError,setHistoryError]=useState(''),[historyBusy,setHistoryBusy]=useState(false),[page,setPage]=useState(0),[more,setMore]=useState(false);
 const lock=useRef(false);
 useEffect(()=>{const c=new AbortController();setSaved(null);setCollection(null);setError('');setNotice('');api<SavedCollection>(`custom-collections/${collectionId}`,{signal:c.signal}).then(v=>{if(!c.signal.aborted)setCollection(v);}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));});api<Match>(path+'/checklist-match',{signal:c.signal}).then(v=>{if(!c.signal.aborted){setSaved(v);setEntry(v.entry_id||'');setConfirmed(v.confirmed);setReview(false);}}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));});return()=>c.abort();},[path,collectionId,version]);
 useEffect(()=>{if(!historyOpen)return;const c=new AbortController();setHistoryError('');setHistory([]);setMore(false);setHistoryBusy(true);api<Event[]>(path+`/checklist-history?limit=11&offset=${page*10}`,{signal:c.signal}).then(v=>{if(!c.signal.aborted){setHistory(v.slice(0,10));setMore(v.length>10);}}).catch(e=>{if(!c.signal.aborted)setHistoryError(errorText(e));}).finally(()=>{if(!c.signal.aborted)setHistoryBusy(false);});return()=>c.abort();},[path,historyOpen,page,saved?.revision]);
 const entries=collection?.proposal.collection.checklist||[];
 function label(id:string|null,qualifies:boolean){return id?`${entries.find(e=>e.id===id)?.title||id} (${qualifies?'confirmed qualifying':'needs review'})`:'Unmatched';}
 async function save(event:FormEvent){event.preventDefault();if(!saved||!collection||locked||busy||review||lock.current)return;lock.current=true;setBusy(true);setError('');setNotice('');try{await runSave(async()=>{const value=await api<Match>(path+'/checklist-match',jsonSave({expected_revision:saved.revision,entry_id:entry||null,confirmed:!!entry&&confirmed}));setSaved(value);setEntry(value.entry_id||'');setConfirmed(value.confirmed);setPage(0);setNotice(value.confirmed?'Checklist match saved. This figure qualifies toward this entry.':value.entry_id?'Checklist link saved for review. It does not count yet.':'Checklist match cleared. Its history is retained.');changed();});}catch(e){setReview(e instanceof ApiError&&(e.uncertain||e.status===409));setError(errorText(e));}finally{lock.current=false;setBusy(false);}}
 const disabled=locked||busy||review||!saved||!collection;
 return <section aria-label="Checklist match"><h3>Checklist match</h3><p>Choose which goal this physical figure represents. Names do not confirm an original release.</p>
 {collection&&<p>Eligibility: {collection.proposal.collection.completion.eligibility}</p>}
 {(!saved||!collection)&&!error&&<p role="status">Loading saved checklist match…</p>}
 {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status">{notice}</p>}
 {review&&<p role="status">The save needs review. Reload the saved match to see what was recorded before saving again. Nothing will be retried automatically.</p>}
 <button type="button" disabled={locked||busy} onClick={()=>setVersion(v=>v+1)}>Reload saved checklist match</button><p className="hint">Reload replaces this checklist draft with the saved match. Other copy details are unchanged.</p>
 <form aria-label="Review checklist match" onSubmit={save}><fieldset disabled={disabled}>
 <label htmlFor="checklist-entry">Checklist entry</label><select id="checklist-entry" value={entry} onChange={e=>{setEntry(e.target.value);setConfirmed(false);setNotice('');}}><option value="">Not matched</option>{entries.map(e=><option value={e.id} key={e.id}>{e.title}</option>)}</select>
 <label className="custom-choice"><input type="checkbox" checked={confirmed} disabled={!entry} onChange={e=>setConfirmed(e.target.checked)} />I reviewed this figure and confirm it meets this collection’s eligibility rules.</label>
 <p className="hint">Leave unchecked when uncertain. The link can be saved for review without counting it.</p>
 <button type="submit" disabled={!saved||(saved.entry_id||'')===entry&&saved.confirmed===confirmed}>Save checklist match</button>
 </fieldset></form>
 <details open={historyOpen} onToggle={e=>setHistoryOpen(e.currentTarget.open)}><summary>Checklist match history</summary>{historyError&&<p role="alert" className="error">{historyError}</p>}<ol className="movement-history">{history.map(e=><li key={e.revision}><span>{label(e.before_entry_id,e.before_confirmed)} → {label(e.after_entry_id,e.after_confirmed)}</span><small>Revision {e.revision} · {new Date(e.created_at).toLocaleString()}</small></li>)}</ol>{historyBusy&&<p role="status">Loading checklist history…</p>}{!historyBusy&&!history.length&&!historyError&&<p>No checklist changes on this page.</p>}<button type="button" disabled={page===0||busy||historyBusy} onClick={()=>setPage(v=>v-1)}>Previous checklist changes</button><button type="button" disabled={!more||busy||historyBusy} onClick={()=>setPage(v=>v+1)}>More checklist changes</button></details>
 </section>;
}
