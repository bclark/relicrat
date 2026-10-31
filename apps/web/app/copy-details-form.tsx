'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError, errorText, jsonSave, type InventoryCopy, type RecordField, type CollectionTypes, type RunSave } from '../lib/inventory-client';
import { Pages, usePage } from './identification';

type Props = { types: CollectionTypes | null; fields: RecordField[]; copy: InventoryCopy; runSave: RunSave; locked: boolean; saved: (copy: InventoryCopy) => void; failed: (error: unknown) => void };
type Edit = { id: string; before_title: string | null; after_title: string | null; before_edition_label: string | null; after_edition_label: string | null; before_collection_type: string | null; after_collection_type: string | null; before_record_details: {artist?:string;format?:string}|null; after_record_details: {artist?:string;format?:string}|null; after_revision: number; created_at: string };

export default function CopyDetailsForm({ types, fields, copy, runSave, locked, saved, failed }: Props) {
  const [recordType, setRecordType] = useState(copy.collection_type);
  const [artist, setArtist] = useState(copy.record_details.artist || '');
  const [format, setFormat] = useState(copy.record_details.format || '');
  const [title, setTitle] = useState(copy.title || '');
  const [edition, setEdition] = useState('');
  const [initialEdition, setInitialEdition] = useState('');
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [needsReview, setNeedsReview] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [page, setPage] = useState(0);
  const history = usePage<Edit>(historyOpen ? `inventory/${copy.id}/detail-history` : null, page, String(copy.details_revision));

  useEffect(() => {
    const controller = new AbortController();
    setReady(false); setError(''); setNeedsReview(false); setTitle(copy.title || ''); setRecordType(copy.collection_type); setArtist(copy.record_details.artist || ''); setFormat(copy.record_details.format || '');
    const load = copy.edition_label === null && copy.catalog_item_id && copy.release_id
      ? api<{ name: string | null }>(`catalog/items/${copy.catalog_item_id}/releases/${copy.release_id}`, { signal: controller.signal }).then(release => release.name || '')
      : Promise.resolve(copy.edition_label || '');
    load.then(value => {
      if (!controller.signal.aborted) { setEdition(value); setInitialEdition(value); setReady(true); }
    }).catch(problem => { if (!controller.signal.aborted) setError(errorText(problem)); });
    return () => controller.abort();
  }, [copy.id, copy.title, copy.edition_label, copy.details_revision, copy.catalog_item_id, copy.release_id, copy.identification_revision, copy.collection_type, copy.record_details.artist, copy.record_details.format, refresh]);

  async function submit(event: FormEvent) {
    event.preventDefault(); if (locked || !ready) return;
    try {
      await runSave(async () => {
        setError(''); setNotice('Saving copy details…');
        // An unchanged matched edition keeps following the existing catalog link.
        // A changed label is an explicit personal description, including blank.
        const label = edition.trim() === initialEdition ? copy.edition_label : edition.trim();
        const result = await api<InventoryCopy>(`inventory/${copy.id}/details`, jsonSave({ title: title.trim() || null, edition_label: label, collection_type: recordType, record_details:{artist:artist.trim() || null,format:format.trim() || null},
          expected_details_revision: copy.details_revision, expected_identification_revision: copy.identification_revision }));
        saved(result); setNotice('Copy details saved.');
      });
    } catch (problem) { setNotice(''); setNeedsReview(problem instanceof ApiError && (problem.uncertain || problem.status === 409)); failed(problem); }
  }
  const dirty = title.trim() !== (copy.title || '') || edition.trim() !== initialEdition || recordType!==copy.collection_type || artist.trim()!==(copy.record_details.artist || '') || format.trim()!==(copy.record_details.format || '');
  return <div className="copy-details-form">
    <h3>Edit this copy</h3>
    <form aria-label="Edit copy details" onSubmit={submit}><fieldset disabled={locked || !ready}>
      <label htmlFor="copy-type">Collection type</label><select id="copy-type" value={recordType} onChange={event=>{setRecordType(event.target.value as 'other'|'record');setNotice('');}}>{types ? Object.values(types).map(type=><option key={type.id} value={type.id}>{type.label}</option>) : <option value={recordType}>{recordType}</option>}</select>
      {recordType!==copy.collection_type && <p className="hint">Changing type keeps this physical copy and its saved details. Save details to apply it.</p>}
      <label htmlFor="copy-title">{types?.[recordType].title.label || 'Title'}</label><input id="copy-title" maxLength={types?.[recordType].title.max_length || 500} value={title} onChange={event => { setTitle(event.target.value); setNotice(''); }} />
      {((recordType==='record' && fields.includes('artist')) || artist || copy.record_details.artist) && <><label htmlFor="copy-artist">{types?.record.fields.find(field=>field.key==='artist')?.label || 'artist'} (optional)</label><input id="copy-artist" maxLength={types?.record.fields.find(field=>field.key==='artist')?.max_length || 500} value={artist} onChange={event=>{setArtist(event.target.value);setNotice('');}} /></>}
      {((recordType==='record' && fields.includes('format')) || format || copy.record_details.format) && <><label htmlFor="copy-format">{types?.record.fields.find(field=>field.key==='format')?.label || 'format'} (optional)</label><input id="copy-format" maxLength={types?.record.fields.find(field=>field.key==='format')?.max_length || 100} value={format} onChange={event=>{setFormat(event.target.value);setNotice('');}} /></>}
      {recordType==='record' && <p className="hint">Saved record details stay editable even when hidden from new entry forms.</p>}
      {(recordType!=='record' || fields.includes('edition') || edition || copy.edition_label!==null || copy.release_id) && <><label htmlFor="copy-edition">Edition</label><input id="copy-edition" maxLength={500} value={edition} onChange={event => { setEdition(event.target.value); setNotice(''); }} aria-describedby="copy-edition-help" />
      <p className="hint" id="copy-edition-help">Optional. For example, Blue vinyl or First printing.</p></>}
      {copy.edition_label !== null && copy.release_id && <p className="hint">Your edition label is used for this copy. Shared catalog information is under Advanced.</p>}
      <button className="primary" type="submit" disabled={!dirty}>Save details</button>
    </fieldset></form>
    {!ready && !error && <p role="status">Loading saved edition…</p>}
    {error && <p className="error" role="alert">{error} <button type="button" className="quiet" disabled={locked} onClick={() => setRefresh(value => value + 1)}>Reload edition</button></p>}
    {dirty && ready && !needsReview && <p className="hint">Unsaved changes to this copy.</p>}
    <p className="notice" role="status">{notice}</p>
    <details className="movement-history" onToggle={event => setHistoryOpen(event.currentTarget.open)}><summary>Copy edit history</summary>
      <p className="hint">Oldest first. Earlier titles and edition labels are kept.</p>
      {history.busy ? <p role="status">Loading copy edit history…</p> : history.error ? <p role="alert" className="error">{history.error} Use Reload copy.</p> : history.items.length ? <ol>{history.items.map(edit => <li key={edit.id}>
        <span>{edit.before_title || 'No title'} to {edit.after_title || 'No title'}</span>
        {edit.before_edition_label !== edit.after_edition_label && <small>Edition label: {edit.before_edition_label || 'Not entered'} to {edit.after_edition_label || 'Not entered'}</small>}
        {edit.before_collection_type!==edit.after_collection_type && <small>Type: {edit.before_collection_type || 'Other'} to {edit.after_collection_type || 'Other'}</small>}
        {(['artist','format'] as const).filter(key=>edit.before_record_details?.[key]!==edit.after_record_details?.[key]).map(key=><small key={key}>{key==='artist' ? 'Artist' : 'Format'}: {edit.before_record_details?.[key] || 'Not entered'} to {edit.after_record_details?.[key] || 'Not entered'}</small>)}
        <small>Revision {edit.after_revision} · {new Date(edit.created_at).toLocaleString()}</small>
      </li>)}</ol> : <p>No copy edits recorded.</p>}
      <Pages label="Copy edit history pages" page={page} more={history.more} disabled={locked || history.busy} select={setPage} />
    </details>
  </div>;
}
