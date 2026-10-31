'use client';
import {useEffect,useState} from 'react';
import {api,errorText,type Location} from '../lib/inventory-client';
export default function StorageFilter({value,change,busy,refresh}:{value:string;change:(value:string)=>void;busy:boolean;refresh:number}){
 const [locations,setLocations]=useState<Location[]>([]),[offset,setOffset]=useState(0),[more,setMore]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState(''),[version,setVersion]=useState(0);
 useEffect(()=>{const controller=new AbortController();setLoading(true);setError('');
  api<Location[]>(`storage-locations?limit=100&offset=${offset}`,{signal:controller.signal}).then(result=>{if(!controller.signal.aborted){setLocations(old=>Array.from(new Map([...old,...result].map(l=>[l.id,l])).values()));setMore(result.length===100);}}).catch(e=>{if(!controller.signal.aborted)setError(errorText(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();
 },[offset,refresh,version]);
 function label(location:Location){const names=[location.name],seen=new Set([location.id]);let parent=location.parent_id;while(parent&&!seen.has(parent)){seen.add(parent);const p=locations.find(l=>l.id===parent);if(!p){names.unshift('…');break;}names.unshift(p.name);parent=p.parent_id;}return names.join(' / ');}
 return <><label htmlFor="collection-storage-filter">Storage location</label><select id="collection-storage-filter" value={value} disabled={busy} onChange={e=>change(e.target.value)}><option value="">All locations</option><option value="unassigned">Not assigned</option>{locations.map(location=><option key={location.id} value={location.id}>{label(location)}</option>)}</select><p className="hint">Matches copies stored directly at the selected location. Imported box labels need a reviewed storage assignment first.</p>{loading&&<p role="status">Loading locations…</p>}{error&&<p className="error" role="alert">{error} <button disabled={busy||loading} onClick={()=>setVersion(version+1)}>Reload filter locations</button></p>}{more&&<button disabled={busy||loading||!!error} onClick={()=>setOffset(offset+100)}>Load more filter locations</button>}</>;
}
