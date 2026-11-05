'use client';

import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type RefObject } from 'react';
import { api, ApiError, errorText, jsonSave, type CollectionSettings, type CollectionTypes, type RecordField, type ComicField, type MovieField, type CollectionTypeId, type RunSave } from '../lib/inventory-client';

type Props = { focusType?:CollectionTypeId; guard?:RefObject<()=>boolean>; preserveDraft?:boolean; open: boolean; close: () => void; types: CollectionTypes; settings: CollectionSettings; runSave: RunSave; locked: boolean; saved: (value: CollectionSettings) => void; reload: () => void };

export default function CollectionSetup({ types, settings, runSave, locked, saved, reload, open, close, focusType, guard, preserveDraft=false }: Props) {
  const fields = types.record.fields as (typeof types.record.fields[number] & {key: RecordField})[];
  const [step, setStep] = useState(1);
  const [moviesEnabled,setMoviesEnabled] = useState(!!settings.movies_enabled);
  const [movieSelected,setMovieSelected] = useState<MovieField[]>(settings.movie_fields || ['media_format','studio','edition','notes']);
  const [comicsEnabled, setComicsEnabled] = useState(!!settings.comics_enabled);
  const [comicSelected, setComicSelected] = useState<ComicField[]>(settings.comic_fields || ['issue_number','publisher','edition','notes']);
  const [enabled, setEnabled] = useState(settings.records_enabled);
  const [defaultType, setDefaultType] = useState(settings.default_type);
  const [selected, setSelected] = useState<RecordField[]>(settings.record_fields);
  const [error, setError] = useState('');
  const [review, setReview] = useState(false);
  const [notice, setNotice] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  function start(value=settings) { setStep(1);setMoviesEnabled(!!value.movies_enabled);setMovieSelected(value.movie_fields || ['media_format','studio','edition','notes']); setComicsEnabled(!!value.comics_enabled); setComicSelected(value.comic_fields || types.comic.fields.filter(field=>field.suggested).map(field=>field.key as ComicField)); setEnabled(value.records_enabled); setDefaultType(value.default_type); setSelected(value.status==='not_started' && value.revision===0 ? fields.filter(field=>field.suggested).map(field=>field.key) : value.record_fields); setError(''); setReview(false); setNotice(''); }
  useEffect(() => {
    if (open) { if(!preserveDraft)start(); heading.current?.focus(); }
  }, [open]);
  const focusedDirty=focusType==='record'?JSON.stringify([...selected].sort())!==JSON.stringify([...settings.record_fields].sort()):focusType==='comic'?JSON.stringify([...comicSelected].sort())!==JSON.stringify([...(settings.comic_fields||[])].sort()):focusType==='movie'?JSON.stringify([...movieSelected].sort())!==JSON.stringify([...(settings.movie_fields||['media_format','studio','edition','notes'])].sort()):false;
  const dirty=focusType?focusedDirty:moviesEnabled!==!!settings.movies_enabled||comicsEnabled!==!!settings.comics_enabled||enabled!==settings.records_enabled||defaultType!==settings.default_type||JSON.stringify([...selected].sort())!==JSON.stringify([...settings.record_fields].sort())||JSON.stringify([...comicSelected].sort())!==JSON.stringify([...(settings.comic_fields||[])].sort())||JSON.stringify([...movieSelected].sort())!==JSON.stringify([...(settings.movie_fields||['media_format','studio','edition','notes'])].sort());
  function canReplace(){return !(locked||review)&&(!dirty||window.confirm('Discard the unsaved entry preferences?'));}
  useLayoutEffect(()=>{if(guard)guard.current=canReplace;return()=>{if(guard)guard.current=()=>true;};});
  useEffect(()=>{function warn(e:BeforeUnloadEvent){if(dirty||review){e.preventDefault();e.returnValue='';}}window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[dirty,review]);
  async function reloadSaved(){if(dirty||review){if(!window.confirm('Reload saved preferences and discard this local draft?'))return;}try{const value=await api<CollectionSettings>('collection-settings');saved(value);start(value);}catch(problem){setError(errorText(problem));}}
  function next(value: number) { setStep(value); requestAnimationFrame(() => heading.current?.focus()); }
  async function commit(status: 'configured' | 'skipped') {
    if (locked || review) return;
    try {
      await runSave(async () => {
        setError(''); setNotice('Saving collection setup…');
        const result = await api<CollectionSettings>('collection-settings', jsonSave(focusType?{status:'configured',records_enabled:settings.records_enabled,comics_enabled:!!settings.comics_enabled,movies_enabled:!!settings.movies_enabled,default_type:settings.default_type,record_fields:focusType==='record'?selected:settings.record_fields,comic_fields:focusType==='comic'?comicSelected:settings.comic_fields||[],movie_fields:focusType==='movie'?movieSelected:settings.movie_fields||['media_format','studio','edition','notes'],expected_revision:settings.revision}:{status, records_enabled:status==='skipped' ? settings.records_enabled : enabled,
          default_type:status==='skipped' ? settings.default_type : defaultType==='record' && !enabled || defaultType==='comic' && !comicsEnabled || defaultType==='movie' && !moviesEnabled ? 'other' : defaultType, movies_enabled:status==='skipped' ? !!settings.movies_enabled : moviesEnabled, movie_fields:status==='skipped' ? settings.movie_fields || ['media_format','studio','edition','notes'] : movieSelected, comics_enabled:status==='skipped' ? !!settings.comics_enabled : comicsEnabled, comic_fields:status==='skipped' ? settings.comic_fields || ['issue_number','publisher','edition','notes'] : comicSelected, record_fields:status==='skipped' ? settings.record_fields : selected, expected_revision:settings.revision}));
        saved(result); if(!focusType){setStep(1);close();} setNotice(status==='skipped' ? 'Setup skipped. You can set it up anytime.' : focusType?'Entry preferences saved. Existing values are unchanged.':'Collection setup saved. Only a title is required when adding a find.');
      });
    } catch (problem) { setNotice(''); setError(errorText(problem)); setReview(problem instanceof ApiError && (problem.uncertain || problem.status===409)); }
  }
  function submit(event: FormEvent) { event.preventDefault(); if(step===1) next(enabled || comicsEnabled || moviesEnabled ? 2 : 3); else if(step===2) next(3); else void commit('configured'); }
  if(focusType){const definition=types[focusType],chosen=focusType==='record'?selected:focusType==='comic'?comicSelected:movieSelected;function choose(key:string,checked:boolean){if(focusType==='record')setSelected(v=>checked?[...v,key as RecordField]:v.filter(k=>k!==key));else if(focusType==='comic')setComicSelected(v=>checked?[...v,key as ComicField]:v.filter(k=>k!==key));else setMovieSelected(v=>checked?[...v,key as MovieField]:v.filter(k=>k!==key));setNotice('');}
    return <section className="collection-preferences" aria-label={`${definition.plural_label} entry preferences`}><h2 ref={heading} tabIndex={-1}>{definition.plural_label} entry preferences</h2><p>Choose optional fields for new items. Hiding a field never deletes saved values.</p><div className="management-split"><form onSubmit={e=>{e.preventDefault();void commit('configured');}}><fieldset disabled={locked||review||focusType==='other'}><legend>Visible fields</legend><label className="custom-choice"><input type="checkbox" checked disabled/>{definition.title.label} — always shown</label>{definition.fields.map(field=><label className="custom-choice" key={field.key}><input type="checkbox" checked={focusType==='other'||chosen.includes(field.key as never)} onChange={e=>choose(field.key,e.target.checked)}/>{field.label}</label>)}{focusType!=='other'&&<button className="primary" type="submit">Save entry preferences</button>}</fieldset></form><aside className="management-preview"><h3>New-item preview</h3><fieldset disabled>{definition.entry_order.map(key=>key==='title'?<label key={key}>{definition.title.label}<input placeholder="Example title"/></label>:definition.fields.find(f=>f.key===key)&& (focusType==='other'||chosen.includes(key as never))?<label key={key}>{definition.fields.find(f=>f.key===key)!.label} (optional){definition.fields.find(f=>f.key===key)!.input==='select'?<select><option>Not specified</option>{definition.fields.find(f=>f.key===key)!.options?.map(option=><option key={option}>{option}</option>)}<option>Other…</option></select>:key==='notes'?<textarea rows={3}/>:<input/>}</label>:null)}</fieldset><p className="hint">Illustrative only. Nothing entered here is saved.</p></aside></div>{focusType==='other'&&<p>Other is always available. Its basic entry fields are fixed in this version.</p>}{error&&<p className="error" role="alert">{error} <button type="button" disabled={locked} onClick={()=>void reloadSaved()}>Reload saved preferences</button></p>}<p role="status">{notice}</p></section>;
  }
  return <section className="collection-setup" aria-label="Collection setup">
    {open && <div id="collection-editor">
      <h2 ref={heading} tabIndex={-1}>Collection setup · Step {step} of 3</h2>
      <form onSubmit={submit} aria-label="Set up collection"><fieldset disabled={locked || review}>
        {step===1 && <><h3>What do you collect?</h3><p>Albums, Comics and Movies have tailored fields. Use Other for anything else.</p>
          <label><input type="checkbox" checked={enabled} onChange={event => { setEnabled(event.target.checked); if(event.target.checked && defaultType==='other')setDefaultType('record');else if(!event.target.checked && defaultType==='record')setDefaultType('other'); }} /> {types.record.plural_label}</label>
          <label><input type="checkbox" checked={comicsEnabled} onChange={event=>{setComicsEnabled(event.target.checked);if(event.target.checked && defaultType==='other')setDefaultType('comic');else if(!event.target.checked && defaultType==='comic')setDefaultType('other');}} /> {types.comic.plural_label}</label>
          <label><input type="checkbox" checked={moviesEnabled} onChange={event=>{setMoviesEnabled(event.target.checked);if(event.target.checked && defaultType==='other')setDefaultType('movie');else if(!event.target.checked && defaultType==='movie')setDefaultType('other');}} /> {types.movie?.plural_label || 'Movies'}</label>
          <p className="hint">Other is always available. Existing finds keep their type and details.</p>
          {(enabled || comicsEnabled || moviesEnabled) && <><label htmlFor="default-type">Start new finds as</label><select id="default-type" value={defaultType} onChange={event => setDefaultType(event.target.value as CollectionTypeId)}>{Object.values(types).filter(type=>type.id==='other' || type.id==='record' && enabled || type.id==='comic' && comicsEnabled || type.id==='movie' && moviesEnabled).map(type=><option key={type.id} value={type.id}>{type.label}</option>)}</select></>}
        </>}
        {step===2 && <>{enabled && <><h3>What matters to you about your {types.record.plural_label.toLowerCase()}?</h3><p>Choose the fields you want to see. All of them are optional when adding an album.</p>
          <p>{types.record.title.label} is always shown.</p>{fields.map(field => <label key={field.key}><input type="checkbox" checked={selected.includes(field.key)} onChange={event => setSelected(before => event.target.checked ? [...before,field.key] : before.filter(key => key!==field.key))} /> {field.label}</label>)}
          </>}
          {comicsEnabled && <><h3>What matters to you about your comics?</h3><p>{types.comic.title.label} is always shown. Other fields are optional.</p>
            {types.comic.fields.map(field=><label key={field.key}><input type="checkbox" checked={comicSelected.includes(field.key as ComicField)} onChange={event=>setComicSelected(before=>event.target.checked ? [...before,field.key as ComicField] : before.filter(key=>key!==field.key))} /> {field.label}</label>)}
          </>}
          {moviesEnabled && <><h3>What matters to you about your movies?</h3><p>{types.movie?.title.label || 'Movie or box-set title'} is always shown. Other fields are optional.</p>
            {types.movie?.fields.map(field=><label key={field.key}><input type="checkbox" checked={movieSelected.includes(field.key as MovieField)} onChange={event=>setMovieSelected(before=>event.target.checked ? [...before,field.key as MovieField] : before.filter(key=>key!==field.key))} /> {field.label}</label>)}
          </>}
          <p className="hint">These are suggested fields you can adjust. Hiding a field never deletes saved values. Photos and storage remain available after saving.</p>
        </>}
        {step===3 && <><h3>Preview your entry form</h3><p>This example is not added to your collection.</p><div className="setup-preview">
          {Object.values(types).filter(type=>type.id==='other' ? !enabled && !comicsEnabled && !moviesEnabled : type.id==='record' ? enabled : type.id==='movie' ? moviesEnabled : comicsEnabled).map(type=><section key={type.id} aria-label={`${type.label} preview`}><h4>{type.label}</h4>{type.entry_order.map(key=>{
            if(key==='title')return <p key={key}><strong>{type.title.label}:</strong> {type.id==='movie' ? 'Example movie' : type.id==='comic' ? 'Example series' : 'Example album'}</p>;
            const field=type.fields.find(field=>field.key===key);
            const chosen=type.id==='movie' ? movieSelected : type.id==='comic' ? comicSelected : selected;
            return field && (type.id==='other' || chosen.includes(key as never)) ? <p key={key}>{field.label} (optional)</p> : null;
          })}</section>)}
          </div><p>New finds start as {types[defaultType].label}. You can change these choices later in Collection settings.</p></>}
        <div className="setup-actions">{step>1 && <button type="button" onClick={()=>next(step===3 && !enabled && !comicsEnabled && !moviesEnabled ? 1 : step-1)}>Back</button>}<button className="primary" type="submit">{step===3 ? 'Save setup' : 'Continue'}</button><button type="button" className="quiet" onClick={()=>close()}>Cancel setup</button></div>
      </fieldset></form>
      {settings.status==='not_started' && <button className="text-button" disabled={locked || review} onClick={() => void commit('skipped')}>Skip for now</button>}
    </div>}
    {error && <p role="alert" className="error">{error} <button type="button" disabled={locked} onClick={()=>void reloadSaved()}>Reload settings</button></p>}
    <p role="status" className="notice">{notice}</p>
  </section>;
}
