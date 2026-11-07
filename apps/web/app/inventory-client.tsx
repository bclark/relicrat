'use client';

import ItemIntake,{type IntakeStart} from './item-intake';
import SignOut from './sign-out';
import CollectionManager from './collection-manager';
import CollectionFilter from './collection-filter';
import ChecklistProgress from './checklist-progress';
import Appearance from './appearance';
import CsvImport from './csv-import';
import ImportStorage from './import-storage';
import GroupedCollection from './grouped-collection';
import CollectionRows from './collection-rows';
import StorageFilter from './storage-filter';
import LocationDirectory from './location-directory';
import LocationEditor from './location-editor';
import {locationLink} from '../lib/location-link';

import { useCallback, useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react';
import { api, errorText, type CollectionSettings, type CollectionTypeId, type CollectionTypes, type InventoryCopy,type Location,type RunSave } from '../lib/inventory-client';
import CopyDetail from './copy-detail';

const PAGE = 20;
type Sort = ''|'recent'|'title'|'artist';
export default function InventoryClient({initialLocationId}: {initialLocationId?:string}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [settingsPanel, setSettingsPanel] = useState<'appearance' | 'collection' | null>(null);
  const [intakeVisible,setIntakeVisible]=useState(false);
  const [phone,setPhone]=useState(false);
  const [phoneHome,setPhoneHome]=useState(!initialLocationId);
  const [filtersOpen,setFiltersOpen]=useState(false);
  const phoneAdd=useRef<HTMLButtonElement>(null);
  const searchInput=useRef<HTMLInputElement>(null);
  const phoneFilters=useRef<HTMLButtonElement>(null);
  useEffect(()=>{
    const width=window.matchMedia('(max-width:759px)');
    const update=()=>setPhone(width.matches);
    update();
    width.addEventListener('change',update);
    return ()=>width.removeEventListener('change',update);
  },[]);
  const detailGuard=useRef<()=>boolean>(()=>true);
  const browseScroll=useRef(0);
  const [collectionName,setCollectionName]=useState('');
  const [detailOpen,setDetailOpen]=useState(false);
  const [view,setView]=useState<'list'|'bricks'>('list');
  const collectionHeading=useRef<HTMLHeadingElement>(null),intakeGuard=useRef<()=>boolean>(()=>true);
  const [intakeStart,setIntakeStart]=useState<IntakeStart>({target:'',scope:'',name:'All items',sequence:0});
  const [locationBrowse,setLocationBrowse]=useState<{path:Location[];unassigned?:boolean}|null>(null);
  const [locationEditor,setLocationEditor]=useState<'create'|'edit'|null>(null);
  const currentLocation=locationBrowse?.path.at(-1);
  const locationIndex=!!locationBrowse&&!currentLocation&&!locationBrowse.unassigned;
  const browseTitle=locationBrowse?(currentLocation?.name||(locationBrowse.unassigned?'Unassigned copies':'Locations')):collectionName||'Your collection';
  function openCopy(id:string){
    if(id!==selected&&!detailGuard.current())return;
    if(!intakeGuard.current())return;
    if(!detailOpen&&!intakeVisible)browseScroll.current=window.scrollY;
    if(!phone)setPhoneHome(false);
    else if(toolsPanel.current)toolsPanel.current.open=false;
    setIntakeVisible(false);
    setSelected(id);
    setDetailOpen(true);
    if(id===selected)requestAnimationFrame(()=>document.getElementById('record-title')?.focus());
  }
  function backToCollection(){
    setDetailOpen(false);
    requestAnimationFrame(()=>{
      const destination=phone&&phoneHome
        ? document.getElementById('collection-home-title')
        : document.getElementById(`copy-row-${selected}`)||collectionHeading.current;
      destination?.focus({preventScroll:true});
      window.scrollTo({top:browseScroll.current});
    });
  }
  function showCollections(){
    setPhoneHome(true);
    requestAnimationFrame(()=>{
      const heading=document.getElementById('collection-home-title');
      const choice=heading?.parentElement?.querySelector<HTMLButtonElement>('[data-collection="'+CSS.escape(browseCollection)+'"]');
      (choice||heading)?.focus({preventScroll:true});
      window.scrollTo({top:0});
      choice?.scrollIntoView({block:'nearest'});
    });
  }
  function startIntake(target=browseCollection,entryId?:string){if(!intakeGuard.current())return;if(!intakeVisible)browseScroll.current=window.scrollY;if(target&&target!==browseCollection){setBrowseCollection(target);setLocationBrowse(null);setImportBatchId('');setShowImportStorage(false);setPage(0);}setIntakeStart(old=>({target,scope:target,name:target===browseCollection?(target?browseTitle:'All items'):'collection',entryId,sequence:old.sequence+1}));setIntakeVisible(true);setDetailOpen(false);}
  function closeIntake(){setIntakeVisible(false);requestAnimationFrame(()=>{(phone&&phoneHome?phoneAdd.current:collectionHeading.current)?.focus({preventScroll:true});window.scrollTo({top:browseScroll.current});});}
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
    const control = phone ? menuButton.current : document.getElementById(`${settingsPanel}-control`);
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
  const [browseView,setBrowseView]=useState<'groups'|'copies'|null>(null);
  const [{id:storageFilter,label:storageLabel},setStorage]=useState({id:'',label:''});
  const [sort,setSort]=useState<Sort>('');
  const [browseCollection,setBrowseCollection]=useState('');
  const [importBatchId,setImportBatchId]=useState('');
  const [showImportStorage,setShowImportStorage]=useState(false);
  const customCollectionId=browseCollection.startsWith('custom:')?browseCollection.slice(7):'';
  const typeFilter:CollectionTypeId|''=customCollectionId?'':browseCollection as CollectionTypeId|'';
  useEffect(()=>{const c=new AbortController();setCollectionName(customCollectionId?'Custom collection':typeFilter?types?.[typeFilter]?.plural_label||'Selected collection':'Your collection');if(customCollectionId)api<{name:string}>(`custom-collections/${customCollectionId}`,{signal:c.signal}).then(v=>{if(!c.signal.aborted)setCollectionName(v.name);}).catch(()=>{});return()=>c.abort();},[browseCollection,types]);
  function beginFigure(entryId?:string){startIntake(browseCollection,entryId);}
  function chooseCollection(value:string,batchId=''){
    if(busy)return;
    if(batchId!==importBatchId){setLoading(true);setPage(0);}
    if(locationBrowse)setLoading(true);
    setLocationBrowse(null);
    setLocationEditor(null);
    setImportBatchId(batchId);
    setShowImportStorage(false);
    if(value!==browseCollection||(phone&&phoneHome))setLoading(true);
    setIntakeVisible(false);setBrowseCollection(value);setDetailOpen(false);setPhoneHome(false);
    if(value!=='record'&&sort==='artist')setSort('');
    if(value!==browseCollection||!phone){
      setPage(0);
      if(phone){setDraftQuery('');setQuery('');setStorage({id:'',label:''});setBrowseView(null);setFiltersOpen(false);}
    }
    if(phone&&toolsPanel.current)toolsPanel.current.open=false;
    if(phone)requestAnimationFrame(()=>{
      collectionHeading.current?.focus({preventScroll:true});
      window.scrollTo({top:0});
    });
  }
  function browseLocations(path:Location[]=[],unassigned=false){
    if(busy)return;
    setLocationBrowse({path,unassigned});
    setLocationEditor(null);
    setBrowseCollection('');
    setImportBatchId('');
    setShowImportStorage(false);
    setIntakeVisible(false);
    setDetailOpen(false);
    setPhoneHome(false);
    setDraftQuery('');setQuery('');setStorage({id:'',label:''});setSort('');setPage(0);setFiltersOpen(false);
    if(path.length||unassigned){setLoading(true);changed();}
    if(toolsPanel.current)toolsPanel.current.open=false;
    requestAnimationFrame(()=>{
      collectionHeading.current?.focus({preventScroll:true});
      window.scrollTo({top:0});
    });
  }
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

  const [openingLocation,setOpeningLocation]=useState(!!initialLocationId);
  const [locationError,setLocationError]=useState('');
  useEffect(()=>{
    if(!initialLocationId)return;
    const controller=new AbortController();
    async function openLinkedLocation(target:string){
      const path:Location[]=[];
      const visited=new Set<string>();
      let id:string|null=target;
      while(id){
        if(visited.has(id))throw new Error('This location has an invalid storage path.');
        visited.add(id);
        const place:Location=await api<Location>(`storage-locations/${id}`,{signal:controller.signal});
        path.unshift(place);
        id=place.parent_id;
      }
      if(!controller.signal.aborted){
        setLocationBrowse({path});
        requestAnimationFrame(()=>collectionHeading.current?.focus({preventScroll:true}));
      }
    }
    openLinkedLocation(initialLocationId)
      .catch(problem=>{if(!controller.signal.aborted)setLocationError(errorText(problem));})
      .finally(()=>{if(!controller.signal.aborted)setOpeningLocation(false);});
    return()=>controller.abort();
  },[initialLocationId]);

  const grouped=!locationBrowse && !importBatchId && !customCollectionId && (browseView??(phone?'copies':'groups'))==='groups' && (!typeFilter || !!types?.[typeFilter]?.grouping);
  const activeSort=sort==='artist'&&typeFilter!=='record'?'':sort;
  const titleSort=typeFilter==='comic'?'Series and issue':'Title A–Z';
  const sortLabel=activeSort==='title'?titleSort:activeSort==='artist'?'Artist A–Z':activeSort==='recent'?'Recently added':'';
  const copySort=activeSort?`&sort=${activeSort}`:'';
  const effectiveStorage=locationBrowse?(currentLocation?.id||(locationBrowse.unassigned?'unassigned':'')):storageFilter;
  const filters=`&q=${encodeURIComponent(query)}${importBatchId?`&import_batch_id=${importBatchId}`:''}${customCollectionId?`&custom_collection_id=${encodeURIComponent(customCollectionId)}`:typeFilter?`&collection_type=${typeFilter}${typeFilter==='other'?'&exclude_custom=true':''}`:''}${effectiveStorage==='unassigned'?'&unassigned=true':effectiveStorage?`&storage_location_id=${effectiveStorage}`:''}`;
  useEffect(() => {
    if(openingLocation||locationError||grouped||locationIndex||(phone&&phoneHome)){setLoading(false);return;}
    const controller = new AbortController();
    setLoading(true); setListError('');
    api<InventoryCopy[]>(`inventory?limit=${PAGE + 1}&offset=${page * PAGE}${filters}${copySort}`, { signal: controller.signal })
      .then(result => {
        if (controller.signal.aborted) return;
        setItems(result.slice(0, PAGE)); setMore(result.length > PAGE);
      })
      .catch(error => { if (!controller.signal.aborted) setListError(errorText(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [filters, copySort, page, refresh, grouped, locationIndex, phone, phoneHome, openingLocation, locationError]);

  function reloadInventory(){changed();}
  function search(event: FormEvent) {
    event.preventDefault(); setQuery(draftQuery.trim()); setPage(0); changed();
  }
  const showingPhoneHome=phoneHome&&!intakeVisible&&!detailOpen;
  const filterCount=Number(!locationBrowse&&!!storageFilter)+Number(grouped)+Number(!grouped&&!!activeSort);
  const viewControls=<div className="view-controls" role="group" aria-label="Collection view"><button type="button" className="quiet" aria-pressed={view==='list'} onClick={()=>setView('list')}>List</button><button type="button" className="quiet" aria-pressed={view==='bricks'} onClick={()=>setView('bricks')}>Covers</button></div>;
  return (
    <div className="themed-app collection-journey" style={appearanceStyles} onClickCapture={event=>{const target=(event.target as HTMLElement).closest('a.brand,button');if((target?.matches('a.brand')||target?.textContent==='Sign out')&&(!detailGuard.current()||!managementGuard.current())){event.preventDefault();event.stopPropagation();}}}>
      <a className="skip-link" href={intakeVisible?"#add-find":detailOpen?"#record-title":phone&&showingPhoneHome?"#collection-home-title":"#collection-title"}>Skip to main content</a>
      <header className="masthead">
        <a className="brand" href="/">RelicRat</a><span className="brand-tagline">Your collection, one copy at a time.</span>
        <div className="account-nav" ref={accountNav} onKeyDown={event => {
          if (event.key === 'Escape' && menuOpen) { setMenuOpen(false); menuButton.current?.focus(); }
        }} onBlur={event => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setMenuOpen(false);
        }}>
          {settingsPanel!=='collection'&&!detailOpen&&!intakeVisible&&<button className="phone-add quiet" type="button" aria-label="Add an item" ref={phoneAdd} disabled={busy} onClick={()=>startIntake(phoneHome?'':browseCollection)}>+ Add</button>}
          <button className="menu-toggle quiet" ref={menuButton} type="button" aria-expanded={menuOpen} aria-controls="account-actions" onClick={() => setMenuOpen(value => !value)}>Menu</button>
          <div id="account-actions" className="account-actions" data-open={menuOpen}>
            <button id="appearance-control" className="quiet" type="button" aria-expanded={settingsPanel === 'appearance'} aria-controls="appearance-editor" onClick={() => toggleSettings('appearance')}>{settingsPanel === 'appearance' ? 'Close appearance' : 'Appearance'}</button>
            {<button id="collection-control" className="quiet" type="button" disabled={busy} aria-expanded={settingsPanel === 'collection'} aria-controls="collection-management" onClick={() => toggleSettings('collection')}>Manage collections</button>}
            <button type="button" className="phone-imports quiet" onClick={()=>{
              setSettingsPanel(null);setMenuOpen(false);
              if(toolsPanel.current)toolsPanel.current.open=true;
              requestAnimationFrame(()=>toolsPanel.current?.querySelector('summary')?.focus());
            }}>Collection tools and imports</button>
            <SignOut />
          </div>
        </div>
      </header>
      <main className="collection-main">
        <Appearance applied={setAppearanceStyles} open={settingsPanel === 'appearance'} />
        <CollectionManager open={settingsPanel==='collection'} close={closeSettings} guard={managementGuard} types={types} settings={settings} runSave={runSave} busy={busy} saved={setSettings} changed={()=>{changed();setCollectionVersion(v=>v+1);}} browse={value=>{chooseCollection(value);setSettingsPanel(null);}}/>
        {settingsError && <p className="error" role="alert">{settingsError} Collection preferences are unavailable. <button disabled={busy} onClick={()=>setSettingsVersion(value=>value+1)}>Reload settings</button> <button disabled={busy} onClick={()=>{if(!detailGuard.current()||!intakeGuard.current())return;setTypes(old=>old||({other:{schema_version:1,id:'other',label:'Other',plural_label:'Other finds',title:{key:'title',label:'Title',max_length:500,placeholder:'',suggested:true},fields:[{key:'notes',label:'Notes',max_length:10000,placeholder:'',suggested:true}],entry_order:['title','notes'],grouping:null}} as CollectionTypes));setSettings({status:'skipped',default_type:'other',records_enabled:false,record_fields:[],revision:0});setBrowseCollection('other');setLocationBrowse(null);setImportBatchId('');setShowImportStorage(false);setIntakeStart(old=>({target:'other',scope:'other',name:'Other finds',sequence:old.sequence+1}));setIntakeVisible(true);setDetailOpen(false);}}>Use generic entry</button></p>}
        {!settings && !settingsError && <p role="status">Loading collection settings…</p>}
        <details className="collection-tools" ref={toolsPanel} hidden={settingsPanel==='collection'}><summary>Collection tools and imports</summary><CsvImport runSave={runSave} locked={busy} changed={changed} openCopy={openCopy} browse={(type,batchId)=>{
          if(toolsPanel.current)toolsPanel.current.open=false;
          setDraftQuery('');setQuery('');setStorage({id:'',label:''});setSort('');setPage(0);chooseCollection(type,batchId);
          requestAnimationFrame(()=>collectionHeading.current?.focus());
        }}/></details>
        {openingLocation&&<p role="status">Opening storage location…</p>}
        {locationError&&<p role="alert" className="error">Could not open this location. {locationError} <a href={locationLink(initialLocationId)}>Try again</a> <a href="/">Open RelicRat</a></p>}
        <div hidden={settingsPanel==='collection'||openingLocation||!!locationError} data-phone-home={showingPhoneHome} className={`workspace${detailOpen ? ' detail-open' : ''}${selected ? ' has-selection' : ''}`}>
          <aside className="collection-sidebar"><CollectionFilter browseLocations={()=>browseLocations()} homeHeadingId={phone?"collection-home-title":undefined} value={locationBrowse?'locations':browseCollection} change={chooseCollection} types={types} busy={busy} refresh={collectionVersion} /></aside>
          <ItemIntake start={intakeStart} visible={intakeVisible} guard={intakeGuard} close={closeIntake} openCopy={openCopy} types={types} settings={settings} busy={busy} runSave={runSave} saved={()=>changed()}/>
          <section className="collection" hidden={intakeVisible} aria-labelledby="collection-title">
            <button type="button" className="phone-back text-button" disabled={busy} onClick={showCollections}>Back to collections</button>
            <div className="section-heading collection-heading"><h1 id="collection-title" tabIndex={-1} ref={collectionHeading}>{browseTitle}</h1>{!phone&&!locationIndex&&viewControls}</div>
            {locationBrowse&&<>
              {!locationIndex&&<button className="text-button" type="button" disabled={busy} onClick={()=>browseLocations(locationBrowse.path.slice(0,-1))}>
                {locationBrowse.path.length>1?`Back to ${locationBrowse.path.at(-2)?.name}`:'All locations'}
              </button>}
              {locationIndex&&<button className="text-button" type="button" disabled={busy} onClick={()=>browseLocations([],true)}>Unassigned copies</button>}
              {!locationBrowse.unassigned&&<div className="form-actions">
                <button type="button" disabled={busy} onClick={()=>setLocationEditor('create')}>{currentLocation?'Add nested location':'Add location'}</button>
                {currentLocation&&<>
                  <button type="button" disabled={busy} onClick={()=>setLocationEditor('edit')}>Rename or move location</button>
                  <a href={`/location-label/${currentLocation.id}`}>Print QR label</a>
                </>}
              </div>}
              {locationEditor&&<LocationEditor key={locationEditor} path={locationEditor==='edit'?locationBrowse.path.slice(0,-1):locationBrowse.path}
                location={locationEditor==='edit'?currentLocation:undefined} busy={busy} runSave={runSave}
                onSaved={path=>browseLocations(path)} onCancel={()=>setLocationEditor(null)}/>}
              {!locationBrowse.unassigned&&<LocationDirectory key={currentLocation?.id||'root'} parentId={currentLocation?.id} open={place=>browseLocations([...locationBrowse.path,place])} busy={busy} refresh={refresh}/>}
              {!locationIndex&&<p className="hint">{locationBrowse.unassigned?'Copies without a physical location. Open a copy to assign one.':'Copies stored directly here. Open a nested location to see its copies.'}</p>}
            </>}
            {!locationIndex&&<>
            <div className="collection-actions"><button className="primary" type="button" disabled={busy} aria-expanded={intakeVisible} onClick={()=>startIntake()}>Add an item</button><button className="text-button" disabled={busy||loading} onClick={reloadInventory}>Reload inventory</button></div>
            {importBatchId&&<div className="browse-active" aria-label="Import scope">
              <span>Showing copies from this import</span>
              <button className="text-button" type="button" disabled={busy} onClick={()=>{chooseCollection(browseCollection);requestAnimationFrame(()=>collectionHeading.current?.focus());}}>View full collection</button>
              {typeFilter==='comic'&&<button className="text-button" type="button" disabled={busy} aria-expanded={showImportStorage} onClick={()=>setShowImportStorage(open=>!open)}>{showImportStorage?'Close storage mapping':'Map imported storage boxes'}</button>}
            </div>}
            {importBatchId&&showImportStorage&&<ImportStorage key={importBatchId} batchId={importBatchId} locked={busy} runSave={runSave} changed={changed}/>}
            <div className={`inventory-results ${view}`}>
            <div className="browse-toolbar">
            <form className="search" onSubmit={search} aria-label="Search inventory">
              <label htmlFor="query">Find a copy</label>
              <div className="search-controls"><input id="query" ref={searchInput} type="search" maxLength={200} value={draftQuery} onChange={e => setDraftQuery(e.target.value)} placeholder={phone?"Find items":"Title, artist, studio or barcode"} disabled={busy} /><button type="submit" disabled={busy}>Search</button></div>
            </form>
            {phone&&viewControls}
            <button type="button" className="phone-filters quiet" ref={phoneFilters} aria-expanded={filtersOpen} aria-controls="browse-options" onClick={()=>setFiltersOpen(open=>!open)}>Filters{filterCount?` (${filterCount})`:''}</button>
            <div id="browse-options" className="browse-options" data-expanded={filtersOpen}>
              {!locationBrowse&&<div className="storage-filter"><StorageFilter value={storageFilter} change={(id,label)=>{setStorage({id,label});setPage(0);}} busy={busy} refresh={refresh} /></div>}
              <div className="browse-mode"><label htmlFor="collection-browse-view">Browse view</label><select id="collection-browse-view" value={grouped?'groups':'copies'} disabled={busy} onChange={event=>{setBrowseView(event.target.value as 'groups'|'copies');setPage(0);}}><option value="groups" disabled={!!locationBrowse||!!importBatchId||!!customCollectionId||!!typeFilter&&!types?.[typeFilter]?.grouping}>Grouped collection</option><option value="copies">Individual copies</option></select></div>
              <div className="browse-sort">
                <label htmlFor="copy-sort">Sort copies</label>
                <select id="copy-sort" value={grouped?'':activeSort} disabled={busy} onChange={event=>{
                  const order=event.target.value as Sort;
                  if(grouped||order!==activeSort){setLoading(true);setSort(order);setBrowseView('copies');setPage(0);}
                }}>
                  <option value="">{grouped?'Sort individual copies':'Default order'}</option>
                  <option value="recent">Recently added</option>
                  <option value="title">{titleSort}</option>
                  {typeFilter==='record'&&<option value="artist">Artist A–Z</option>}
                </select>
              </div>
            </div>
            </div>
            {(query||(!locationBrowse&&storageFilter)||(!grouped&&activeSort))&&<div className="browse-active" aria-label="Active browse options">
              {query&&<div><span>Search: <strong>{query}</strong></span><button className="text-button" type="button" disabled={busy} onClick={()=>{setDraftQuery('');setQuery('');setPage(0);searchInput.current?.focus({preventScroll:true});}}>Clear search</button></div>}
              {!locationBrowse&&storageFilter&&<div><span>Storage: <strong>{storageLabel}</strong></span><button className="text-button" type="button" disabled={busy} onClick={()=>{setStorage({id:'',label:''});setPage(0);
                (phone&&!filtersOpen?phoneFilters.current:document.getElementById('collection-storage-filter'))?.focus({preventScroll:true});
              }}>Clear storage filter</button></div>}
              {!grouped&&activeSort&&<span>Sort: <strong>{sortLabel}</strong></span>}
            </div>}
            {grouped?<GroupedCollection key={filters} type={typeFilter as ''|'record'|'comic'|'movie'} noun={typeFilter?types?.[typeFilter]?.grouping?.plural_label||'Groups':'Collection types'} filters={filters} refresh={refresh} busy={busy||!types} selected={selected} open={openCopy} retry={reloadInventory} chooseType={(value,customId)=>chooseCollection(customId?'custom:'+customId:value)}/>:<>
            <div role="status" className="result-status">{loading ? 'Loading copies…' : listError ? 'Inventory unavailable' : `${items.length} ${items.length === 1 ? 'copy' : 'copies'} on this page${customCollectionId?' · Custom collection':typeFilter ? ` · ${types?.[typeFilter]?.plural_label || typeFilter}` : ''}`}</div>
            {listError ? <p className="error" role="alert">{listError} <button type="button" className="text-button" onClick={reloadInventory}>Try again</button></p>
              : loading ? <div className="loading-lines" aria-hidden="true"><span /><span /><span /></div>
              : items.length === 0 ? <div className="empty"><h3>{query || effectiveStorage || typeFilter || customCollectionId ? 'No matching copies' : page ? 'No more copies on this page' : 'Your first find starts here'}</h3><p>{query ? 'Clear the search to see more copies.' : locationBrowse ? 'There are no copies here.' : storageFilter ? 'Clear the storage filter to see more copies.' : typeFilter || customCollectionId ? importBatchId ? 'There are no active copies from this import.' : 'There are no saved copies in this collection yet.' : page ? 'Go back to the previous page or reload the inventory.' : 'Enter a title and save. You can add everything else later.'}</p></div>
              : <CollectionRows groupByType={!activeSort&&(!phone||!typeFilter&&!customCollectionId)} types={types} items={items} busy={busy} selected={selected} open={openCopy}/>}

            <nav className="pagination" data-single-page={page===0&&!more} aria-label="Inventory pages"><button disabled={busy || loading || page === 0} onClick={() => {setLoading(true);setPage(value => value - 1);}}>Previous</button><span>Page {page + 1}</span><button disabled={busy || loading || !!listError || !more} onClick={() => {setLoading(true);setPage(value => value + 1);}}>Next</button></nav>
            </>}
            {customCollectionId&&<div className="browse-checklist"><ChecklistProgress key={customCollectionId} collectionId={customCollectionId} refresh={refresh} locked={busy} addFigure={entryId=>beginFigure(entryId)} /><p className="hint">Checklist progress covers the whole collection. Search and storage filters affect the saved copies.</p></div>}
            </div>
            </>}
          </section>
          <aside className="copy-inspector" hidden={!detailOpen} aria-label="Selected copy">
            <button type="button" className="text-button back-to-collection" disabled={busy} onClick={backToCollection}>{phone&&phoneHome?'Back to collections':'Back to collection'}</button>
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
