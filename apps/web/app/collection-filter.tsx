'use client';
import {useEffect,useState} from 'react';
import {api,errorText,type CollectionTypes} from '../lib/inventory-client';
type Choice={id:string;name:string};
export default function CollectionFilter({value,change,types,busy,refresh,compact=false,homeHeadingId}:{value:string;change:(value:string)=>void;types:CollectionTypes|null;busy:boolean;refresh:number;compact?:boolean;homeHeadingId?:string}){
 const [choices,setChoices]=useState<Choice[]>([]),[page,setPage]=useState(0),[more,setMore]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState(''),[version,setVersion]=useState(0),[selected,setSelected]=useState<Choice|null>(null);
 const selectedId=value.startsWith('custom:')?value.slice(7):'';
 useEffect(()=>{const c=new AbortController();setLoading(true);setError('');setChoices([]);setMore(false);api<Choice[]>(`custom-collections?limit=51&offset=${page*50}`,{signal:c.signal}).then(v=>{if(!c.signal.aborted){setChoices(v.slice(0,50));setMore(v.length>50);}}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));}).finally(()=>{if(!c.signal.aborted)setLoading(false);});return()=>c.abort();},[page,refresh,version]);
 useEffect(()=>{setSelected(null);if(!selectedId)return;const c=new AbortController();api<Choice>(`custom-collections/${selectedId}`,{signal:c.signal}).then(v=>{if(!c.signal.aborted)setSelected(v);}).catch(e=>{if(!c.signal.aborted)setError(errorText(e));});return()=>c.abort();},[selectedId,version]);
 const showCurrent=!homeHeadingId;
 const builtins=types?Object.values(types):[];
 return <nav className={`collection-navigation${compact?' compact-choice':''}`} aria-label={compact?'Item destination':'Collections'}>
 <div className="collection-links" hidden={compact}>{homeHeadingId?<h1 id={homeHeadingId} tabIndex={-1}>Your collections</h1>:<h2>Collections</h2>}<button type="button" className="collection-link" data-collection="" aria-current={showCurrent&&!value?'page':undefined} disabled={busy||!types} onClick={()=>change('')}>All items</button>
 {builtins.map(type=><button type="button" className="collection-link" data-collection={type.id} aria-current={showCurrent&&value===type.id?'page':undefined} disabled={busy} key={type.id} onClick={()=>change(type.id)}>{type.plural_label}</button>)}
 {selectedId&&!choices.some(c=>c.id===selectedId)&&<button type="button" className="collection-link" data-collection={value} aria-current={showCurrent?"page":undefined} disabled={busy} onClick={()=>change(value)}>{selected?.name||'Selected collection'}</button>}
 {choices.map(c=><button type="button" className="collection-link" key={c.id} data-collection={'custom:'+c.id} aria-current={showCurrent&&value==='custom:'+c.id?'page':undefined} disabled={busy} onClick={()=>change('custom:'+c.id)}>{c.name}</button>)}
</div>
 {compact&&<div className="mobile-collection-choice"><label htmlFor="intake-destination">Collection</label><select id="intake-destination" value={value} disabled={busy||!types} onChange={e=>change(e.target.value)}>{builtins.map(type=><option key={type.id} value={type.id}>{type.plural_label}</option>)}{selectedId&&!choices.some(c=>c.id===selectedId)&&<option value={value}>{selected?.name||'Selected collection'}</option>}{choices.map(c=><option value={'custom:'+c.id} key={c.id}>{c.name}</option>)}</select></div>}
 {loading&&<p role="status">Loading collections…</p>}{error&&<p role="alert" className="error">Some collections could not be loaded. {error} <button type="button" disabled={busy||loading} onClick={()=>setVersion(v=>v+1)}>Reload collection choices</button></p>}
 {(page>0||more)&&<div className="collection-choice-pages"><button type="button" disabled={busy||loading||page===0} onClick={()=>setPage(p=>p-1)}>Previous collection choices</button><button type="button" disabled={busy||loading||!more} onClick={()=>setPage(p=>p+1)}>More collection choices</button></div>}</nav>;
}
