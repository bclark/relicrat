'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, copyName, errorText, jsonSave, type InventoryCopy, type Location, type Photo, type Movement, type RunSave } from '../lib/inventory-client';

import Identification from './identification';
import CopyDetailsForm from './copy-details-form';

type Props = { copyId: string; runSave: RunSave; busy: boolean; blocked: boolean; changed: () => void };
const mergeLocations = (before: Location[], after: Location[]) => [...new Map([...before, ...after].map(item => [item.id, item])).values()];

export default function CopyDetail({ copyId, runSave, busy, blocked, changed }: Props) {
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
        setLocations(before => mergeLocations(before, [place])); setName('');
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
  const locked = busy || blocked || review || loading || readBusy || !copy;
  return <section className="copy-record" aria-labelledby="record-title">
    <div className="section-heading"><h2 ref={heading} tabIndex={-1} id="record-title">{copy ? copyName(copy) : 'Copy record'}</h2><button className="quiet" disabled={busy || loading || readBusy} onClick={() => { setLoading(true); setNotice(''); setVersion(value => value + 1); }}>Reload copy</button></div>
    {error && <p className="error" role="alert">{error}</p>}
    {review && <p className="hint">No save will be retried automatically. Reload and inspect this record before saving again.</p>}
    <p className="notice" role="status">{notice}</p>
    {loading ? <p role="status">Loading copy, photos, and storage…</p> : !copy ? <p>Reload this copy to try again, or open another copy.</p> : <>
      <div className="record-state"><span>Saved copy</span><span>{locationName(copy.storage_location_id)}</span></div>
      {copy.description && <p className="copy-notes">{copy.description}</p>}
      <CopyDetailsForm copy={copy} runSave={runSave} locked={locked} saved={record => { setCopy(record); changed(); }} failed={failed} />
      <h3>Photos</h3>
      {photos.length ? <div className="photos">{photos.map((photo, index) => <a key={photo.id} href={`/api/v1/inventory/${copyId}/photos/${photo.id}`} target="_blank" rel="noreferrer"><img src={`/api/v1/inventory/${copyId}/photos/${photo.id}`} alt={`Photo ${index + 1} of ${copyName(copy)}`} loading="lazy" /><span>View photo {index + 1}</span></a>)}</div> : <p className="hint">No photos yet. Add a clear view of this physical copy.</p>}
      <form onSubmit={upload} aria-label="Add photo"><fieldset disabled={locked}><label htmlFor="photo">Photo file</label><input ref={photoInput} id="photo" type="file" accept="image/jpeg,image/png,image/webp" onChange={e => setFile(e.target.files?.[0] || null)} aria-describedby="photo-help" /><p className="hint" id="photo-help">JPEG, PNG, or WebP. Up to 15 MiB. Photos save separately from the copy.</p><button disabled={!file} type="submit">Upload photo</button></fieldset></form>
      <h3>Storage</h3>
      <fieldset disabled={locked} aria-label="Assign storage"><label htmlFor="copy-location">Location</label><select id="copy-location" value={copy.storage_location_id || ''} onChange={e => { void assign(e.target.value); }} aria-describedby="storage-help"><option value="">Unassigned</option>{locations.map(location => <option key={location.id} value={location.id}>{optionLabel(location)}</option>)}</select></fieldset>
      <p className="hint" id="storage-help">Choosing a location saves it immediately.</p>
      <p className="notice" role="status">{storageNotice}</p>
      <p className="hint">{locations.length} locations loaded.{moreLocations ? ' More may be available.' : ''}</p>
      {moreLocations && <button className="quiet" disabled={busy || readBusy || loading} onClick={() => loadMore('locations')}>Load more locations</button>}
      <details className="new-location"><summary>Create a storage location</summary><form onSubmit={createLocation} aria-label="Create storage"><fieldset disabled={locked}><label htmlFor="location-name">Location name</label><input id="location-name" value={name} maxLength={250} required onChange={e => setName(e.target.value)} placeholder="e.g. Comic box A" /><label htmlFor="location-parent">Inside another location</label><select id="location-parent" value={parent} onChange={e => setParent(e.target.value)}><option value="">No parent location</option>{locations.map(location => <option key={location.id} value={location.id}>{optionLabel(location)}</option>)}</select><button type="submit">Create location</button></fieldset></form></details>
      <details className="movement-history"><summary>Movement history · {moves.length}{moreMoves ? '+' : ''} recorded</summary><p className="hint">Oldest first. Locations not loaded above are shown by their full reference.</p>{moves.length ? <ol>{moves.map(move => <li key={move.id}><span>{locationName(move.before_location_id)} to {locationName(move.after_location_id)}</span><small>Revision {move.after_revision} · {new Date(move.created_at).toLocaleString()}</small></li>)}</ol> : <p>No movements recorded.</p>}{moreMoves && <button disabled={busy || readBusy || loading} onClick={() => loadMore('moves')}>Load more movements</button>}</details>
      <details className="new-location" onToggle={event => { if (event.currentTarget.open) setCatalogRequested(true); }}><summary>Advanced: catalog matching</summary>{catalogRequested && <Identification copy={copy} runSave={runSave} locked={locked} saved={record => { setCopy(record); changed(); }} failed={failed} />}</details>
      <details className="copy-meta"><summary>Record information</summary><dl><dt>Physical copy ID</dt><dd>{copy.id}</dd><dt>Added</dt><dd>{new Date(copy.created_at).toLocaleString()}</dd><dt>Ownership status</dt><dd>{copy.ownership_status}</dd><dt>Identification</dt><dd>{copy.identification_status}</dd>{copy.catalog_item_id && <><dt>Catalog reference</dt><dd>{copy.catalog_item_id}</dd></>}</dl><p className="hint">Manual identification keeps this physical copy and its provisional information. Catalog editing and automatic matching remain unavailable.</p></details>
    </>}
  </section>;
}
