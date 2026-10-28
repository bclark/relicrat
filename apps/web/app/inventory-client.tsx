'use client';

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, copyName, errorText, jsonSave, type InventoryCopy, type RunSave } from '../lib/inventory-client';
import CopyDetail from './copy-detail';

const PAGE = 20;
export default function InventoryClient() {
  const [title, setTitle] = useState('');
  const [notes, setNotes] = useState('');
  const [saveError, setSaveError] = useState('');
  const [notice, setNotice] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const [busy, setBusy] = useState(false);
  const saveLock = useRef(false);
  const titleInput = useRef<HTMLInputElement>(null);
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
    api<InventoryCopy[]>(`inventory?limit=${PAGE + 1}&offset=${page * PAGE}&q=${encodeURIComponent(query)}`, { signal: controller.signal })
      .then(result => {
        if (controller.signal.aborted) return;
        setItems(result.slice(0, PAGE)); setMore(result.length > PAGE);
        if (reviewReload.current) { setUncertain(false); reviewReload.current = false; }
      })
      .catch(error => { if (!controller.signal.aborted) setListError(errorText(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query, page, refresh]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (uncertain) return;
    if (!title.trim() && !notes.trim()) {
      setSaveError('Add a title or notes so you can recognize this copy later.'); titleInput.current?.focus(); return;
    }
    try {
      await runSave(async () => {
        setSaveError(''); setNotice('');
        const copy = await api<InventoryCopy>('inventory', jsonSave({ title: title.trim() || null, description: notes.trim() || null }));
        setTitle(''); setNotes(''); setSelected(copy.id);
        setDraftQuery(''); setQuery(''); setPage(0); changed();
        setNotice('Copy saved. Add its photo or location below.');
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
      <header className="masthead"><a className="brand" href="/">RelicRat</a><span>Your collection, one copy at a time.</span></header>
      <main>
        <div className="development"><strong>Synthetic collection trial</strong><span>Use made-up records and test photos. Authentication and production backups are not ready.</span></div>
        <div className="workspace">
          <div className="workbench">
            <section className="intake" aria-labelledby="add-find">
              <h1 id="add-find">Add a find</h1>
              <p className="intro">Start with what you know. Identification can come later.</p>
              <form onSubmit={create} aria-label="Add a find">
                <fieldset disabled={busy || uncertain}>
                  <label htmlFor="find-title">Title</label>
                  <input ref={titleInput} id="find-title" maxLength={500} value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Comic with a blue cover" aria-describedby="intake-help" />
                  <label htmlFor="find-notes">Notes</label>
                  <textarea id="find-notes" maxLength={10000} rows={3} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Distinctive details, condition, or where you found it" aria-describedby="intake-help" />
                  <p className="hint" id="intake-help">A title or notes is required. Add photos and storage after saving.</p>
                  <button className="primary" type="submit">{busy ? 'Saving…' : 'Save copy'}</button>
                </fieldset>
              </form>
              {saveError && <p className="error" role="alert">{saveError}</p>}
              {uncertain && <p className="hint">Check for this copy before saving again. <button className="text-button" onClick={reloadInventory} disabled={busy || loading}>Reload inventory</button></p>}
              <p className="notice" role="status">{notice}</p>
            </section>
            {selected ? <CopyDetail key={selected} copyId={selected} runSave={runSave} busy={busy} blocked={uncertain} changed={changed} />
              : <div className="record-placeholder"><h2>Give each copy a home</h2><p>Save a find or open a copy from your collection to add photos and choose its storage location.</p></div>}
          </div>
          <section className="collection" aria-labelledby="collection-title">
            <div className="section-heading"><h2 id="collection-title">Your collection</h2><button className="quiet" disabled={busy || loading} onClick={reloadInventory}>Reload inventory</button></div>
            <form className="search" onSubmit={search} aria-label="Search inventory">
              <label htmlFor="query">Find a copy</label>
              <div className="search-controls"><input id="query" type="search" maxLength={200} value={draftQuery} onChange={e => setDraftQuery(e.target.value)} placeholder="Search titles, notes, or identified names" disabled={busy} /><button type="submit" disabled={busy}>Search</button></div>
              {query && <button className="text-button" type="button" disabled={busy} onClick={() => { setDraftQuery(''); setQuery(''); setPage(0); }}>Clear search</button>}
            </form>
            <div role="status" className="result-status">{loading ? 'Loading copies…' : listError ? 'Inventory unavailable' : `${items.length} ${items.length === 1 ? 'copy' : 'copies'} on this page${query ? ` matching “${query}”` : ''}`}</div>
            {listError ? <p className="error" role="alert">{listError} Use Reload inventory to try again.</p>
              : loading ? <div className="loading-lines" aria-hidden="true"><span /><span /><span /></div>
              : items.length === 0 ? <div className="empty"><h3>{query ? 'No matching copies' : page ? 'No more copies on this page' : 'Your first find starts here'}</h3><p>{query ? 'Try a shorter phrase or clear the search. Search treats symbols as literal text.' : page ? 'Go back to the previous page or reload the inventory.' : 'Add a title or a few notes. You do not need to identify the collectible yet.'}</p></div>
              : <ul className="inventory-list">{items.map(copy => <li key={copy.id}><button disabled={busy} className="inventory-row" aria-label={`Open ${copyName(copy)}`} aria-pressed={copy.id === selected} onClick={() => { setSelected(copy.id); setNotice(''); }}><strong>{copyName(copy)}</strong><span>{copy.description && copy.title ? copy.description : 'Open this physical copy'}</span><small>{copy.identification_status === 'unidentified' ? 'Not identified yet' : copy.identification_status} · {copy.storage_location_id ? 'Location assigned' : 'No location yet'}</small></button></li>)}</ul>}
            <nav className="pagination" aria-label="Inventory pages"><button disabled={busy || loading || page === 0} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {page + 1}</span><button disabled={busy || loading || !!listError || !more} onClick={() => setPage(value => value + 1)}>Next</button></nav>
          </section>
        </div>
      </main>
      <footer>Provisional intake, photos, storage, and search. Catalog identification and production recovery are separate work.</footer>
    </>
  );
}
