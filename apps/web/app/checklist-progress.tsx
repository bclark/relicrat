'use client';
import {useEffect,useState} from 'react';
import {api,errorText} from '../lib/inventory-client';
type Progress={completed:number;total:number;unassigned_copies:number;entries:{id:string;title:string;confirmed_copies:number;pending_copies:number}[]};
export default function ChecklistProgress({collectionId,refresh,addFigure,locked=false}:{collectionId:string;refresh:number;addFigure?:(entryId:string)=>void;locked?:boolean}){
 const [value,setValue]=useState<Progress|null>(null),[error,setError]=useState(''),[missing,setMissing]=useState(false),[expanded,setExpanded]=useState(false),[version,setVersion]=useState(0);
 useEffect(()=>{const controller=new AbortController();setValue(null);setError('');api<Progress>(`custom-collections/${collectionId}/progress`,{signal:controller.signal}).then(v=>{if(!controller.signal.aborted)setValue(v);}).catch(e=>{if(!controller.signal.aborted)setError(errorText(e));});return()=>controller.abort();},[collectionId,refresh,version]);
 return <section aria-label="Checklist progress"><h3>Checklist progress</h3>
 {error&&<p role="alert" className="error">Progress could not be loaded. {error}</p>}
 {!value&&!error&&<p role="status">Loading checklist progress…</p>}
 {value&&<><p role="status"><strong>{value.completed} of {value.total} collected</strong> — owner-confirmed qualifying figures.</p><p>Duplicates and variants count once per entry. Unreviewed, sold, traded, lost and removed figures do not count.</p>
 <p>Owned figures without a checklist match: {value.unassigned_copies}. Open a saved figure to review its match.</p>
 <details open={expanded} onToggle={e=>setExpanded(e.currentTarget.open)}><summary>View checklist and missing entries</summary><label className="custom-choice"><input type="checkbox" checked={missing} onChange={e=>setMissing(e.target.checked)} />Show only entries without a confirmed figure</label>
 <ul>{value.entries.filter(e=>!missing||e.confirmed_copies===0).map(e=><li key={e.id}><strong>{e.title}</strong> — {e.confirmed_copies?`Collected · Qualifying figures: ${e.confirmed_copies}`:e.pending_copies?`Needs review · Linked figures: ${e.pending_copies}`:'Missing — no confirmed figure'}{addFigure&&e.confirmed_copies===0&&e.pending_copies===0&&<> <button type="button" disabled={locked} aria-label={`Add this figure: ${e.title}`} onClick={()=>addFigure(e.id)}>Add this figure</button></>}</li>)}</ul>
 {missing&&value.completed===value.total&&<p>Every entry has a confirmed qualifying figure.</p>}</details></>}
 <button type="button" onClick={()=>setVersion(v=>v+1)}>Refresh checklist progress</button></section>;
}
