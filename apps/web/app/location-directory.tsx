import {useEffect,useState} from 'react';
import {api,errorText,type Location} from '../lib/inventory-client';

const PAGE_SIZE = 20;

export default function LocationDirectory({parentId,open,busy,refresh}:{
  parentId?:string;
  open:(location:Location)=>void;
  busy:boolean;
  refresh:number;
}){
  const [page,setPage]=useState(0);
  const [locations,setLocations]=useState<Location[]|null>(null);
  const [error,setError]=useState('');
  const [retry,setRetry]=useState(0);

  useEffect(()=>{
    const controller=new AbortController();
    const parent=parentId?`parent_id=${parentId}`:'root_only=true';
    api<Location[]>(`storage-locations?${parent}&limit=${PAGE_SIZE+1}&offset=${page*PAGE_SIZE}`,{signal:controller.signal})
      .then(result=>{if(!controller.signal.aborted){setLocations(result);setError('');}})
      .catch(problem=>{if(!controller.signal.aborted)setError(errorText(problem));});
    return ()=>controller.abort();
  },[parentId,page,refresh,retry]);

  function changePage(next:number){
    setLocations(null);
    setError('');
    setPage(next);
  }

  return <section aria-label={parentId?'Nested locations':'Top-level locations'}>
    <h2>{parentId?'Inside this location':'Top-level locations'}</h2>
    {error?<p role="alert" className="error">{error} <button type="button" disabled={busy} onClick={()=>{setError('');setRetry(value=>value+1);}}>Retry locations</button></p>
      :locations===null?<p role="status">Loading locations…</p>
      :locations.length?<ul>{locations.slice(0,PAGE_SIZE).map(location=><li key={location.id}>
        <button type="button" className="collection-link" disabled={busy} onClick={()=>open(location)}>{location.name}</button>
      </li>)}</ul>:<p>{parentId?'No nested locations.':'No storage locations yet. You can create one from a copy’s Storage section.'}</p>}
    {(page>0||(locations?.length??0)>PAGE_SIZE)&&<nav aria-label="Location pages" className="pagination">
      <button type="button" disabled={busy||page===0} onClick={()=>changePage(page-1)}>Previous locations</button>
      <span>Page {page+1}</span>
      <button type="button" disabled={busy||!locations||locations.length<=PAGE_SIZE} onClick={()=>changePage(page+1)}>Next locations</button>
    </nav>}
  </section>;
}
