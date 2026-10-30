'use client';

import { useRef, useState, type FormEvent } from 'react';
import { api, ApiError, errorText, jsonSave, type CollectionSettings, type RecordField, type RunSave } from '../lib/inventory-client';

const fields: { key: RecordField; label: string }[] = [{key:'artist',label:'Artist or band'}, {key:'format',label:'Format'}, {key:'edition',label:'Edition or pressing'}, {key:'notes',label:'Notes'}];
type Props = { settings: CollectionSettings; runSave: RunSave; locked: boolean; saved: (value: CollectionSettings) => void; reload: () => void };

export default function CollectionSetup({ settings, runSave, locked, saved, reload }: Props) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(1);
  const [enabled, setEnabled] = useState(settings.records_enabled);
  const [defaultType, setDefaultType] = useState(settings.default_type);
  const [selected, setSelected] = useState<RecordField[]>(settings.record_fields);
  const [error, setError] = useState('');
  const [review, setReview] = useState(false);
  const [notice, setNotice] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  function start() { setStep(1); setEnabled(settings.records_enabled); setDefaultType(settings.default_type); setSelected(settings.record_fields); setError(''); setReview(false); setNotice(''); setOpen(true); }
  function next(value: number) { setStep(value); requestAnimationFrame(() => heading.current?.focus()); }
  async function commit(status: 'configured' | 'skipped') {
    if (locked || review) return;
    try {
      await runSave(async () => {
        setError(''); setNotice('Saving collection setup…');
        const result = await api<CollectionSettings>('collection-settings', jsonSave({status, records_enabled:status==='skipped' ? settings.records_enabled : enabled,
          default_type:status==='skipped' ? settings.default_type : enabled ? defaultType : 'other', record_fields:status==='skipped' ? settings.record_fields : selected, expected_revision:settings.revision}));
        saved(result); setOpen(false); setNotice(status==='skipped' ? 'Setup skipped. You can set it up anytime.' : 'Collection setup saved. Only a title is required when adding a find.');
      });
    } catch (problem) { setNotice(''); setError(errorText(problem)); setReview(problem instanceof ApiError && (problem.uncertain || problem.status===409)); }
  }
  function submit(event: FormEvent) { event.preventDefault(); if(step===1) next(enabled ? 2 : 3); else if(step===2) next(3); else void commit('configured'); }
  return <section className="collection-setup" aria-label="Collection setup">
    {!open ? <><button className="quiet" disabled={locked} onClick={start}>{settings.status==='not_started' ? 'Set up your collection' : 'Collection settings'}</button>
      {settings.status==='not_started' && <button className="text-button" disabled={locked || review} onClick={() => void commit('skipped')}>Skip for now</button>}</> : <>
      <h2 ref={heading} tabIndex={-1}>Collection setup · Step {step} of 3</h2>
      <form onSubmit={submit} aria-label="Set up collection"><fieldset disabled={locked || review}>
        {step===1 && <><h3>What do you collect?</h3><p>Records have tailored fields today. Use Other for anything else.</p>
          <label><input type="checkbox" checked={enabled} onChange={event => { setEnabled(event.target.checked); setDefaultType(event.target.checked ? 'record' : 'other'); }} /> Records</label>
          <p className="hint">Other is always available. Existing finds keep their type and details.</p>
          {enabled && <><label htmlFor="default-type">Start new finds as</label><select id="default-type" value={defaultType} onChange={event => setDefaultType(event.target.value as 'other'|'record')}><option value="record">Record</option><option value="other">Other</option></select></>}
        </>}
        {step===2 && <><h3>What matters to you about your records?</h3><p>Choose the fields you want to see. All of them are optional when adding a record.</p>
          <p>Album title is always shown.</p>{fields.map(field => <label key={field.key}><input type="checkbox" checked={selected.includes(field.key)} onChange={event => setSelected(before => event.target.checked ? [...before,field.key] : before.filter(key => key!==field.key))} /> {field.label}</label>)}
          <p className="hint">These are suggested fields you can adjust. Hiding a field never deletes saved values. Photos and storage remain available after saving.</p>
        </>}
        {step===3 && <><h3>Preview your entry form</h3><p>This example is not added to your collection.</p><div className="setup-preview">
          <p><strong>{enabled ? 'Album title' : 'Title'}:</strong> Example album</p>
          {enabled && fields.filter(field=>selected.includes(field.key)).map(field=><p key={field.key}>{field.label} (optional)</p>)}
          {!enabled && <p>Notes (optional)</p>}
          </div><p>New finds start as {enabled && defaultType==='record' ? 'Record' : 'Other'}. You can change these choices later in Collection settings.</p></>}
        <div className="setup-actions">{step>1 && <button type="button" onClick={()=>next(step===3 && !enabled ? 1 : step-1)}>Back</button>}<button className="primary" type="submit">{step===3 ? 'Save setup' : 'Continue'}</button><button type="button" className="quiet" onClick={()=>setOpen(false)}>Cancel setup</button></div>
      </fieldset></form>
    </>}
    {error && <p role="alert" className="error">{error} <button type="button" disabled={locked} onClick={()=>{setOpen(false);setError('');setReview(false);reload();}}>Reload settings</button></p>}
    <p role="status" className="notice">{notice}</p>
  </section>;
}
