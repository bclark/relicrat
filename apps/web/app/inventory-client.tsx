'use client';

import ObservationInput from './observation-input';
import SignOut from './sign-out';
import CollectionSetup from './collection-setup';

import { Fragment, useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, copyName, errorText, jsonSave, type CollectionSettings, type CollectionTypeId, type CollectionTypes, type InventoryCopy, type RunSave } from '../lib/inventory-client';
import CopyDetail from './copy-detail';

const PAGE = 20;
export default function InventoryClient() {
  const [entryVersion, setEntryVersion] = useState(0);
  const [title, setTitle] = useState('');
  const [settings, setSettings] = useState<CollectionSettings | null>(null);
  const [types, setTypes] = useState<CollectionTypes | null>(null);
  const [settingsError, setSettingsError] = useState('');
  const [settingsVersion, setSettingsVersion] = useState(0);
  const [genericEntry, setGenericEntry] = useState(false);
  const [collectionType, setCollectionType] = useState<CollectionTypeId>('other');
  const [issueNumber, setIssueNumber] = useState('');
  const [publisher, setPublisher] = useState('');
  const [artist, setArtist] = useState('');
  const [format, setFormat] = useState('');
  const [edition, setEdition] = useState('');
  const draftTouched = useRef(false);
  const record = collectionType==='record';
  const showField = (key:string,value:string) => collectionType==='other' || !!value || (collectionType==='comic' ? settings?.comic_fields : settings?.record_fields)?.includes(key as never);
  useEffect(() => {
    const controller = new AbortController(); setSettingsError('');
    Promise.all([api<CollectionSettings>('collection-settings', {signal:controller.signal}), api<CollectionTypes>('collection-settings/types', {signal:controller.signal})]).then(([value, definitions])=>{
      if(controller.signal.aborted) return;
      setTypes(definitions);
      setSettings(value); if(!draftTouched.current) setCollectionType(value.default_type);
    }).catch(problem=>{if(!controller.signal.aborted) setSettingsError(errorText(problem));});
    return ()=>controller.abort();
  },[settingsVersion]);
  function changeType(value: CollectionTypeId) {
    if(value===collectionType) return;
    if((title || notes || artist || format || edition || issueNumber || publisher) && !window.confirm('Changing type will discard this unsaved find. Change type?')) return;
    setCollectionType(value);setIssueNumber('');setPublisher('');setTitle('');setNotes('');setArtist('');setFormat('');setEdition('');setSaveError('');draftTouched.current=true;
  }
  const [notes, setNotes] = useState('');
  const [saveError, setSaveError] = useState('');
  const [notice, setNotice] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const [busy, setBusy] = useState(false);
  const saveLock = useRef(false);
  const titleInput = useRef<HTMLInputElement>(null);
  const [typeFilter, setTypeFilter] = useState<CollectionTypeId | ''>('');
  const [draftQuery, setDraftQuery] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [items, setItems] = useState<InventoryCopy[]>([]);
  const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const reviewReload = useRef(false);
  const runSave: RunSave = useCallback(async function<T>(action: () => Promise<T>) {
    if (saveLock.current) return;
    saveLock.current = true;
    setBusy(true);
    try { return await action(); }
    finally { saveLock.current = false; setBusy(false); }
  }, []);
  const changed = useCallback(() => setRefresh(value => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setListError('');
    api<InventoryCopy[]>(`inventory?limit=${PAGE + 1}&offset=${page * PAGE}&q=${encodeURIComponent(query)}${typeFilter ? `&collection_type=${encodeURIComponent(typeFilter)}` : ''}`, { signal: controller.signal })
      .then(result => {
        if (controller.signal.aborted) return;
        setItems(result.slice(0, PAGE)); setMore(result.length > PAGE);
        if (reviewReload.current) { setUncertain(false); reviewReload.current = false; }
      })
      .catch(error => { if (!controller.signal.aborted) setListError(errorText(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query, page, refresh, typeFilter]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (uncertain || (!settings && !genericEntry)) return;
    if (!title.trim()) {
      setSaveError('Add a title so you can recognize this copy later.'); titleInput.current?.focus(); return;
    }
    try {
      await runSave(async () => {
        setSaveError(''); setNotice('');
        const copy = await api<InventoryCopy>('inventory', jsonSave({ title: title.trim(), description: notes.trim() || null, collection_type: collectionType, record_details: record ? {artist:artist.trim() || null,format:format.trim() || null} : {}, comic_details:collectionType==='comic' ? {issue_number:issueNumber.trim() || null,publisher:publisher.trim() || null} : {}, edition_label: edition.trim() || null }));
        setEntryVersion(value=>value+1);setIssueNumber('');setPublisher(''); setTitle(''); setNotes(''); setArtist('');setFormat('');setEdition('');draftTouched.current=false; setSelected(copy.id);
        setDraftQuery(''); setQuery(''); setPage(0); changed();
        setNotice(typeFilter && typeFilter!==copy.collection_type ? 'Copy saved. Choose All types to see it in the list.' : 'Copy saved. You can add more details whenever you like.');
      });
    } catch (error) {
      setSaveError(errorText(error));
      if (error instanceof ApiError && error.uncertain) setUncertain(true);
    }
  }
  function reloadInventory() {
    reviewReload.current = true;
    if (uncertain) { setDraftQuery(''); setQuery(''); setPage(0); }
    changed();
  }
  function search(event: FormEvent) {
    event.preventDefault(); setQuery(draftQuery.trim()); setPage(0); changed();
  }
  return (
    <>
      <a className="skip-link" href="#add-find">Skip to adding a find</a>
      <header className="masthead"><a className="brand" href="/">RelicRat</a><span>Your collection, one copy at a time.</span><SignOut /></header>
      <main>
        <div className="development"><strong>Synthetic collection trial</strong><span>Use made-up records and test photos. Owner sign-in is enabled. Production backups are not ready.</span></div>
        {settings && types && <CollectionSetup types={types} key={settingsVersion} settings={settings} runSave={runSave} locked={busy || uncertain} saved={value=>{setSettings(value);if(!title && !notes && !artist && !format && !edition && !issueNumber && !publisher) setCollectionType(value.default_type);}} reload={()=>setSettingsVersion(value=>value+1)} />}
        {settingsError && <p className="error" role="alert">{settingsError} Collection preferences are unavailable. <button disabled={busy} onClick={()=>setSettingsVersion(value=>value+1)}>Reload settings</button> <button disabled={busy} onClick={()=>{setGenericEntry(true);changeType('other');}}>Use generic entry</button></p>}
        {!settings && !settingsError && <p role="status">Loading collection settings…</p>}
        <div className="workspace">
          <div className="workbench">
            <section className="intake" aria-labelledby="add-find">
              <h1 id="add-find">Add a find</h1>
              <p className="intro">Start with a title. Everything else is optional.</p>
              <form onSubmit={create} aria-label="Add a find">
                <fieldset disabled={busy || uncertain || (!settings && !genericEntry)}>
                  {settings && <><label htmlFor="find-type">What are you adding?</label><select id="find-type" value={collectionType} onChange={event=>changeType(event.target.value as CollectionTypeId)}>{types && Object.values(types).map(type=><option key={type.id} value={type.id}>{type.label}</option>)}</select></>}
                  {(types?.[collectionType].entry_order || ['title', ...(types?.[collectionType].fields.map(field=>field.key) || [])]).map(key=>{
                    if(key==='title') return <Fragment key="title"><label htmlFor="find-title">{types?.[collectionType].title.label || 'Title'}</label>
                      <input ref={titleInput} id="find-title" required maxLength={types?.[collectionType].title.max_length || 500} value={title} onChange={e=>{setTitle(e.target.value);draftTouched.current=true;}} placeholder={types?.[collectionType].title.placeholder} aria-describedby="intake-help" /></Fragment>;
                    const field = types?.[collectionType].fields.find(field=>field.key===key);
                    const values: Record<string,string> = {artist,format,edition,notes,issue_number:issueNumber,publisher};
                    const setters: Record<string,(value:string)=>void> = {artist:setArtist,format:setFormat,edition:setEdition,notes:setNotes,issue_number:setIssueNumber,publisher:setPublisher};
                    if(!field || !showField(key,values[key])) return null;
                    return <Fragment key={key}><label htmlFor={`find-${key}`}>{field.label} (optional)</label>
                      {key==='notes' ? <textarea id="find-notes" maxLength={field.max_length} rows={3} value={notes} onChange={e=>{setNotes(e.target.value);draftTouched.current=true;}} placeholder={field.placeholder} aria-describedby="intake-help" />
                        : <ObservationInput key={`${key}-${entryVersion}`} id={`find-${key}`} field={field} value={values[key]} change={value=>{setters[key](value);draftTouched.current=true;}} />}</Fragment>;
                  })}
                  {!types && <><label htmlFor="find-notes">Notes (optional)</label><textarea id="find-notes" maxLength={10000} rows={3} value={notes} onChange={e=>{setNotes(e.target.value);draftTouched.current=true;}} /></>}
                  <p className="hint" id="intake-help">You can add an edition, photos or storage whenever you like.</p>
                  <button className="primary" type="submit">{busy ? 'Saving…' : 'Save copy'}</button>
                </fieldset>
              </form>
              {saveError && <p className="error" role="alert">{saveError}</p>}
              {uncertain && <p className="hint">Check for this copy before saving again. <button className="text-button" onClick={reloadInventory} disabled={busy || loading}>Reload inventory</button></p>}
              <p className="notice" role="status">{notice}</p>
            </section>
            {selected ? <CopyDetail key={selected} copyId={selected} runSave={runSave} busy={busy} blocked={uncertain} changed={changed} types={types} comicFields={settings?.comic_fields || []} recordFields={settings?.record_fields || []} />
              : <div className="record-placeholder"><h2>Open a copy to edit it</h2><p>Choose a saved copy to edit its title, edition, photos and storage.</p></div>}
          </div>
          <section className="collection" aria-labelledby="collection-title">
            <div className="section-heading"><h2 id="collection-title">Your collection</h2><button className="quiet" disabled={busy || loading} onClick={reloadInventory}>Reload inventory</button></div>
            <label htmlFor="collection-type-filter">Show collection type</label>
            <select id="collection-type-filter" value={typeFilter} disabled={busy || !types} onChange={event=>{setTypeFilter(event.target.value as CollectionTypeId | '');setPage(0);}}>
              <option value="">All types</option>{types && Object.values(types).map(type=><option key={type.id} value={type.id}>{type.plural_label}</option>)}
            </select>
            <form className="search" onSubmit={search} aria-label="Search inventory">
              <label htmlFor="query">Find a copy</label>
              <div className="search-controls"><input id="query" type="search" maxLength={200} value={draftQuery} onChange={e => setDraftQuery(e.target.value)} placeholder="Search titles, notes, or identified names" disabled={busy} /><button type="submit" disabled={busy}>Search</button></div>
              {query && <button className="text-button" type="button" disabled={busy} onClick={() => { setDraftQuery(''); setQuery(''); setPage(0); }}>Clear search</button>}
            </form>
            <div role="status" className="result-status">{loading ? 'Loading copies…' : listError ? 'Inventory unavailable' : `${items.length} ${items.length === 1 ? 'copy' : 'copies'} on this page${typeFilter ? ` · ${types?.[typeFilter].plural_label || typeFilter}` : ''}${query ? ` matching “${query}”` : ''}`}</div>
            {listError ? <p className="error" role="alert">{listError} Use Reload inventory to try again.</p>
              : loading ? <div className="loading-lines" aria-hidden="true"><span /><span /><span /></div>
              : items.length === 0 ? <div className="empty"><h3>{query || typeFilter ? 'No matching copies' : page ? 'No more copies on this page' : 'Your first find starts here'}</h3><p>{typeFilter ? 'Try another collection type or choose All types. You can also clear the search.' : query ? 'Try a shorter phrase or clear the search. Search treats symbols as literal text.' : page ? 'Go back to the previous page or reload the inventory.' : 'Enter a title and save. You can add everything else later.'}</p></div>
              : <ul className="inventory-list">{items.map(copy => <li key={copy.id}><button disabled={busy} className="inventory-row" aria-label={`Open ${copyName(copy)}${copy.edition_label ? ` · ${copy.edition_label}` : ''}`} aria-pressed={copy.id === selected} onClick={() => { setSelected(copy.id); setNotice(''); }}><strong>{copyName(copy)}</strong><span>{copy.description && copy.title ? copy.description : 'Open this physical copy'}</span><small>{copy.edition_label || (copy.edition_label === null && copy.release_id ? 'Catalog matched' : 'Saved copy')} · {copy.storage_location_id ? 'Location assigned' : 'No location yet'}</small></button></li>)}</ul>}
            <nav className="pagination" aria-label="Inventory pages"><button disabled={busy || loading || page === 0} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {page + 1}</span><button disabled={busy || loading || !!listError || !more} onClick={() => setPage(value => value + 1)}>Next</button></nav>
          </section>
        </div>
      </main>
      <footer>Provisional intake, photos, manual identification, storage, and search. Production recovery and broader deployment hardening remain unfinished.</footer>
    </>
  );
}
