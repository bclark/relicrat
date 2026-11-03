'use client';
import {useEffect,useState} from 'react';
import {api,errorText,type CollectionTypes} from '../lib/inventory-client';
type Choice={id:string;name:string};
export default function CollectionFilter({value,change,types,busy,refresh}:{value:string;change:(value:string)=>void;types:CollectionTypes|null;busy:boolean;refresh:number}){
 const [choices,setChoices]=useState<Choice[]>([]),[page,setPage]=useState(0),[more,setMore]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState(''),[version,setVersion]=useState(0),[selected,setSelected]=useState<Choice|null>(null);
 const selectedId=value.startsWith('custom:')?value.slice(7):'';
 useEffect(()=>{const c=new AbortController();setLoading(true);setError('');setChoices([]);setMore(false);api<Choice[]>(`custom-collections?limit=51&offset=${page*50}`,{signal:c.signal}).then(v=>{if(!c.signal.aborted){setChoices(v.slice(0,50));setMore(v.length>50);}}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));}).finally(()=>{if(!c.signal.aborted)setLoading(false);});return()=>c.abort();},[page,refresh,version]);
 useEffect(()=>{setSelected(null);if(!selectedId)return;const c=new AbortController();api<Choice>(`custom-collections/${selectedId}`,{signal:c.signal}).then(v=>{if(!c.signal.aborted)setSelected(v);}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));});return()=>c.abort();},[selectedId,version]);
 return <><label htmlFor="collection-type-filter">Show collection</label><select id="collection-type-filter" value={value} disabled={busy||!types} onChange={e=>change(e.target.value)}><option value="">All types</option><optgroup label="Collection types">{types&&Object.values(types).map(type=><option key={type.id} value={type.id}>{type.plural_label}</option>)}</optgroup><optgroup label="Custom collections">{selectedId&&!choices.some(c=>c.id===selectedId)&&<option value={value}>{selected?.name||'Selected custom collection'}</option>}{choices.map(c=><option value={'custom:'+c.id} key={c.id}>{c.name}</option>)}</optgroup></select>
 {loading&&<p role="status">Loading custom collection choices…</p>}{error&&<p role="alert" className="error">Custom collection choices unavailable. {error} <button type="button" disabled={busy||loading} onClick={()=>setVersion(v=>v+1)}>Reload collection choices</button></p>}
 {(page>0||more)&&<div><button type="button" disabled={busy||loading||page===0} onClick={()=>setPage(p=>p-1)}>Previous collection choices</button><button type="button" disabled={busy||loading||!more} onClick={()=>setPage(p=>p+1)}>More collection choices</button></div>}</>;
}
