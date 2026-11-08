import {useState,type FormEvent} from 'react';
import {api,errorText,type InventoryCopy,type Location} from '../lib/inventory-client';
import LocationDirectory from './location-directory';

export type Finding = {kind:'missing';id:string;title:string} | {kind:'extra';index:number;title:string};
export type Resolution =
  | {action:'found';copy_id:string}
  | {action:'move_missing';copy_id:string;destination_id:string;expected_storage_revision:number}
  | {action:'match_extra';extra_index:number;copy_id:string;expected_storage_revision:number}
  | {action:'create_extra';extra_index:number;title:string;collection_type:string};

export default function AuditResolution({finding,box,expected,busy,confirm,cancel}:{
  finding:Finding;box:Location;expected:Set<string>;busy:boolean;
  confirm:(action:Resolution)=>Promise<void>;cancel:()=>void;
}){
  const [mode,setMode]=useState<'found'|'move'|'match'|'create'>(finding.kind==='missing'?'found':'match');
  const [path,setPath]=useState<Location[]>([]);
  const [query,setQuery]=useState(finding.title);
  const [matches,setMatches]=useState<InventoryCopy[]|null>(null);
  const [match,setMatch]=useState<InventoryCopy|null>(null);
  const [title,setTitle]=useState(finding.title);
  const [type,setType]=useState('other');
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(false);
  const [missing,setMissing]=useState<InventoryCopy|null>(null);
  const destination=path.at(-1);
  const locked=busy||loading;

  async function move(){
    if(finding.kind!=='missing')return;
    setError('');setLoading(true);
    try{
      setMissing(await api<InventoryCopy>(`inventory/${finding.id}`));
      setMode('move');
    }catch(problem){setError(errorText(problem));}
    finally{setLoading(false);}
  }

  async function search(event:FormEvent){
    event.preventDefault();
    if(locked||!query.trim())return;
    setError('');setMatches(null);setMatch(null);setLoading(true);
    try{
      const copies=await api<InventoryCopy[]>(`inventory?limit=50&q=${encodeURIComponent(query.trim())}`);
      setMatches(copies.filter(copy=>copy.ownership_status==='owned'&&!expected.has(copy.id)));
    }catch(problem){setError(errorText(problem));}
    finally{setLoading(false);}
  }

  return <section aria-label="Resolve discrepancy">
    <h4>Resolve {finding.title}</h4>
    {finding.kind==='missing'?<>
      <button type="button" disabled={locked} aria-pressed={mode==='found'} onClick={()=>setMode('found')}>Found in this box</button>
      <button type="button" disabled={locked} aria-pressed={mode==='move'} onClick={()=>void move()}>Found elsewhere</button>
      {mode==='found'?<>
        <p>Record that you found this copy in {box.name}.</p>
        <button type="button" disabled={locked} onClick={()=>void confirm({action:'found',copy_id:finding.id})}>Confirm found</button>
      </>:<>
        <p>Choose where you found this copy. Confirming updates its storage assignment.</p>
        <p>Destination <strong>{path.map(location=>location.name).join(' / ')||'All locations'}</strong></p>
        {destination&&<button type="button" disabled={locked} onClick={()=>setPath(path.slice(0,-1))}>Back up one level</button>}
        <LocationDirectory key={destination?.id||'root'} parentId={destination?.id} open={place=>setPath([...path,place])} busy={locked} refresh={0}/>
        {destination&&destination.id!==box.id&&missing&&<button type="button" disabled={locked}
          onClick={()=>void confirm({action:'move_missing',copy_id:finding.id,destination_id:destination.id,expected_storage_revision:missing.storage_revision})}>Confirm move to {destination.name}</button>}
      </>}
    </>:<>
      <button type="button" disabled={locked} aria-pressed={mode==='match'} onClick={()=>setMode('match')}>Match existing copy</button>
      <button type="button" disabled={locked} aria-pressed={mode==='create'} onClick={()=>setMode('create')}>Add as a new copy</button>
      {mode==='match'?<>
        <form onSubmit={search}>
          <label>Search inventory<input value={query} disabled={locked} maxLength={200} onChange={event=>{setQuery(event.target.value);setMatches(null);setMatch(null);}}/></label>
          <button type="submit" disabled={locked||!query.trim()}>Search inventory</button>
        </form>
        {matches&&(matches.length?<ul>{matches.map(copy=><li key={copy.id}>
          <button type="button" disabled={locked} aria-pressed={match?.id===copy.id} onClick={()=>setMatch(copy)}>
            {[copy.title||'Untitled copy',copy.edition_label,copy.storage_location_name||'No assigned location',`Copy ${copy.id.slice(0,8)}`].filter(Boolean).join(' · ')}
          </button>
        </li>)}</ul>:<p>No eligible copies in these results. Try another search.</p>)}
        {match&&<><p>Assign {match.title||'this copy'} to {box.name}.</p><button type="button" disabled={locked}
          onClick={()=>void confirm({action:'match_extra',extra_index:finding.index,copy_id:match.id,expected_storage_revision:match.storage_revision})}>Confirm match and assignment</button></>}
      </>:<form onSubmit={event=>{
        event.preventDefault();
        if(!locked&&title.trim())void confirm({action:'create_extra',extra_index:finding.index,title:title.trim(),collection_type:type});
      }}>
        <p>The new copy will be stored in {box.name}.</p>
        <label>Copy title<input value={title} maxLength={500} required disabled={locked} onChange={event=>setTitle(event.target.value)}/></label>
        <label>Collection type<select value={type} disabled={locked} onChange={event=>setType(event.target.value)}>
          <option value="other">Other</option><option value="record">Album</option><option value="comic">Comic</option><option value="movie">Movie</option><option value="game">Video game</option>
        </select></label>
        <button type="submit" disabled={locked||!title.trim()}>Confirm new copy</button>
      </form>}
    </>}
    {error&&<p role="alert" className="error">{error}</p>}
    <button type="button" disabled={locked} onClick={cancel}>Leave unresolved</button>
  </section>;
}
