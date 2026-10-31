'use client';

import { useRef, useState, type FormEvent } from 'react';
import { api, ApiError, errorText, jsonSave, type CollectionSettings, type CollectionTypes, type RecordField, type ComicField, type CollectionTypeId, type RunSave } from '../lib/inventory-client';

type Props = { types: CollectionTypes; settings: CollectionSettings; runSave: RunSave; locked: boolean; saved: (value: CollectionSettings) => void; reload: () => void };

export default function CollectionSetup({ types, settings, runSave, locked, saved, reload }: Props) {
  const fields = types.record.fields as (typeof types.record.fields[number] & {key: RecordField})[];
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(1);
  const [comicsEnabled, setComicsEnabled] = useState(!!settings.comics_enabled);
  const [comicSelected, setComicSelected] = useState<ComicField[]>(settings.comic_fields || ['issue_number','publisher','edition','notes']);
  const [enabled, setEnabled] = useState(settings.records_enabled);
  const [defaultType, setDefaultType] = useState(settings.default_type);
  const [selected, setSelected] = useState<RecordField[]>(settings.record_fields);
  const [error, setError] = useState('');
  const [review, setReview] = useState(false);
  const [notice, setNotice] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  function start() { setStep(1); setComicsEnabled(!!settings.comics_enabled); setComicSelected(settings.comic_fields || types.comic.fields.filter(field=>field.suggested).map(field=>field.key as ComicField)); setEnabled(settings.records_enabled); setDefaultType(settings.default_type); setSelected(settings.status==='not_started' && settings.revision===0 ? fields.filter(field=>field.suggested).map(field=>field.key) : settings.record_fields); setError(''); setReview(false); setNotice(''); setOpen(true); }
  function next(value: number) { setStep(value); requestAnimationFrame(() => heading.current?.focus()); }
  async function commit(status: 'configured' | 'skipped') {
    if (locked || review) return;
    try {
      await runSave(async () => {
        setError(''); setNotice('Saving collection setup…');
        const result = await api<CollectionSettings>('collection-settings', jsonSave({status, records_enabled:status==='skipped' ? settings.records_enabled : enabled,
          default_type:status==='skipped' ? settings.default_type : defaultType==='record' && !enabled || defaultType==='comic' && !comicsEnabled ? 'other' : defaultType, comics_enabled:status==='skipped' ? !!settings.comics_enabled : comicsEnabled, comic_fields:status==='skipped' ? settings.comic_fields || ['issue_number','publisher','edition','notes'] : comicSelected, record_fields:status==='skipped' ? settings.record_fields : selected, expected_revision:settings.revision}));
        saved(result); setOpen(false); setNotice(status==='skipped' ? 'Setup skipped. You can set it up anytime.' : 'Collection setup saved. Only a title is required when adding a find.');
      });
    } catch (problem) { setNotice(''); setError(errorText(problem)); setReview(problem instanceof ApiError && (problem.uncertain || problem.status===409)); }
  }
  function submit(event: FormEvent) { event.preventDefault(); if(step===1) next(enabled || comicsEnabled ? 2 : 3); else if(step===2) next(3); else void commit('configured'); }
  return <section className="collection-setup" aria-label="Collection setup">
    {!open ? <><button className="quiet" disabled={locked} onClick={start}>{settings.status==='not_started' ? 'Set up your collection' : 'Collection settings'}</button>
      {settings.status==='not_started' && <button className="text-button" disabled={locked || review} onClick={() => void commit('skipped')}>Skip for now</button>}</> : <>
      <h2 ref={heading} tabIndex={-1}>Collection setup · Step {step} of 3</h2>
      <form onSubmit={submit} aria-label="Set up collection"><fieldset disabled={locked || review}>
        {step===1 && <><h3>What do you collect?</h3><p>Albums and Comics have tailored fields today. Use Other for anything else.</p>
          <label><input type="checkbox" checked={enabled} onChange={event => { setEnabled(event.target.checked); if(event.target.checked && defaultType==='other')setDefaultType('record');else if(!event.target.checked && defaultType==='record')setDefaultType('other'); }} /> {types.record.plural_label}</label>
          <label><input type="checkbox" checked={comicsEnabled} onChange={event=>{setComicsEnabled(event.target.checked);if(event.target.checked && defaultType==='other')setDefaultType('comic');else if(!event.target.checked && defaultType==='comic')setDefaultType('other');}} /> {types.comic.plural_label}</label>
          <p className="hint">Other is always available. Existing finds keep their type and details.</p>
          {(enabled || comicsEnabled) && <><label htmlFor="default-type">Start new finds as</label><select id="default-type" value={defaultType} onChange={event => setDefaultType(event.target.value as CollectionTypeId)}>{Object.values(types).filter(type=>type.id==='other' || type.id==='record' && enabled || type.id==='comic' && comicsEnabled).map(type=><option key={type.id} value={type.id}>{type.label}</option>)}</select></>}
        </>}
        {step===2 && <>{enabled && <><h3>What matters to you about your {types.record.plural_label.toLowerCase()}?</h3><p>Choose the fields you want to see. All of them are optional when adding an album.</p>
          <p>{types.record.title.label} is always shown.</p>{fields.map(field => <label key={field.key}><input type="checkbox" checked={selected.includes(field.key)} onChange={event => setSelected(before => event.target.checked ? [...before,field.key] : before.filter(key => key!==field.key))} /> {field.label}</label>)}
          </>}
          {comicsEnabled && <><h3>What matters to you about your comics?</h3><p>{types.comic.title.label} is always shown. Other fields are optional.</p>
            {types.comic.fields.map(field=><label key={field.key}><input type="checkbox" checked={comicSelected.includes(field.key as ComicField)} onChange={event=>setComicSelected(before=>event.target.checked ? [...before,field.key as ComicField] : before.filter(key=>key!==field.key))} /> {field.label}</label>)}
          </>}
          <p className="hint">These are suggested fields you can adjust. Hiding a field never deletes saved values. Photos and storage remain available after saving.</p>
        </>}
        {step===3 && <><h3>Preview your entry form</h3><p>This example is not added to your collection.</p><div className="setup-preview">
          {Object.values(types).filter(type=>type.id==='other' ? !enabled && !comicsEnabled : type.id==='record' ? enabled : comicsEnabled).map(type=><section key={type.id} aria-label={`${type.label} preview`}><h4>{type.label}</h4>{type.entry_order.map(key=>{
            if(key==='title')return <p key={key}><strong>{type.title.label}:</strong> {type.id==='comic' ? 'Example series' : 'Example album'}</p>;
            const field=type.fields.find(field=>field.key===key);
            const chosen=type.id==='comic' ? comicSelected : selected;
            return field && (type.id==='other' || chosen.includes(key as never)) ? <p key={key}>{field.label} (optional)</p> : null;
          })}</section>)}
          </div><p>New finds start as {types[defaultType].label}. You can change these choices later in Collection settings.</p></>}
        <div className="setup-actions">{step>1 && <button type="button" onClick={()=>next(step===3 && !enabled && !comicsEnabled ? 1 : step-1)}>Back</button>}<button className="primary" type="submit">{step===3 ? 'Save setup' : 'Continue'}</button><button type="button" className="quiet" onClick={()=>setOpen(false)}>Cancel setup</button></div>
      </fieldset></form>
    </>}
    {error && <p role="alert" className="error">{error} <button type="button" disabled={locked} onClick={()=>{setOpen(false);setError('');setReview(false);reload();}}>Reload settings</button></p>}
    <p role="status" className="notice">{notice}</p>
  </section>;
}
