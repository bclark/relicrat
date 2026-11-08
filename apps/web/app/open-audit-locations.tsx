import {useEffect,useState} from 'react';
import {api,errorText} from '../lib/inventory-client';
import {locationLink} from '../lib/location-link';

type Row={id:string;name:string;unresolved:number};
const PAGE=20;

export default function OpenAuditLocations(){
  const [page,setPage]=useState(0);
  const [rows,setRows]=useState<Row[]|null>(null);
  const [error,setError]=useState('');
  useEffect(()=>{
    const controller=new AbortController();
    api<Row[]>(`storage-locations/audits/open?limit=${PAGE+1}&offset=${page*PAGE}`,{signal:controller.signal})
      .then(result=>{if(!controller.signal.aborted)setRows(result);})
      .catch(problem=>{if(!controller.signal.aborted)setError(errorText(problem));});
    return()=>controller.abort();
  },[page]);

  function navigate(next:number){setRows(null);setError('');setPage(next);}

  return <section aria-label="Locations with unresolved findings">
    <h2>Locations with unresolved findings</h2>
    {error?<p role="alert">{error}</p>:!rows?<p role="status">Loading unresolved findings…</p>
      :rows.length?<ul>{rows.slice(0,PAGE).map(row=><li key={row.id}>
        <a href={locationLink(row.id)}>{row.name}</a> · {row.unresolved} unresolved
      </li>)}</ul>:<p>No locations with unresolved findings on this page.</p>}
    {(page>0||(rows?.length??0)>PAGE)&&<nav aria-label="Unresolved locations pages" className="pagination">
      <button type="button" disabled={page===0} onClick={()=>navigate(page-1)}>Previous</button>
      <button type="button" disabled={!rows||rows.length<=PAGE} onClick={()=>navigate(page+1)}>Next</button>
    </nav>}
  </section>;
}
