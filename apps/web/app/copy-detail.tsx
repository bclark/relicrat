'use client';

import { useCallback, useEffect, useLayoutEffect, useRef, useState, Fragment, type FormEvent, type RefObject } from 'react';
import { api, ApiError, copyName, errorText, jsonSave, type InventoryCopy, type Location, type Photo, type Movement, type RecordField, type ComicField, type MovieField, type CollectionTypes, type RunSave } from '../lib/inventory-client';

import Identification from './identification';
import CopyDetailsForm from './copy-details-form';
import ChecklistMatch from './checklist-match';

type Props = { active?:boolean; guard?:RefObject<()=>boolean>; movieFields: MovieField[]; types: CollectionTypes | null; copyId: string; runSave: RunSave; busy: boolean; blocked: boolean; changed: () => void; recordFields: RecordField[]; comicFields: ComicField[] };
const mergeLocations = (before: Location[], after: Location[]) => [...new Map([...before, ...after].map(item => [item.id, item])).values()];

export default function CopyDetail({ types, copyId, runSave, busy, blocked, changed, recordFields, comicFields, movieFields, guard, active=true }: Props) {
  const [editing,setEditing]=useState(false);
  const [detailsDirty,setDetailsDirty]=useState(false);
  const [detailsReview,setDetailsReview]=useState(false);
  const [inspected,setInspected]=useState<InventoryCopy|null>(null);
  const [inspectionPhotos,setInspectionPhotos]=useState<Photo[]>([]);
  const detailsState=useRef({dirty:false,uncertain:false});
  const [catalogDirty,setCatalogDirty]=useState(false);
  const [checklistDirty,setChecklistDirty]=useState(false);
  const otherDirty=catalogDirty||checklistDirty;
  const detailsChanged=useCallback((dirty:boolean,uncertain:boolean)=>{detailsState.current={dirty,uncertain};setDetailsDirty(dirty);setDetailsReview(uncertain);},[]);
  const [copy, setCopy] = useState<InventoryCopy | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [locationOffset, setLocationOffset] = useState(0);
  const [moreLocations, setMoreLocations] = useState(false);
  const [moves, setMoves] = useState<Movement[]>([]);
  const [moreMoves, setMoreMoves] = useState(false);
  const [name, setName] = useState('');
  const [parent, setParent] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const photoInput = useRef<HTMLInputElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const [loading, setLoading] = useState(true);
  const [readBusy, setReadBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [storageNotice, setStorageNotice] = useState('');
  const [review, setReview] = useState(false);
  const [version, setVersion] = useState(0);
  const [catalogRequested, setCatalogRequested] = useState(false);
  const readLock = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    setEditing(false);setDetailsReview(false);setInspected(null);setCatalogDirty(false);setChecklistDirty(false);detailsState.current={dirty:false,uncertain:false};setName('');setParent('');
    setLoading(true); setError(''); setStorageNotice(''); setCopy(null); setFile(null);
    const options = { signal: controller.signal };
    Promise.all([
      api<InventoryCopy>(`inventory/${copyId}`, options),
      api<Photo[]>(`inventory/${copyId}/photos`, options),
      api<Location[]>('storage-locations?limit=100&offset=0', options),
      api<Movement[]>(`inventory/${copyId}/locations?limit=11&offset=0`, options),
    ]).then(async ([record, images, places, history]) => {
      const pageSize = places.length;
      if (record.storage_location_id && !places.some(location => location.id === record.storage_location_id)) {
        const current = await api<Location>(`storage-locations/${record.storage_location_id}`, options);
        places = [...places, current];
      }
      if (controller.signal.aborted) return;
      setCopy(record); setPhotos(images); setLocations(places);
      // Current-location lookup is not part of the first paginated page.
      setLocationOffset(pageSize);
      setMoreLocations(pageSize === 100);
      setMoves(history.slice(0, 10)); setMoreMoves(history.length > 10);
      setReview(false);
    }).catch(problem => { if (!controller.signal.aborted) setError(errorText(problem)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [copyId, version]);
  useEffect(() => { if (copy && !loading) heading.current?.focus(); }, [copy?.id, loading]);

  function canLeave(){
    if(busy||blocked||review||detailsState.current.uncertain){window.alert('A save needs review. Reload this copy and inspect the saved record before opening another item.');return false;}
    return !(detailsState.current.dirty||otherDirty||file||name||parent)||window.confirm('Discard the unsaved changes to this copy and open another item?');
  }
  useLayoutEffect(()=>{if(guard)guard.current=canLeave;return()=>{if(guard)guard.current=()=>true;};});
  useEffect(()=>{function warn(e:BeforeUnloadEvent){if(detailsState.current.dirty||detailsState.current.uncertain||otherDirty||file||name||parent){e.preventDefault();e.returnValue='';}}window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[otherDirty,file,name,parent]);
  function failed(problem: unknown) {
    if (problem instanceof ApiError && (problem.uncertain || problem.status === 409)) setReview(true);
    setError(problem instanceof ApiError && problem.status === 409
      ? 'This copy changed elsewhere. Reload the copy and review its saved details before saving again.'
      : errorText(problem));
  }
  function locationName(id: string | null) {
    if (!id) return 'Unassigned';
    const found = locations.find(location => location.id === id);
    return found?.name || `Location ${id}`;
  }
  function optionLabel(location: Location) {
    const parentName = location.parent_id ? locations.find(item => item.id === location.parent_id)?.name : null;
    return `${parentName ? `${parentName} / ` : ''}${location.name} · ${location.id.slice(0, 8)}`;
  }
  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file || review || blocked) return;
    if (!file.size || file.size > 15 * 1024 * 1024) { setError('Choose a photo between 1 byte and 15 MiB.'); return; }
    try {
      await runSave(async () => {
        setError(''); setNotice('');
        const form = new FormData(); form.set('file', file);
        const photo = await api<Photo>(`inventory/${copyId}/photos`, { method: 'POST', body: form });
        setPhotos(before => [photo, ...before]); setFile(null);
        if (photoInput.current) photoInput.current.value = '';
        setNotice('Photo saved. The copy and its existing history are unchanged.');
      });
    } catch (problem) { failed(problem); }
  }
  async function assign(locationId: string) {
    if (!copy || locked || locationId === (copy.storage_location_id || '')) return;
    try {
      await runSave(async () => {
        setError(''); setNotice(''); setStorageNotice('Saving location…');
        const record = await api<InventoryCopy>(`inventory/${copyId}/location`, jsonSave({ storage_location_id: locationId || null, expected_storage_revision: copy.storage_revision }));
        setCopy(record); changed();
        setStorageNotice(record.storage_location_id ? `Added to ${locationName(record.storage_location_id)}.` : 'Copy is now unassigned.');
        // A follow-up read failure does not turn a confirmed save into a retry.
        try {
          const history = await api<Movement[]>(`inventory/${copyId}/locations?limit=11&offset=0`);
          setMoves(history.slice(0, 10)); setMoreMoves(history.length > 10);
        } catch { setError('Location was saved, but history could not be refreshed. Reload the copy to view it.'); }
      });
    } catch (problem) { setStorageNotice(''); failed(problem); }
  }
  async function createLocation(event: FormEvent) {
    event.preventDefault(); if (!name.trim() || review || blocked) return;
    try {
      await runSave(async () => {
        setError(''); setNotice('');
        const place = await api<Location>('storage-locations', jsonSave({ name: name.trim(), parent_id: parent || null }));
        setLocations(before => mergeLocations(before, [place])); setName(''); setParent('');
        setNotice(`${place.name} created. Choose it under Location to move this copy there.`);
      });
    } catch (problem) { failed(problem); }
  }
  async function loadMore(kind: 'locations' | 'moves') {
    if (readLock.current) return;
    readLock.current = true; setReadBusy(true); setError('');
    try {
      if (kind === 'locations') {
        const result = await api<Location[]>(`storage-locations?limit=100&offset=${locationOffset}`);
        setLocations(before => mergeLocations(before, result)); setLocationOffset(before => before + result.length); setMoreLocations(result.length === 100);
      } else {
        const result = await api<Movement[]>(`inventory/${copyId}/locations?limit=11&offset=${moves.length}`);
        setMoves(before => [...before, ...result.slice(0, 10)]); setMoreMoves(result.length > 10);
      }
    } catch (problem) { setError(errorText(problem)); }
    finally { readLock.current = false; setReadBusy(false); }
  }
  function reloadCopy(){if((detailsState.current.dirty||detailsState.current.uncertain||otherDirty||file||name||parent)&&!window.confirm('Reload the saved copy and discard its local draft?'))return;setLoading(true);setNotice('');setVersion(value=>value+1);}
  const locked = busy || blocked || review || loading || readBusy || !copy;
  return <section className={`copy-record${editing?' editing':''}`} aria-labelledby="record-title" onChangeCapture={event=>{const target=event.target as HTMLElement;if(target.closest('.identification'))setCatalogDirty(true);else if(target.closest('[aria-label="Review checklist match"]'))setChecklistDirty(true);}}>
    <div className="detail-trail">{editing&&<button type="button" className="text-button" disabled={busy} onClick={()=>{setEditing(false);requestAnimationFrame(()=>document.getElementById('copy-edit')?.focus());}}>Back to item</button>}{detailsReview?<span role="status">Save needs review</span>:detailsDirty?<span>{editing?'Unsaved changes':'Draft retained'}</span>:null}</div><div className="section-heading"><h2 ref={heading} tabIndex={-1} id="record-title">{editing?'Edit details':copy ? copy.title||copyName(copy) : 'Copy record'}</h2><button className="quiet" disabled={busy || loading || readBusy} hidden={!review&&!error} onClick={reloadCopy}>Reload copy</button></div>
    {error && <p className="error" role="alert">{error}</p>}
    {review && <section className="save-inspection" aria-label="Save recovery"><p>No save will be retried automatically. Inspect the saved record before deciding whether to discard your preserved draft.</p><button type="button" disabled={busy||readBusy} onClick={async()=>{setReadBusy(true);try{const [record,images]=await Promise.all([api<InventoryCopy>(`inventory/${copyId}`),api<Photo[]>(`inventory/${copyId}/photos`)]);setInspected(record);setInspectionPhotos(images);}catch(problem){setError(errorText(problem));}finally{setReadBusy(false);}}}>Inspect saved details</button>{inspected&&<><h3>Saved record — separate from your draft</h3><dl className="copy-summary"><dt>Title</dt><dd>{copyName(inspected)}</dd><dt>Collection</dt><dd>{inspected.custom_collection_name||types?.[inspected.collection_type]?.label||inspected.collection_type}</dd><dt>Barcode</dt><dd>{inspected.barcode?.value?`${inspected.barcode.value} · ${inspected.barcode.format}${inspected.barcode.supplement?` · ${inspected.barcode.supplement}`:''}`:'Not entered'}</dd><dt>Edition</dt><dd>{inspected.edition_label||'Not entered'}</dd>{Object.entries({...inspected.record_details,...inspected.comic_details,...inspected.movie_details,...inspected.custom_details}).map(([key,value])=><Fragment key={key}><dt>{types&&Object.values(types).flatMap(t=>t.fields).find(f=>f.key===key)?.label||key.replaceAll('_',' ')}</dt><dd>{value===null?'Not recorded':Array.isArray(value)?value.join(', ')||'None selected':typeof value==='boolean'?(value?'Yes':'No'):value||'Not entered'}</dd></Fragment>)}</dl><p>Saved catalog covers: {inspectionPhotos.filter(photo=>photo.role==='catalog_cover').length}</p>{inspectionPhotos.filter(photo=>photo.role==='catalog_cover').map(photo=><figure key={photo.id} className="inspector-cover"><img src={`/api/v1/inventory/${copyId}/photos/${photo.id}`} alt="Saved catalog artwork"/><figcaption>Catalog artwork, not a photo of your copy.</figcaption></figure>)}<p className="hint">Your draft is still preserved. Use Reload copy above only after inspection; it replaces the local draft with the saved record.</p></>}</section>}
    <p className="notice" role="status">{notice}</p>
    {loading ? <p role="status">Loading copy, photos, and storage…</p> : !copy ? <p>Reload this copy to try again, or open another copy.</p> : <>
      <p className="detail-context">{copy.custom_collection_name||types?.[copy.collection_type]?.plural_label||copy.collection_type}{editing?` · ${copyName(copy)}`:''}</p><div hidden={editing} className="item-reading"><p className="copy-subtitle">{[copy.record_details.artist,copy.record_details.format,copy.movie_details?.media_format,copy.movie_details?.studio,copy.comic_details?.publisher,copy.edition_label].filter(Boolean).join(' · ')}</p>

      {photos.find(photo=>photo.role==='catalog_cover')&&<figure className="inspector-cover"><img src={`/api/v1/inventory/${copyId}/photos/${photos.find(photo=>photo.role==='catalog_cover')!.id}`} alt={`Catalog cover for ${copyName(copy)}`} /><figcaption>Catalog artwork, not a photo of your copy.</figcaption></figure>}
      {!editing&&<button className="primary" type="button" id="copy-edit" disabled={locked} onClick={()=>{setNotice('');setEditing(true);requestAnimationFrame(()=>(document.querySelector('.copy-details-form form input') as HTMLInputElement|null)?.focus());}}>{detailsDirty?'Continue editing':'Edit details'}</button>}
      </div>{!editing&&copy.custom_collection_id&&<ChecklistMatch key={copy.id} collectionId={copy.custom_collection_id} copyId={copy.id} locked={locked} runSave={runSave} changed={()=>{setChecklistDirty(false);changed();}} />}
      <CopyDetailsForm active={active} editing={editing} cancel={()=>{setEditing(false);requestAnimationFrame(()=>document.getElementById('copy-edit')?.focus());}} stateChanged={detailsChanged} types={types} fields={recordFields} movieFields={movieFields} comicFields={comicFields} copy={copy} runSave={runSave} locked={locked} saved={(record,artwork) => { setCopy(record);setEditing(false);detailsState.current={dirty:false,uncertain:false};setDetailsReview(false);setInspected(null);setNotice('Changes saved.');requestAnimationFrame(()=>document.getElementById('copy-edit')?.focus()); changed(); if(artwork)void api<Photo[]>(`inventory/${copyId}/photos`).then(setPhotos).catch(()=>setError('Details saved, but artwork could not reload. Reload this copy.')); }} failed={failed} />
      <div className="copy-operations" hidden={editing}>{photos.some(photo=>photo.role==='catalog_cover')&&<details aria-label="Catalog artwork"><summary>Artwork source</summary><p className="hint">Imported artwork, not photographs of your physical copy.</p><div className="photos catalog-sources">{photos.filter(photo=>photo.role==='catalog_cover').map(photo=><div key={photo.id}><a href={`/api/v1/inventory/${copyId}/photos/${photo.id}`} target="_blank" rel="noreferrer"><img src={`/api/v1/inventory/${copyId}/photos/${photo.id}`} alt={`Catalog cover for ${copyName(copy)}`} loading="lazy"/></a><p>{photo.source_url&&<a href={photo.source_url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">Source: {photo.source_provider}</a>}</p></div>)}</div></details>}
      <section className="item-section"><h3>Photos of your copy</h3><details className="copy-photos"><summary>Add or view photos</summary>
      {photos.some(photo=>photo.role!=='catalog_cover') ? <div className="photos">{photos.filter(photo=>photo.role!=='catalog_cover').map((photo, index) => <a key={photo.id} href={`/api/v1/inventory/${copyId}/photos/${photo.id}`} target="_blank" rel="noreferrer"><img src={`/api/v1/inventory/${copyId}/photos/${photo.id}`} alt={`Photo ${index + 1} of ${copyName(copy)}`} loading="lazy" /><span>View photo {index + 1}</span></a>)}</div> : <p className="hint">No photos yet. Add a clear view of this physical copy.</p>}
      <form onSubmit={upload} aria-label="Add photo"><fieldset disabled={locked}><label htmlFor="photo">Photo file</label><input ref={photoInput} id="photo" type="file" accept="image/jpeg,image/png,image/webp" onChange={e => setFile(e.target.files?.[0] || null)} aria-describedby="photo-help" /><p className="hint" id="photo-help">JPEG, PNG, or WebP. Up to 15 MiB. Photos save separately from the copy.</p><button disabled={!file} type="submit">Upload photo</button></fieldset></form>
      </details></section><section className="item-section"><h3>Storage</h3><p className="saved-location">{locationName(copy.storage_location_id)}</p><details className="storage-editor"><summary>Change storage</summary>
      <fieldset disabled={locked||detailsDirty} aria-label="Assign storage"><label htmlFor="copy-location">Location</label><select id="copy-location" value={copy.storage_location_id || ''} onChange={e => { void assign(e.target.value); }} aria-describedby="storage-help"><option value="">Unassigned</option>{locations.map(location => <option key={location.id} value={location.id}>{optionLabel(location)}</option>)}</select></fieldset>
      <p className="hint" id="storage-help">Choosing a location saves it immediately.</p>
      <p className="notice" role="status">{storageNotice}</p>
      <p className="hint">{locations.length} locations loaded.{moreLocations ? ' More may be available.' : ''}</p>
      {moreLocations && <button className="quiet" disabled={busy || readBusy || loading} onClick={() => loadMore('locations')}>Load more locations</button>}
      <details className="new-location"><summary>Create a storage location</summary><form onSubmit={createLocation} aria-label="Create storage"><fieldset disabled={locked}><label htmlFor="location-name">Location name</label><input id="location-name" value={name} maxLength={250} required onChange={e => setName(e.target.value)} placeholder="e.g. Comic box A" /><label htmlFor="location-parent">Inside another location</label><select id="location-parent" value={parent} onChange={e => setParent(e.target.value)}><option value="">No parent location</option>{locations.map(location => <option key={location.id} value={location.id}>{optionLabel(location)}</option>)}</select><button type="submit">Create location</button></fieldset></form></details>
      </details></section>{copy.description&&<section className="item-section"><h3>Notes</h3><p className="copy-notes">{copy.description}</p><p className="hint">Notes are read-only.</p></section>}<details className="movement-history"><summary>Movement history · {moves.length}{moreMoves ? '+' : ''} recorded</summary><p className="hint">Oldest first. Locations not loaded above are shown by their full reference.</p>{moves.length ? <ol>{moves.map(move => <li key={move.id}><span>{locationName(move.before_location_id)} to {locationName(move.after_location_id)}</span><small>Revision {move.after_revision} · {new Date(move.created_at).toLocaleString()}</small></li>)}</ol> : <p>No movements recorded.</p>}{moreMoves && <button disabled={busy || readBusy || loading} onClick={() => loadMore('moves')}>Load more movements</button>}</details>
      <details className="new-location" onToggle={event => { if (event.currentTarget.open) setCatalogRequested(true); }}><summary>Advanced: catalog matching</summary>{catalogRequested && <Identification copy={copy} runSave={runSave} locked={locked||detailsDirty} saved={record => {setCatalogDirty(false);setCopy(record);changed();}} failed={failed} />}</details>
      <details className="copy-meta"><summary>Record information</summary><dl><dt>Physical copy ID</dt><dd>{copy.id}</dd><dt>Added</dt><dd>{new Date(copy.created_at).toLocaleString()}</dd><dt>Ownership status</dt><dd>{copy.ownership_status}</dd><dt>Identification</dt><dd>{copy.identification_status}</dd>{copy.catalog_item_id && <><dt>Catalog reference</dt><dd>{copy.catalog_item_id}</dd></>}</dl>{!review&&!error&&<button type="button" disabled={busy||loading||readBusy} onClick={reloadCopy}>Reload copy</button>}<p className="hint">Manual identification keeps this physical copy and its provisional information. Catalog editing and automatic matching remain unavailable.</p></details>
      </div>
    </>}
  </section>;
}
