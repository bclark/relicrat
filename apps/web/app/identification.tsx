'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { api, errorText, jsonSave, type InventoryCopy, type RunSave } from '../lib/inventory-client';

type Category = { id: string; name: string };
type Item = { id: string; category_id: string; canonical_name: string };
type Release = { id: string; catalog_item_id: string; name: string | null };
type History = { id: string; before_catalog_item_id: string | null; after_catalog_item_id: string; before_release_id: string | null; after_release_id: string | null; after_revision: number; created_at: string };
type Props = { copy: InventoryCopy; runSave: RunSave; locked: boolean; saved: (copy: InventoryCopy) => void; failed: (error: unknown) => void };
const releaseName = (release: Release) => release.name || `Unnamed release · ${release.id}`;

// Four bounded catalog/history readers share cancellation and page semantics.
function usePage<T>(path: string | null, page: number, refresh: string) {
  const [state, setState] = useState({ items: [] as T[], busy: true, more: false, error: '' });
  useEffect(() => {
    const controller = new AbortController();
    setState({ items: [], busy: !!path, more: false, error: '' });
    if (path) api<T[]>(`${path}${path.includes('?') ? '&' : '?'}limit=21&offset=${page * 20}`, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) setState({ items: result.slice(0, 20), busy: false, more: result.length > 20, error: '' }); })
      .catch(problem => { if (!controller.signal.aborted) setState({ items: [], busy: false, more: false, error: errorText(problem) }); });
    return () => controller.abort();
  }, [path, page, refresh]);
  return state;
}
function Pages({ label, page, more, disabled, select }: { label: string; page: number; more: boolean; disabled: boolean; select: (value: number) => void }) {
  if (page === 0 && !more) return null;
  return <nav className="pagination" aria-label={label}><button type="button" className="quiet" disabled={disabled || page === 0} onClick={() => select(page - 1)}>Previous</button><span>Page {page + 1}</span><button type="button" className="quiet" disabled={disabled || !more} onClick={() => select(page + 1)}>Next</button></nav>;
}

export default function Identification({ copy, runSave, locked, saved, failed }: Props) {
  const [current, setCurrent] = useState<Item | null>(null);
  const [currentRelease, setCurrentRelease] = useState<Release | null>(null);
  const [selected, setSelected] = useState<Item | null>(null);
  const [edition, setEdition] = useState<Release | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [searchVersion, setSearchVersion] = useState(0);
  const [page, setPage] = useState(0);
  const [releasePage, setReleasePage] = useState(0);
  const [categoryPage, setCategoryPage] = useState(0);
  const [historyPage, setHistoryPage] = useState(0);
  const [category, setCategory] = useState<Category | null>(null);
  const [newCategory, setNewCategory] = useState('');
  const [newItem, setNewItem] = useState('');
  const [newRelease, setNewRelease] = useState('');
  const [refresh, setRefresh] = useState(0);
  const items = usePage<Item>(`catalog/items?q=${encodeURIComponent(search)}`, page, `${refresh}-${searchVersion}`);
  const releases = usePage<Release>(selected ? `catalog/items/${selected.id}/releases` : null, releasePage, String(refresh));
  const categories = usePage<Category>('catalog/categories', categoryPage, String(refresh));
  const history = usePage<History>(`inventory/${copy.id}/reconciliations`, historyPage, `${refresh}-${copy.identification_revision}`);

  useEffect(() => {
    const controller = new AbortController(), options = { signal: controller.signal };
    setReady(false); setError('');
    Promise.all([
      copy.catalog_item_id ? api<Item>(`catalog/items/${copy.catalog_item_id}`, options) : Promise.resolve(null),
      copy.catalog_item_id && copy.release_id ? api<Release>(`catalog/items/${copy.catalog_item_id}/releases/${copy.release_id}`, options) : Promise.resolve(null),
    ]).then(([item, release]) => {
      if (controller.signal.aborted) return;
      setCurrent(item); setCurrentRelease(release); setSelected(item); setEdition(release); setReleasePage(0); setHistoryPage(0); setReady(true);
    }).catch(problem => { if (!controller.signal.aborted) setError(errorText(problem)); });
    return () => controller.abort();
  }, [copy.id, copy.catalog_item_id, copy.release_id, copy.identification_revision, refresh]);

  function choose(item: Item) {
    if (item.id === selected?.id) return;
    setSelected(item); setEdition(null); setReleasePage(0); setNewRelease(''); setNotice('');
  }
  async function create(event: FormEvent, kind: 'category' | 'item' | 'release') {
    event.preventDefault(); if (locked || !ready) return;
    try {
      await runSave(async () => {
        setError(''); setNotice('');
        if (kind === 'category') {
          const result = await api<Category>('catalog/categories', jsonSave({ name: newCategory.trim() }));
          setCategory(result); setNewCategory(''); setNotice('Category created. Choose it when creating a catalog entry.');
        } else if (kind === 'item' && category) {
          const result = await api<Item>('catalog/items', jsonSave({ category_id: category.id, canonical_name: newItem.trim() }));
          choose(result); setNewItem(''); setNotice('Catalog entry created. Use Save identification to link this physical copy.');
        } else if (kind === 'release' && selected) {
          const result = await api<Release>(`catalog/items/${selected.id}/releases`, jsonSave({ name: newRelease.trim() }));
          setEdition(result); setNewRelease(''); setNotice('Release created. Use Save identification to link this physical copy.');
        }
      });
    } catch (problem) { setError(errorText(problem)); failed(problem); }
  }
  async function identify(event: FormEvent) {
    event.preventDefault(); if (!selected || locked || !ready || releases.busy || releases.error) return;
    try {
      await runSave(async () => {
        setError(''); setNotice('');
        const result = await api<InventoryCopy>(`inventory/${copy.id}/reconcile`, jsonSave({ catalog_item_id: selected.id, release_id: edition?.id || null, expected_revision: copy.identification_revision }));
        saved(result); setNotice('Identification saved. This physical copy, its photos and storage are preserved.');
      });
    } catch (problem) { setError(errorText(problem)); failed(problem); }
  }
  const disabled = locked || !ready;
  const editionOptions = edition && !releases.items.some(item => item.id === edition.id) ? [edition, ...releases.items] : releases.items;
  const categoryOptions = category && !categories.items.some(item => item.id === category.id) ? [category, ...categories.items] : categories.items;
  return <div className="identification">
    <h3>Identification</h3>
    <p className="hint">Catalog entries describe collectibles; releases describe editions or variants. Linking one never adds another physical copy.</p>
    {!ready ? <p role="status">{error ? 'Identification could not be loaded.' : 'Loading identification…'}</p> : <p className="current-identification">Current: <strong>{current?.canonical_name || 'Not identified yet'}</strong>{currentRelease ? ` · ${releaseName(currentRelease)}` : current ? ' · No release specified' : ''}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    <p className="notice" role="status">{notice}</p>
    <button type="button" className="quiet" disabled={locked} onClick={() => setRefresh(value => value + 1)}>Reload catalog</button>
    <form aria-label="Search catalog" onSubmit={event => { event.preventDefault(); setPage(0); setSearch(query.trim()); setSearchVersion(value => value + 1); }}><fieldset disabled={disabled}><label htmlFor="catalog-search">Find a catalog entry</label><input id="catalog-search" maxLength={200} value={query} onChange={event => setQuery(event.target.value)} placeholder="e.g. Synthetic comic #1" /><button type="submit">Search catalog</button></fieldset></form>
    {items.busy ? <p role="status">Searching catalog…</p> : items.error ? <p role="alert" className="error">{items.error} Use Reload catalog to try again.</p> : <>
      {items.items.length ? <fieldset className="catalog-results" disabled={disabled}><legend>Catalog results · {items.items.length} on this page</legend>{items.items.map(item => <label key={item.id} className="catalog-choice"><input type="radio" name="catalog-item" checked={item.id === selected?.id} onChange={() => choose(item)} /><span>{item.canonical_name}<small>Reference {item.id.slice(0, 8)}</small></span></label>)}</fieldset> : <p className="hint">No catalog entries found. Search again or create an entry below.</p>}
      <Pages label="Catalog pages" page={page} more={items.more} disabled={locked || items.busy} select={setPage} />
    </>}
    <form aria-label="Save identification" onSubmit={identify}><fieldset disabled={disabled}>
      <p>Selected: <strong>{selected?.canonical_name || 'Choose a catalog entry above'}</strong></p>
      {selected && <><label htmlFor="catalog-release">Edition or variant</label><select id="catalog-release" value={edition?.id || ''} disabled={releases.busy || !!releases.error} onChange={event => setEdition(editionOptions.find(item => item.id === event.target.value) || null)}><option value="">No release specified</option>{editionOptions.map(item => <option key={item.id} value={item.id}>{releaseName(item)} · {item.id.slice(0, 8)}</option>)}</select>{releases.busy && <p role="status">Loading releases…</p>}{releases.error && <p className="error" role="alert">{releases.error} Use Reload catalog before saving.</p>}<Pages label="Release pages" page={releasePage} more={releases.more} disabled={disabled || releases.busy} select={setReleasePage} /></>}
      <p className="hint">No release specified saves catalog-only identification and removes any previous release. Saving records a manual identification, not a verified match.</p>
      <button type="submit" disabled={!selected || releases.busy || !!releases.error || (selected.id === copy.catalog_item_id && (edition?.id || null) === copy.release_id && copy.identification_status === 'identified')}>Save identification</button>
    </fieldset></form>
    <details className="new-location"><summary>Create a catalog entry</summary>
      <p className="hint">Search first. Similar names can describe different collectibles. New entries stay separate; nothing is merged automatically.</p>
      <form aria-label="Create catalog entry" onSubmit={event => create(event, 'item')}><fieldset disabled={disabled || categories.busy || !!categories.error}><label htmlFor="catalog-category">Category</label><select id="catalog-category" value={category?.id || ''} onChange={event => setCategory(categoryOptions.find(item => item.id === event.target.value) || null)}><option value="">Choose a category</option>{categoryOptions.map(item => <option key={item.id} value={item.id}>{item.name} · {item.id.slice(0, 8)}</option>)}</select><label htmlFor="catalog-name">Catalog name</label><input id="catalog-name" required maxLength={500} value={newItem} onChange={event => setNewItem(event.target.value)} /><button disabled={!category || !newItem.trim()} type="submit">Create catalog entry</button></fieldset></form>
      {categories.busy && <p role="status">Loading categories…</p>}{categories.error && <p role="alert" className="error">{categories.error} Use Reload catalog.</p>}<Pages label="Category pages" page={categoryPage} more={categories.more} disabled={disabled || categories.busy} select={setCategoryPage} />
      <form aria-label="Create category" onSubmit={event => create(event, 'category')}><fieldset disabled={disabled}><label htmlFor="category-name">New category name</label><input id="category-name" required maxLength={200} value={newCategory} onChange={event => setNewCategory(event.target.value)} /><button disabled={!newCategory.trim()} type="submit">Create category</button></fieldset></form>
    </details>
    {selected && <details className="new-location"><summary>Create a release for {selected.canonical_name}</summary><p className="hint">This release belongs only to the selected catalog entry. It saves separately from identification.</p><form aria-label="Create release" onSubmit={event => create(event, 'release')}><fieldset disabled={disabled || releases.busy || !!releases.error}><label htmlFor="release-name">Release name</label><input id="release-name" required maxLength={500} value={newRelease} onChange={event => setNewRelease(event.target.value)} /><button disabled={!newRelease.trim()} type="submit">Create release</button></fieldset></form></details>}
    <details className="movement-history"><summary>Identification history</summary><p className="hint">Oldest first. Full catalog and release references are retained so similar names remain distinguishable.</p>{history.busy ? <p role="status">Loading identification history…</p> : history.error ? <p className="error" role="alert">{history.error} Use Reload catalog.</p> : history.items.length ? <ol>{history.items.map(event => <li key={event.id}><span>{event.before_catalog_item_id || 'Unidentified'} to {event.after_catalog_item_id}</span><small>Release: {event.before_release_id || 'None'} to {event.after_release_id || 'None'}</small><small>Revision {event.after_revision} · {new Date(event.created_at).toLocaleString()}</small></li>)}</ol> : <p>No identification changes recorded.</p>}<Pages label="Identification history pages" page={historyPage} more={history.more} disabled={locked || history.busy} select={setHistoryPage} /></details>
  </div>;
}
