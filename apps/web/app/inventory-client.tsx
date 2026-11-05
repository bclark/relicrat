'use client';

import ItemIntake,{type IntakeStart} from './item-intake';
import SignOut from './sign-out';
import CollectionManager from './collection-manager';
import CollectionFilter from './collection-filter';
import ChecklistProgress from './checklist-progress';
import Appearance from './appearance';
import CsvImport from './csv-import';
import GroupedCollection from './grouped-collection';
import CollectionRows from './collection-rows';
import StorageFilter from './storage-filter';

import { useCallback, useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react';
import { api, errorText, type CollectionSettings, type CollectionTypeId, type CollectionTypes, type InventoryCopy,type RunSave } from '../lib/inventory-client';
import CopyDetail from './copy-detail';

const PAGE = 20;
export default function InventoryClient() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [settingsPanel, setSettingsPanel] = useState<'appearance' | 'collection' | null>(null);
  const [intakeVisible,setIntakeVisible]=useState(false);
  const detailGuard=useRef<()=>boolean>(()=>true);
  const browseScroll=useRef(0);
  const [collectionName,setCollectionName]=useState('');
  const [detailOpen,setDetailOpen]=useState(false);
  const [view,setView]=useState<'list'|'bricks'>('list');
  const collectionHeading=useRef<HTMLHeadingElement>(null),intakeGuard=useRef<()=>boolean>(()=>true);
  const [intakeStart,setIntakeStart]=useState<IntakeStart>({target:'',scope:'',name:'All items',sequence:0});
  const browseTitle=collectionName || 'Your collection';
  function openCopy(id:string){if(id!==selected&&!detailGuard.current())return;if(!intakeGuard.current())return;if(!detailOpen&&!intakeVisible)browseScroll.current=window.scrollY;setIntakeVisible(false);setSelected(id);setDetailOpen(true);if(id===selected)requestAnimationFrame(()=>document.getElementById('record-title')?.focus());}
  function backToCollection(){setDetailOpen(false);requestAnimationFrame(()=>{(document.getElementById(`copy-row-${selected}`)||collectionHeading.current)?.focus({preventScroll:true});window.scrollTo({top:browseScroll.current});});}
  function startIntake(target=browseCollection,entryId?:string){if(!intakeGuard.current())return;if(!intakeVisible)browseScroll.current=window.scrollY;if(target&&target!==browseCollection){setBrowseCollection(target);setPage(0);}setIntakeStart(old=>({target,scope:target,name:target===browseCollection?(target?browseTitle:'All items'):'collection',entryId,sequence:old.sequence+1}));setIntakeVisible(true);setDetailOpen(false);}
  function closeIntake(){setIntakeVisible(false);requestAnimationFrame(()=>{collectionHeading.current?.focus({preventScroll:true});window.scrollTo({top:browseScroll.current});});}
  const toolsPanel=useRef<HTMLDetailsElement>(null);
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
  const [collectionVersion,setCollectionVersion]=useState(0);
  const managementGuard=useRef<()=>boolean>(()=>true);
  const [appearanceStyles, setAppearanceStyles] = useState<CSSProperties>({});
  const [settings,setSettings]=useState<CollectionSettings|null>(null),[types,setTypes]=useState<CollectionTypes|null>(null);
  const [settingsError,setSettingsError]=useState(''),[settingsVersion,setSettingsVersion]=useState(0);
  const [busy,setBusy]=useState(false);
  const saveLock=useRef(false);
  useEffect(()=>{const c=new AbortController();setSettingsError('');Promise.all([api<CollectionSettings>('collection-settings',{signal:c.signal}),api<CollectionTypes>('collection-settings/types',{signal:c.signal}).then(value=>{if(!c.signal.aborted)setTypes(value);return value;})]).then(([value,definitions])=>{if(!c.signal.aborted){setSettings(value);setTypes(definitions);}}).catch(e=>{if(!c.signal.aborted)setSettingsError(errorText(e));});return()=>c.abort();},[settingsVersion]);
  const [browseView,setBrowseView]=useState<'groups'|'copies'>('groups');
  const [storageFilter,setStorageFilter]=useState('');
  const [browseCollection,setBrowseCollection]=useState('');
  const customCollectionId=browseCollection.startsWith('custom:')?browseCollection.slice(7):'';
  const typeFilter:CollectionTypeId|''=customCollectionId?'':browseCollection as CollectionTypeId|'';
  useEffect(()=>{const c=new AbortController();setCollectionName(customCollectionId?'Custom collection':typeFilter?types?.[typeFilter]?.plural_label||'Selected collection':'Your collection');if(customCollectionId)api<{name:string}>(`custom-collections/${customCollectionId}`,{signal:c.signal}).then(v=>{if(!c.signal.aborted)setCollectionName(v.name);}).catch(()=>{});return()=>c.abort();},[browseCollection,types]);
  function beginFigure(entryId?:string){startIntake(browseCollection,entryId);}
  function chooseCollection(value:string){if(busy)return;setIntakeVisible(false);setBrowseCollection(value);setPage(0);setDetailOpen(false);}
  const [draftQuery, setDraftQuery] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [items, setItems] = useState<InventoryCopy[]>([]);
  const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const runSave: RunSave = useCallback(async function<T>(action: () => Promise<T>) {
    if (saveLock.current) return;
    saveLock.current = true;
    setBusy(true);
    try { return await action(); }
    finally { saveLock.current = false; setBusy(false); }
  }, []);
  const changed = useCallback(() => setRefresh(value => value + 1), []);

  const grouped=!customCollectionId && browseView==='groups' && (!typeFilter || !!types?.[typeFilter]?.grouping);
  const filters=`&q=${encodeURIComponent(query)}${customCollectionId?`&custom_collection_id=${encodeURIComponent(customCollectionId)}`:typeFilter?`&collection_type=${typeFilter}${typeFilter==='other'?'&exclude_custom=true':''}`:''}${storageFilter==='unassigned'?'&unassigned=true':storageFilter?`&storage_location_id=${storageFilter}`:''}`;
  useEffect(() => {
    if(grouped){setLoading(false);return;}
    const controller = new AbortController();
    setLoading(true); setListError('');
    api<InventoryCopy[]>(`inventory?limit=${PAGE + 1}&offset=${page * PAGE}${filters}`, { signal: controller.signal })
      .then(result => {
        if (controller.signal.aborted) return;
        setItems(result.slice(0, PAGE)); setMore(result.length > PAGE);
      })
      .catch(error => { if (!controller.signal.aborted) setListError(errorText(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [filters, page, refresh, grouped]);

  function reloadInventory(){changed();}
  function search(event: FormEvent) {
    event.preventDefault(); setQuery(draftQuery.trim()); setPage(0); changed();
  }
  return (
    <div className="themed-app collection-journey" style={appearanceStyles} onClickCapture={event=>{const target=(event.target as HTMLElement).closest('a.brand,button');if((target?.matches('a.brand')||target?.textContent==='Sign out')&&(!detailGuard.current()||!managementGuard.current())){event.preventDefault();event.stopPropagation();}}}>
      <a className="skip-link" href="#add-find" onClick={()=>{startIntake();}}>Skip to adding a find</a>
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
            {<button id="collection-control" className="quiet" type="button" disabled={busy} aria-expanded={settingsPanel === 'collection'} aria-controls="collection-management" onClick={() => toggleSettings('collection')}>Manage collections</button>}
            <SignOut />
          </div>
        </div>
      </header>
      <main className="collection-main">
        <Appearance applied={setAppearanceStyles} open={settingsPanel === 'appearance'} />
        <CollectionManager open={settingsPanel==='collection'} close={closeSettings} guard={managementGuard} types={types} settings={settings} runSave={runSave} busy={busy} saved={setSettings} changed={()=>{changed();setCollectionVersion(v=>v+1);}} browse={value=>{chooseCollection(value);setSettingsPanel(null);}}/>
        {settingsError && <p className="error" role="alert">{settingsError} Collection preferences are unavailable. <button disabled={busy} onClick={()=>setSettingsVersion(value=>value+1)}>Reload settings</button> <button disabled={busy} onClick={()=>{if(!detailGuard.current()||!intakeGuard.current())return;setTypes(old=>old||({other:{schema_version:1,id:'other',label:'Other',plural_label:'Other finds',title:{key:'title',label:'Title',max_length:500,placeholder:'',suggested:true},fields:[{key:'notes',label:'Notes',max_length:10000,placeholder:'',suggested:true}],entry_order:['title','notes'],grouping:null}} as CollectionTypes));setSettings({status:'skipped',default_type:'other',records_enabled:false,record_fields:[],revision:0});setBrowseCollection('other');setIntakeStart(old=>({target:'other',scope:'other',name:'Other finds',sequence:old.sequence+1}));setIntakeVisible(true);setDetailOpen(false);}}>Use generic entry</button></p>}
        {!settings && !settingsError && <p role="status">Loading collection settings…</p>}
        <details className="collection-tools" ref={toolsPanel} hidden={settingsPanel==='collection'}><summary>Collection tools and imports</summary><CsvImport runSave={runSave} locked={busy} changed={changed} openCopy={openCopy}/></details>
        <div hidden={settingsPanel==='collection'} className={`workspace${detailOpen ? ' detail-open' : ''}${selected ? ' has-selection' : ''}`}>
          <aside className="collection-sidebar"><CollectionFilter value={browseCollection} change={chooseCollection} types={types} busy={busy} refresh={collectionVersion} /></aside>
          <ItemIntake start={intakeStart} visible={intakeVisible} guard={intakeGuard} close={closeIntake} openCopy={openCopy} types={types} settings={settings} busy={busy} runSave={runSave} saved={()=>changed()}/>
          <section className="collection" hidden={intakeVisible} aria-labelledby="collection-title">
            <div className="section-heading collection-heading"><h1 id="collection-title" tabIndex={-1} ref={collectionHeading}>{browseTitle}</h1><div className="view-controls" aria-label="Collection view"><button type="button" className="quiet" aria-pressed={view==='list'} onClick={()=>setView('list')}>List</button><button type="button" className="quiet" aria-pressed={view==='bricks'} onClick={()=>setView('bricks')}>Covers</button></div></div>
            <div className="collection-actions"><button className="primary" type="button" disabled={busy} aria-expanded={intakeVisible} onClick={()=>startIntake()}>Add an item</button><button className="text-button" disabled={busy||loading} onClick={reloadInventory}>Reload inventory</button></div>
                        <div className={`inventory-results ${view}`}>
            <div className="browse-mode"><label htmlFor="collection-browse-view">Browse view</label><select id="collection-browse-view" value={grouped?'groups':'copies'} disabled={busy} onChange={event=>{setBrowseView(event.target.value as 'groups'|'copies');setPage(0);}}><option value="groups" disabled={!!customCollectionId||typeFilter==='other'}>Grouped collection</option><option value="copies">Individual copies</option></select></div>

            {customCollectionId&&<><ChecklistProgress key={customCollectionId} collectionId={customCollectionId} refresh={refresh} locked={busy} addFigure={entryId=>beginFigure(entryId)} /><p className="hint">Checklist progress covers the whole collection. Search and storage filters affect the copies below.</p></>}
            <div className="browse-toolbar">
            <form className="search" onSubmit={search} aria-label="Search inventory">
              <label htmlFor="query">Find a copy</label>
              <div className="search-controls"><input id="query" type="search" maxLength={200} value={draftQuery} onChange={e => setDraftQuery(e.target.value)} placeholder="Title, artist, studio or barcode" disabled={busy} /><button type="submit" disabled={busy}>Search</button></div>
              {query && <button className="text-button" type="button" disabled={busy} onClick={() => { setDraftQuery(''); setQuery(''); setPage(0); }}>Clear search</button>}
            </form>
            <div className="storage-filter"><StorageFilter value={storageFilter} change={value=>{setStorageFilter(value);setPage(0);}} busy={busy} refresh={refresh} /></div>
            </div>
            {grouped?<GroupedCollection key={filters} type={typeFilter as ''|'record'|'comic'|'movie'} noun={typeFilter?types?.[typeFilter]?.grouping?.plural_label||'Groups':'Collection types'} filters={filters} refresh={refresh} busy={busy||!types} selected={selected} open={openCopy} chooseType={(value,customId)=>{setBrowseCollection(customId?'custom:'+customId:value);setPage(0);}}/>:<>
            <div role="status" className="result-status">{loading ? 'Loading copies…' : listError ? 'Inventory unavailable' : `${items.length} ${items.length === 1 ? 'copy' : 'copies'} on this page${customCollectionId?' · Custom collection':typeFilter ? ` · ${types?.[typeFilter]?.plural_label || typeFilter}` : ''}${query ? ` matching “${query}”` : ''}`}</div>
            {listError ? <p className="error" role="alert">{listError} Use Reload inventory to try again.</p>
              : loading ? <div className="loading-lines" aria-hidden="true"><span /><span /><span /></div>
              : items.length === 0 ? <div className="empty"><h3>{query || typeFilter || customCollectionId ? 'No matching copies' : page ? 'No more copies on this page' : 'Your first find starts here'}</h3><p>{typeFilter || customCollectionId ? 'Try another collection or choose All items. You can also clear the search.' : query ? 'Try a shorter phrase or clear the search. Search treats symbols as literal text.' : page ? 'Go back to the previous page or reload the inventory.' : 'Enter a title and save. You can add everything else later.'}</p></div>
              : <CollectionRows groupByType types={types} items={items} busy={busy} selected={selected} open={openCopy}/>}

            <nav className="pagination" aria-label="Inventory pages"><button disabled={busy || loading || page === 0} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {page + 1}</span><button disabled={busy || loading || !!listError || !more} onClick={() => setPage(value => value + 1)}>Next</button></nav>
            </>}

            </div>
          </section>
          <aside className="copy-inspector" hidden={!detailOpen} aria-label="Selected copy">
            <button type="button" className="text-button back-to-collection" disabled={busy} onClick={backToCollection}>Back to collection</button>
            {selected ? <CopyDetail key={selected} active={detailOpen} guard={detailGuard} copyId={selected} runSave={runSave} busy={busy} blocked={false} changed={changed} types={types} movieFields={settings?.movie_fields || ['media_format','studio','edition','notes']} comicFields={settings?.comic_fields || []} recordFields={settings?.record_fields || []} />
              : <div className="record-placeholder"><h2>Open a copy to edit it</h2><p>Choose a saved copy to edit its title, edition, photos and storage.</p></div>}
          </aside>
        </div>
        <div className="development"><strong>Synthetic collection trial</strong><span>Use made-up records and test photos. Owner sign-in is enabled. Production backups are not ready.</span></div>
      </main>
      <footer>Provisional intake, photos, manual identification, storage, and search. Production recovery and broader deployment hardening remain unfinished.</footer>
    </div>
  );
}
