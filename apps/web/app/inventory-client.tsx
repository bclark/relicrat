'use client';

import ObservationInput from './observation-input';
import SignOut from './sign-out';
import CollectionSetup from './collection-setup';
import CollectionAuthoring from './collection-authoring';
import CustomCollections from './custom-collections';
import Appearance from './appearance';
import CsvImport from './csv-import';
import BarcodeInput from './barcode-input';
import GroupedCollection from './grouped-collection';
import CollectionRows from './collection-rows';
import StorageFilter from './storage-filter';

import { Fragment, useCallback, useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react';
import { api, ApiError, copyName, errorText, jsonSave, type BarcodeReading, type CollectionSettings, type CollectionTypeId, type CollectionTypes, type InventoryCopy,type CatalogCover, type RunSave } from '../lib/inventory-client';
import CopyDetail from './copy-detail';

const PAGE = 20;
export default function InventoryClient() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [settingsPanel, setSettingsPanel] = useState<'appearance' | 'collection' | null>(null);
  const [entryOpen, setEntryOpen] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [detailOpen,setDetailOpen]=useState(false);
  const [quickEntry,setQuickEntry]=useState('');
  const [quickReading,setQuickReading]=useState<BarcodeReading|null>(null);
  const [pageCategory,setPageCategory]=useState<CollectionTypeId|'all'>('all');
  const [view,setView]=useState<'list'|'bricks'>('list');
  const quickInput=useRef<HTMLInputElement>(null),collectionHeading=useRef<HTMLHeadingElement>(null),lastQuick=useRef('');
  const categoryTypes:CollectionTypeId[]=['record','comic','movie','other'];
  function openCopy(id:string){setSelected(id);setDetailOpen(true);setNotice('');requestAnimationFrame(()=>document.getElementById('record-title')?.focus());}
  function backToCollection(){setDetailOpen(false);requestAnimationFrame(()=>{(document.getElementById(`copy-row-${selected}`)||collectionHeading.current)?.focus();});}
  function beginEntry(value:string){
    const text=value.trim();setSaveError('');
    if(/^\d{8}$/.test(text)){setSaveError('Eight-digit barcodes can be UPC-E or EAN-8. Scan it to preserve the format, or enter the expanded UPC/EAN.');return;}
    if(/^(?:\d{12}|\d{13})$/.test(text)){
      const format=text.length===13?'EAN_13':'UPC_A';
      if(!types?.[collectionType].barcode_formats?.includes(format)){setSaveError('This barcode format is not supported for this collection type.');return;}
      if(text!==lastQuick.current||barcode?.value!==text)setQuickReading({value:text,format,supplement:null});
    }else if(text&&text!==lastQuick.current)setTitle(text);
    lastQuick.current=text;setEntryOpen(true);draftTouched.current=true;
  }

  useEffect(() => {
    const query = window.matchMedia('(max-width:759px)');
    const update = () => setMobile(query.matches);
    update(); query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  const accountNav = useRef<HTMLDivElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!menuOpen) return;
    function dismiss(event: PointerEvent) {
      if (!accountNav.current?.contains(event.target as Node)) setMenuOpen(false);
    }
    document.addEventListener('pointerdown', dismiss);
    return () => document.removeEventListener('pointerdown', dismiss);
  }, [menuOpen]);
  useEffect(() => {
    if (settingsPanel === 'appearance') document.querySelector<HTMLElement>('#appearance-editor h2')?.focus();
  }, [settingsPanel]);
  function closeSettings() {
    setSettingsPanel(null);
    const control = window.matchMedia('(max-width:650px)').matches ? menuButton.current : document.getElementById(`${settingsPanel}-control`);
    control?.focus();
  }
  function toggleSettings(panel: 'appearance' | 'collection') {
    if (settingsPanel === panel) closeSettings();
    else setSettingsPanel(panel);
    setMenuOpen(false);
  }
  const [createdCollection,setCreatedCollection]=useState({id:'',sequence:0});
  const [appearanceStyles, setAppearanceStyles] = useState<CSSProperties>({});
  const [entryVersion, setEntryVersion] = useState(0);
  const [title, setTitle] = useState('');
  const [catalogCover,setCatalogCover]=useState<CatalogCover|null>(null);
  const [barcode,setBarcode]=useState<BarcodeReading|null>(null);
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
  const [mediaFormat,setMediaFormat] = useState('');
  const [studio,setStudio] = useState('');
  const [edition, setEdition] = useState('');
  const draftTouched = useRef(false);
  const record = collectionType==='record';
  const showField = (key:string,value:string) => collectionType==='other' || !!value || (collectionType==='movie' ? settings?.movie_fields || ['media_format','studio','edition','notes'] : collectionType==='comic' ? settings?.comic_fields : settings?.record_fields)?.includes(key as never);
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
    if((quickEntry || title || notes || artist || format || mediaFormat || studio || edition || issueNumber || publisher || barcode) && !window.confirm('Changing type will discard this unsaved find. Change type?')) return;
    setQuickEntry('');setQuickReading(null);lastQuick.current='';setCatalogCover(null);setBarcode(null);setEntryVersion(value=>value+1);setCollectionType(value);setIssueNumber('');setPublisher('');setTitle('');setNotes('');setArtist('');setFormat('');setMediaFormat('');setStudio('');setEdition('');setSaveError('');draftTouched.current=true;
  }
  const [notes, setNotes] = useState('');
  const [saveError, setSaveError] = useState('');
  const [notice, setNotice] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const [busy, setBusy] = useState(false);
  const saveLock = useRef(false);
  const titleInput = useRef<HTMLInputElement>(null);
  const [browseView,setBrowseView]=useState<'groups'|'copies'>('groups');
  const [storageFilter,setStorageFilter]=useState('');
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
  useLayoutEffect(()=>{if(entryOpen)titleInput.current?.focus();},[entryOpen]);
  useEffect(()=>{
    const text=quickEntry.trim();
    if(entryOpen||busy||uncertain||!settings||text===lastQuick.current||!/^(?:\d{12}|\d{13})$/.test(text))return;
    const timer=setTimeout(()=>beginEntry(text),500);return()=>clearTimeout(timer);
  },[quickEntry,entryOpen,busy,uncertain,settings,collectionType,types]);

  const runSave: RunSave = useCallback(async function<T>(action: () => Promise<T>) {
    if (saveLock.current) return;
    saveLock.current = true;
    setBusy(true);
    try { return await action(); }
    finally { saveLock.current = false; setBusy(false); }
  }, []);
  const changed = useCallback(() => setRefresh(value => value + 1), []);

  const grouped=browseView==='groups' && (!typeFilter || !!types?.[typeFilter].grouping);
  const filters=`&q=${encodeURIComponent(query)}${typeFilter?`&collection_type=${typeFilter}`:''}${storageFilter==='unassigned'?'&unassigned=true':storageFilter?`&storage_location_id=${storageFilter}`:''}`;
  useEffect(()=>setPageCategory('all'),[filters,browseView]);
  useEffect(() => {
    if(grouped){setLoading(false);return;}
    const controller = new AbortController();
    setLoading(true); setListError('');
    api<InventoryCopy[]>(`inventory?limit=${PAGE + 1}&offset=${page * PAGE}${filters}`, { signal: controller.signal })
      .then(result => {
        if (controller.signal.aborted) return;
        setItems(result.slice(0, PAGE)); setMore(result.length > PAGE);
        if (reviewReload.current) { setUncertain(false); reviewReload.current = false; }
      })
      .catch(error => { if (!controller.signal.aborted) setListError(errorText(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [filters, page, refresh, grouped]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (uncertain || (!settings && !genericEntry)) return;
    if (!title.trim()) {
      setSaveError('Add a title so you can recognize this copy later.'); titleInput.current?.focus(); return;
    }
    try {
      await runSave(async () => {
        setSaveError(''); setNotice('');
        const copy = await api<InventoryCopy>('inventory', jsonSave({ catalog_cover:catalogCover?{provider:catalogCover.provider,candidate_id:catalogCover.candidate_id}:null, barcode, title: title.trim(), description: notes.trim() || null, collection_type: collectionType, record_details: record ? {artist:artist.trim() || null,format:format.trim() || null} : {}, movie_details:collectionType==='movie' ? {media_format:mediaFormat.trim() || null,studio:studio.trim() || null} : {}, comic_details:collectionType==='comic' ? {issue_number:issueNumber.trim() || null,publisher:publisher.trim() || null} : {}, edition_label: edition.trim() || null }));
        setQuickEntry('');setQuickReading(null);lastQuick.current='';setEntryOpen(false);setDetailOpen(true);setPageCategory('all');setCatalogCover(null);setBarcode(null);setEntryVersion(value=>value+1);setIssueNumber('');setPublisher(''); setTitle(''); setNotes(''); setArtist('');setFormat('');setMediaFormat('');setStudio('');setEdition('');draftTouched.current=false; setSelected(copy.id);
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
    if (uncertain) { setBrowseView('copies'); setTypeFilter(''); setStorageFilter(''); setDraftQuery(''); setQuery(''); setPage(0); }
    changed();
  }
  function search(event: FormEvent) {
    event.preventDefault(); setQuery(draftQuery.trim()); setPage(0); changed();
  }
  return (
    <div className="themed-app" style={appearanceStyles}>
      <a className="skip-link" href="#add-find" onClick={()=>{setDetailOpen(false);setEntryOpen(true);}}>Skip to adding a find</a>
      <header className="masthead">
        <a className="brand" href="/">RelicRat</a><span className="brand-tagline">Your collection, one copy at a time.</span>
        <div className="account-nav" ref={accountNav} onKeyDown={event => {
          if (event.key === 'Escape' && menuOpen) { setMenuOpen(false); menuButton.current?.focus(); }
        }} onBlur={event => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setMenuOpen(false);
        }}>
          <button className="menu-toggle quiet" ref={menuButton} type="button" aria-expanded={menuOpen} aria-controls="account-actions" onClick={() => setMenuOpen(value => !value)}>Menu</button>
          <div id="account-actions" className="account-actions" data-open={menuOpen}>
            <button id="appearance-control" className="quiet" type="button" aria-expanded={settingsPanel === 'appearance'} aria-controls="appearance-editor" onClick={() => toggleSettings('appearance')}>{settingsPanel === 'appearance' ? 'Close appearance' : 'Appearance'}</button>
            {settings && types && <button id="collection-control" className="quiet" type="button" disabled={busy || uncertain} aria-expanded={settingsPanel === 'collection'} aria-controls="collection-editor" onClick={() => toggleSettings('collection')}>{settings.status === 'not_started' ? 'Set up your collection' : 'Collection settings'}</button>}
            <SignOut />
          </div>
        </div>
      </header>
      <main className="collection-main">
        <Appearance applied={setAppearanceStyles} open={settingsPanel === 'appearance'} />
        {settings && types && <CollectionSetup types={types} key={settingsVersion} settings={settings} open={settingsPanel === 'collection'} close={closeSettings} runSave={runSave} locked={busy || uncertain} saved={value=>{setSettings(value);if(!quickEntry && !title && !notes && !artist && !format && !mediaFormat && !studio && !barcode && !edition && !issueNumber && !publisher) setCollectionType(value.default_type);}} reload={()=>setSettingsVersion(value=>value+1)} />}
        {settingsError && <p className="error" role="alert">{settingsError} Collection preferences are unavailable. <button disabled={busy} onClick={()=>setSettingsVersion(value=>value+1)}>Reload settings</button> <button disabled={busy} onClick={()=>{setGenericEntry(true);changeType('other');}}>Use generic entry</button></p>}
        {!settings && !settingsError && <p role="status">Loading collection settings…</p>}
        <CollectionAuthoring runSave={runSave} locked={busy||uncertain} onCreated={id=>setCreatedCollection(event=>({id,sequence:event.sequence+1}))} />
        <CustomCollections refresh={refresh} createdEvent={createdCollection} runSave={runSave} locked={busy||uncertain} changed={changed} openCopy={openCopy} />
        <CsvImport runSave={runSave} locked={busy || uncertain} changed={changed} openCopy={openCopy} />
        <div className={`workspace${detailOpen ? ' detail-open' : ''}`}>
          <div className="workbench">
            <section className="intake" aria-labelledby="add-find">
              <h2 id="add-find" tabIndex={-1}>Add an item</h2>
              <form className="quick-intake" aria-label="Start adding an item" onSubmit={event=>{event.preventDefault();beginEntry(quickEntry);}}>
                <fieldset disabled={busy||uncertain||(!settings&&!genericEntry)}>
                  <label htmlFor="quick-entry">Title or barcode</label>
                  <input id="quick-entry" ref={quickInput} maxLength={500} value={quickEntry} onChange={event=>{setQuickEntry(event.target.value);draftTouched.current=true;}} placeholder="Type, then press Enter" aria-controls="intake-fields" aria-expanded={entryOpen} autoComplete="off"/>
                  <label htmlFor="find-type">What are you adding?</label><select id="find-type" value={collectionType} onChange={event=>changeType(event.target.value as CollectionTypeId)}>{types?Object.values(types).map(type=><option key={type.id} value={type.id}>{type.label}</option>):<option value="other">Other</option>}</select>
                  <button type="submit" className="quiet intake-continue">Review item</button>
                </fieldset>
              </form>
                    <BarcodeInput key={`${entryVersion}-${collectionType}-${JSON.stringify(types?.[collectionType].lookup)}`} quickReading={quickReading} definition={types?.[collectionType]} values={{title,artist,format,media_format:mediaFormat,studio,edition,issue_number:issueNumber,publisher}} cover={catalogCover} removeCover={()=>setCatalogCover(null)} apply={(fields,cover)=>{if(cover)setCatalogCover(cover);const setters:Record<string,(value:string)=>void>={title:setTitle,artist:setArtist,format:setFormat,media_format:setMediaFormat,studio:setStudio,edition:setEdition,issue_number:setIssueNumber,publisher:setPublisher};for(const [key,value] of Object.entries(fields))setters[key]?.(value);draftTouched.current=true;setEntryOpen(true);titleInput.current?.focus();}} value={barcode} change={value=>{setQuickReading(null);setCatalogCover(null);setBarcode(value);draftTouched.current=true;setEntryOpen(true);titleInput.current?.focus();}} formats={types?.[collectionType].barcode_formats || []} locked={busy || uncertain || !settings || (mobile && detailOpen)} />
              <div id="intake-fields" hidden={!entryOpen}>
                <div className="intake-review-heading"><h3>Review item</h3><button type="button" className="text-button" onClick={()=>{setEntryOpen(false);quickInput.current?.focus();}}>Hide details</button></div>
                <p className="intro">Start with a title. Everything else is optional.</p>
                <form onSubmit={create} aria-label="Add a find"><fieldset disabled={busy||uncertain||(!settings&&!genericEntry)}>
                    {(types?.[collectionType].entry_order || ['title', ...(types?.[collectionType].fields.map(field=>field.key) || [])]).map(key=>{
                      if(key==='title') return <Fragment key="title"><label htmlFor="find-title">{types?.[collectionType].title.label || 'Title'}</label>
                        <input ref={titleInput} id="find-title" required maxLength={types?.[collectionType].title.max_length || 500} value={title} onChange={e=>{setTitle(e.target.value);draftTouched.current=true;}} placeholder={types?.[collectionType].title.placeholder} aria-describedby="intake-help" /></Fragment>;
                      const field = types?.[collectionType].fields.find(field=>field.key===key);
                      const values: Record<string,string> = {artist,format,media_format:mediaFormat,studio,edition,notes,issue_number:issueNumber,publisher};
                      const setters: Record<string,(value:string)=>void> = {artist:setArtist,format:setFormat,media_format:setMediaFormat,studio:setStudio,edition:setEdition,notes:setNotes,issue_number:setIssueNumber,publisher:setPublisher};
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
              </div>
              {saveError && <p className="error" role="alert">{saveError}</p>}
              {uncertain && <p className="hint">Check for this copy before saving again. <button className="text-button" onClick={reloadInventory} disabled={busy || loading}>Reload inventory</button></p>}

            </section>
            {!grouped&&<nav className="categories" aria-label="Categories on this page"><h2>Categories</h2><p className="hint">Counts describe this loaded page only.</p><div className="category-controls">{(['all',...categoryTypes] as const).map(type=><button type="button" className="category-button quiet" key={type} disabled={busy||loading||!!listError} aria-pressed={pageCategory===type} onClick={()=>setPageCategory(type)}>{type==='all'?'All items':types?.[type].plural_label||type}{!loading&&!listError&&<span>{type==='all'?items.length:items.filter(copy=>copy.collection_type===type).length}</span>}</button>)}</div></nav>}
          </div>
          <section className="collection" aria-labelledby="collection-title">
            <div className="section-heading collection-heading"><h1 id="collection-title" tabIndex={-1} ref={collectionHeading}>Your collection</h1><div className="view-controls" aria-label="Collection view"><button type="button" className="quiet" aria-pressed={view==='list'} onClick={()=>setView('list')}>List</button><button type="button" className="quiet" aria-pressed={view==='bricks'} onClick={()=>setView('bricks')}>Bricks</button></div></div>
            <button className="quiet" disabled={busy||loading} onClick={reloadInventory}>Reload inventory</button>
            <div className={`inventory-results ${view}`}>
            <label htmlFor="collection-browse-view">Browse view</label><select id="collection-browse-view" value={browseView} disabled={busy} onChange={event=>{setBrowseView(event.target.value as 'groups'|'copies');setPage(0);}}><option value="groups">Grouped collection</option><option value="copies">Individual copies</option></select>
            <label htmlFor="collection-type-filter">Show collection type</label>
            <select id="collection-type-filter" value={typeFilter} disabled={busy || !types} onChange={event=>{setTypeFilter(event.target.value as CollectionTypeId | '');setPage(0);}}>
              <option value="">All types</option>{types && Object.values(types).map(type=><option key={type.id} value={type.id}>{type.plural_label}</option>)}
            </select>
            <StorageFilter value={storageFilter} change={value=>{setStorageFilter(value);setPage(0);}} busy={busy} refresh={refresh} />
            <form className="search" onSubmit={search} aria-label="Search inventory">
              <label htmlFor="query">Find a copy</label>
              <div className="search-controls"><input id="query" type="search" maxLength={200} value={draftQuery} onChange={e => setDraftQuery(e.target.value)} placeholder="Title, artist, studio or barcode" disabled={busy} /><button type="submit" disabled={busy}>Search</button></div>
              {query && <button className="text-button" type="button" disabled={busy} onClick={() => { setDraftQuery(''); setQuery(''); setPage(0); }}>Clear search</button>}
            </form>
            {grouped?<GroupedCollection key={filters} type={typeFilter as ''|'record'|'comic'|'movie'} noun={typeFilter?types?.[typeFilter].grouping?.plural_label||'Groups':'Collection types'} filters={filters} refresh={refresh} busy={busy||!types} selected={selected} open={openCopy} chooseType={value=>{setTypeFilter(value);setPage(0);}}/>:<>
            <div role="status" className="result-status">{loading ? 'Loading copies…' : listError ? 'Inventory unavailable' : `${items.length} ${items.length === 1 ? 'copy' : 'copies'} on this page${typeFilter ? ` · ${types?.[typeFilter].plural_label || typeFilter}` : ''}${query ? ` matching “${query}”` : ''}`}</div>
            {listError ? <p className="error" role="alert">{listError} Use Reload inventory to try again.</p>
              : loading ? <div className="loading-lines" aria-hidden="true"><span /><span /><span /></div>
              : items.length === 0 ? <div className="empty"><h3>{query || typeFilter ? 'No matching copies' : page ? 'No more copies on this page' : 'Your first find starts here'}</h3><p>{typeFilter ? 'Try another collection type or choose All types. You can also clear the search.' : query ? 'Try a shorter phrase or clear the search. Search treats symbols as literal text.' : page ? 'Go back to the previous page or reload the inventory.' : 'Enter a title and save. You can add everything else later.'}</p></div>
              : <CollectionRows groupByType types={types} items={pageCategory==='all'?items:items.filter(copy=>copy.collection_type===pageCategory)} busy={busy} selected={selected} open={openCopy}/>}

            <nav className="pagination" aria-label="Inventory pages"><button disabled={busy || loading || page === 0} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {page + 1}</span><button disabled={busy || loading || !!listError || !more} onClick={() => setPage(value => value + 1)}>Next</button></nav>
            </>}
            {!grouped&&!loading&&!listError&&pageCategory!=='all'&&items.length>0&&!items.some(copy=>copy.collection_type===pageCategory)&&<p>No copies of this category on this page. Choose All items or another page.</p>}
            </div>
          </section>
          <aside className="copy-inspector" aria-label="Selected copy">
            <button type="button" className="text-button back-to-collection" disabled={busy} onClick={backToCollection}>Back to collection</button>
            {selected ? <CopyDetail key={selected} copyId={selected} runSave={runSave} busy={busy} blocked={uncertain} changed={changed} types={types} movieFields={settings?.movie_fields || ['media_format','studio','edition','notes']} comicFields={settings?.comic_fields || []} recordFields={settings?.record_fields || []} />
              : <div className="record-placeholder"><h2>Open a copy to edit it</h2><p>Choose a saved copy to edit its title, edition, photos and storage.</p></div>}
          </aside>
        </div>
        <p className="notice" role="status">{notice}</p>
        <div className="development"><strong>Synthetic collection trial</strong><span>Use made-up records and test photos. Owner sign-in is enabled. Production backups are not ready.</span></div>
      </main>
      <footer>Provisional intake, photos, manual identification, storage, and search. Production recovery and broader deployment hardening remain unfinished.</footer>
    </div>
  );
}
