import {useId,useRef,useState,type FormEvent} from 'react';
import {api,ApiError,errorText,jsonSave,type Location,type RunSave} from '../lib/inventory-client';
import LocationDirectory from './location-directory';

export default function LocationEditor({path,location,busy,runSave,onSaved,onCancel}:{
  path:Location[];
  location?:Location;
  busy:boolean;
  runSave:RunSave;
  onSaved:(path:Location[])=>void;
  onCancel:()=>void;
}){
  const id=useId();
  const [name,setName]=useState(location?.name||'');
  const [destination,setDestination]=useState(path);
  const [picker,setPicker]=useState<Location[]|null>(null);
  const [error,setError]=useState('');
  const [uncertain,setUncertain]=useState(false);
  const pending=useRef(false);
  const parentId=destination.at(-1)?.id??null;
  const disabled=busy||uncertain;
  const unchanged=location?.name===name.trim()&&location?.parent_id===parentId;

  async function save(event:FormEvent){
    event.preventDefault();
    if(disabled||pending.current||!name.trim()||unchanged||picker)return;
    pending.current=true;
    setError('');
    try{
      const fields={name:name.trim(),parent_id:parentId};
      const saved=await runSave(()=>location
        ?api<Location>(`storage-locations/${location.id}`,jsonSave({
          ...fields,expected_name:location.name,expected_parent_id:location.parent_id,
        }))
        :api<Location>('storage-locations',jsonSave(fields)));
      if(saved)onSaved([...destination,saved]);
    }catch(problem){
      setError(errorText(problem));
      if(problem instanceof ApiError&&problem.uncertain)setUncertain(true);
    }finally{pending.current=false;}
  }

  return <form aria-label={location?'Edit location':'Create location'} onSubmit={save}>
    <label htmlFor={id}>Location name</label>
    <input id={id} value={name} onChange={event=>setName(event.target.value)} maxLength={250} required disabled={disabled}/>
    {location&&<button type="button" className="text-button" disabled={disabled} onClick={()=>setPicker(picker?null:[])} aria-expanded={picker!==null}>Choose a different parent</button>}
    {picker&&<section aria-label="Choose parent location">
      <p>{picker.length?picker.map(place=>place.name).join(' / '):'Top level'}</p>
      {picker.length>0&&<button type="button" disabled={disabled} onClick={()=>setPicker(picker.slice(0,-1))}>Back up one level</button>}
      <button type="button" disabled={disabled} onClick={()=>{setDestination(picker);setPicker(null);}}>Use this destination</button>
      <p className="hint">A location cannot be moved inside itself or one of its nested locations.</p>
      <LocationDirectory key={picker.at(-1)?.id||'root'} parentId={picker.at(-1)?.id} excludedId={location?.id} open={place=>setPicker([...picker,place])} busy={disabled} refresh={0}/>
    </section>}
    <p>New path <strong>{[...destination.map(place=>place.name),name.trim()].filter(Boolean).join(' / ')||'Top level'}</strong></p>
    {error&&<p role="alert" className="error">{error}{uncertain?' Reopen Browse locations to check whether the change was saved.':''}</p>}
    <div className="form-actions">
      <button type="submit" className="primary" disabled={disabled||!name.trim()||unchanged||picker!==null}>{location?'Save location':'Create location'}</button>
      <button type="button" disabled={busy} onClick={onCancel}>Cancel</button>
    </div>
  </form>;
}
