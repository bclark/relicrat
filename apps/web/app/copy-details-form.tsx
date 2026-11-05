'use client';

import { Fragment, useEffect, useLayoutEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, errorText, jsonSave, type InventoryCopy, type RecordField, type ComicField, type MovieField, type CollectionTypeId, type CollectionTypes, type RunSave } from '../lib/inventory-client';
import CustomField,{normalizeCustomValues,replaceCustomValue,customValueText,type CustomValues} from './custom-field';
import type {SavedCollection} from './custom-collections';
import ObservationInput from './observation-input';
import BarcodeInput from './barcode-input';
import type {BarcodeReading,CatalogCover} from '../lib/inventory-client';
import { Pages, usePage } from './identification';

type Props = { active?:boolean; editing?:boolean; cancel?:()=>void; stateChanged?:(dirty:boolean,uncertain:boolean)=>void; movieFields: MovieField[]; types: CollectionTypes | null; fields: RecordField[]; comicFields: ComicField[]; copy: InventoryCopy; runSave: RunSave; locked: boolean; saved: (copy: InventoryCopy, artwork?:boolean) => void; failed: (error: unknown) => void };
type Edit = { before_movie_details?:{media_format?:string;studio?:string}|null;after_movie_details?:{media_format?:string;studio?:string}|null; before_barcode?:Partial<BarcodeReading>|null;after_barcode?:Partial<BarcodeReading>|null; id: string; before_custom_details?:CustomValues|null;after_custom_details?:CustomValues|null;before_title: string | null; after_title: string | null; before_edition_label: string | null; after_edition_label: string | null; before_collection_type: string | null; after_collection_type: string | null; before_comic_details: {issue_number?:string;publisher?:string}|null; after_comic_details: {issue_number?:string;publisher?:string}|null; before_record_details: {artist?:string;format?:string}|null; after_record_details: {artist?:string;format?:string}|null; after_revision: number; created_at: string };

export default function CopyDetailsForm({ types, fields, comicFields, copy, runSave, locked, saved, failed, movieFields, editing=true, active=true, cancel, stateChanged }: Props) {
  const [customCollection,setCustomCollection]=useState<SavedCollection|null>(null);
  const [customValues,setCustomValues]=useState<CustomValues>({});

  const [catalogCover,setCatalogCover]=useState<CatalogCover|null>(null);
  const titleInput=useRef<HTMLInputElement>(null);
  const [recordType, setRecordType] = useState(copy.collection_type);
  const [barcode,setBarcode]=useState<BarcodeReading|null>(copy.barcode?.value ? copy.barcode as BarcodeReading : null);
  const [artist, setArtist] = useState(copy.record_details.artist || '');
  const [format, setFormat] = useState(copy.record_details.format || '');
  const [mediaFormat,setMediaFormat] = useState(copy.movie_details?.media_format || '');
  const [studio,setStudio] = useState(copy.movie_details?.studio || '');
  const [issueNumber, setIssueNumber] = useState(copy.comic_details?.issue_number || '');
  const [publisher, setPublisher] = useState(copy.comic_details?.publisher || '');
  const [title, setTitle] = useState(copy.title || '');
  const [edition, setEdition] = useState('');
  const [initialEdition, setInitialEdition] = useState('');
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [needsReview, setNeedsReview] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [definitionRefresh,setDefinitionRefresh]=useState(0);
  useEffect(()=>{setCustomValues(copy.custom_details||{});},[copy.id,copy.details_revision,refresh]);
  useEffect(()=>{const c=new AbortController();setCustomCollection(null);if(copy.custom_collection_id)api<SavedCollection>(`custom-collections/${copy.custom_collection_id}`,{signal:c.signal}).then(v=>{if(!c.signal.aborted)setCustomCollection(v);}).catch(e=>{if(!c.signal.aborted)failed(e);});return()=>c.abort();},[copy.id,copy.details_revision,copy.custom_collection_id,definitionRefresh,refresh]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [barcodeOpen,setBarcodeOpen]=useState(false);
  const [page, setPage] = useState(0);
  const history = usePage<Edit>(historyOpen ? `inventory/${copy.id}/detail-history` : null, page, String(copy.details_revision));

  useEffect(() => {
    const controller = new AbortController();
    setCatalogCover(null);setBarcode(copy.barcode?.value ? copy.barcode as BarcodeReading : null);setReady(false); setError(''); setNeedsReview(false); setTitle(copy.title || ''); setRecordType(copy.collection_type); setIssueNumber(copy.comic_details?.issue_number || '');setPublisher(copy.comic_details?.publisher || '');setArtist(copy.record_details.artist || ''); setFormat(copy.record_details.format || '');setMediaFormat(copy.movie_details?.media_format || '');setStudio(copy.movie_details?.studio || '');
    const load = copy.edition_label === null && copy.catalog_item_id && copy.release_id
      ? api<{ name: string | null }>(`catalog/items/${copy.catalog_item_id}/releases/${copy.release_id}`, { signal: controller.signal }).then(release => release.name || '')
      : Promise.resolve(copy.edition_label || '');
    load.then(value => {
      if (!controller.signal.aborted) { setEdition(value); setInitialEdition(value); setReady(true); }
    }).catch(problem => { if (!controller.signal.aborted) setError(errorText(problem)); });
    return () => controller.abort();
  }, [copy.id, copy.title, copy.edition_label, copy.details_revision, copy.catalog_item_id, copy.release_id, copy.identification_revision, copy.collection_type, copy.record_details.artist, copy.record_details.format, copy.comic_details?.issue_number, copy.comic_details?.publisher, copy.movie_details?.media_format, copy.movie_details?.studio, copy.barcode?.value, copy.barcode?.format, copy.barcode?.supplement, refresh]);

  async function submit(event: FormEvent) {
    event.preventDefault(); if (locked || !ready || (copy.custom_collection_id&&!customCollection)) return;
    try {
      await runSave(async () => {
        setError(''); setNotice('Saving copy details…');
        // An unchanged matched edition keeps following the existing catalog link.
        // A changed label is an explicit personal description, including blank.
        const label = edition.trim() === initialEdition ? copy.edition_label : edition.trim();
        const result = await api<InventoryCopy>(`inventory/${copy.id}/details`, jsonSave({ catalog_cover:catalogCover?{provider:catalogCover.provider,candidate_id:catalogCover.candidate_id}:null, barcode, title: title.trim() || null, edition_label: label, collection_type: recordType, record_details:{artist:artist.trim() || null,format:format.trim() || null},movie_details:{media_format:mediaFormat.trim() || null,studio:studio.trim() || null},comic_details:{issue_number:issueNumber.trim() || null,publisher:publisher.trim() || null},
          ...(copy.custom_collection_id?{custom_details:normalizeCustomValues(customValues),expected_type_revision:customCollection?.type_revision}:{}), expected_details_revision: copy.details_revision, expected_identification_revision: copy.identification_revision }));
        saved(result,!!catalogCover);setCatalogCover(null); setNotice('');
      });
    } catch (problem) { setNotice(''); setNeedsReview(problem instanceof ApiError && (problem.uncertain || problem.status === 409)); if(problem instanceof ApiError&&problem.status===412)setError(errorText(problem)+' Reload field controls and review your preserved draft.');else failed(problem); }
  }
  const barcodeChanged=(barcode?.value || '')!==(copy.barcode?.value || '') || (barcode?.format || '')!==(copy.barcode?.format || '') || (barcode?.supplement || '')!==(copy.barcode?.supplement || '');
  const customDirty=JSON.stringify(normalizeCustomValues(customValues))!==JSON.stringify(normalizeCustomValues(copy.custom_details||{}));
  const dirty = customDirty || !!catalogCover || barcodeChanged || title.trim() !== (copy.title || '') || edition.trim() !== initialEdition || recordType!==copy.collection_type || artist.trim()!==(copy.record_details.artist || '') || format.trim()!==(copy.record_details.format || '') || issueNumber.trim()!==(copy.comic_details?.issue_number || '') || publisher.trim()!==(copy.comic_details?.publisher || '') || mediaFormat.trim()!==(copy.movie_details?.media_format || '') || studio.trim()!==(copy.movie_details?.studio || '');
  useLayoutEffect(()=>{stateChanged?.(dirty,needsReview);},[dirty,needsReview,stateChanged]);
  const values:Record<string,string>={artist,format,media_format:mediaFormat,studio,issue_number:issueNumber,publisher};
  const setters:Record<string,(value:string)=>void>={artist:setArtist,format:setFormat,media_format:setMediaFormat,studio:setStudio,issue_number:setIssueNumber,publisher:setPublisher};
  const observed={...(copy.record_details || {}),...(copy.comic_details || {}),...(copy.movie_details || {})} as Record<string,string>;
  const activeFields=recordType==='movie' ? movieFields : recordType==='record' ? fields : recordType==='comic' ? comicFields : [];
  const order=(types?.[recordType]?.entry_order || ['title','artist','format','edition']).filter(key=>key!=='notes');
  if(!order.includes('edition')) order.push('edition');
  const retained=['artist','format','issue_number','publisher','media_format','studio'].filter(key=>!order.includes(key as never) && (values[key] || observed[key]));
  return <div className="copy-details-form">
    {!editing&&!customCollection&&<dl className="copy-summary" aria-label="Saved item details">{Object.entries(observed).filter(([,value])=>value).map(([key,value])=><Fragment key={key}><dt>{Object.values(types||{}).flatMap(t=>t.fields).find(f=>f.key===key)?.label||key}</dt><dd>{value}</dd></Fragment>)}<dt>Edition</dt><dd>{ready?initialEdition||'Not entered':'Loading saved edition…'}</dd></dl>}
    {!editing&&customCollection&&<dl className="copy-summary" aria-label="Collection details">{customCollection.proposal.type_definition.optional_fields.map(field=><Fragment key={field.id}><dt>{field.label}</dt><dd>{customValueText(copy.custom_details?.[field.id])}</dd></Fragment>)}</dl>}
    <div hidden={!editing}>{copy.custom_collection_id&&<p>{customCollection?.name||'Custom collection'} — membership is retained.</p>}
    {copy.custom_collection_id&&<button type="button" disabled={locked} onClick={()=>setDefinitionRefresh(v=>v+1)}>Reload field controls</button>}
    <form aria-label="Edit copy details" onSubmit={submit}><fieldset disabled={locked || !ready || (!!copy.custom_collection_id&&!customCollection)}>
      {[...order,...retained].map(key=>{
        if(key==='title')return <Fragment key={key}><label htmlFor="copy-title">{customCollection?.proposal.type_definition.title.label || types?.[recordType]?.title.label || 'Title'}</label><input ref={titleInput} id="copy-title" maxLength={customCollection?.proposal.type_definition.title.max_length||500} value={title} onChange={event=>{setTitle(event.target.value);setNotice('');}} /></Fragment>;
        if(key==='edition')return (recordType==='other' || activeFields.includes('edition') || edition || copy.edition_label!==null || copy.release_id) ? <Fragment key={key}><label htmlFor="copy-edition">{types?.[recordType]?.fields.find(field=>field.key==='edition')?.label || 'Edition'}</label><input id="copy-edition" maxLength={500} value={edition} onChange={event=>{setEdition(event.target.value);setNotice('');}} aria-describedby="copy-edition-help" /><p className="hint" id="copy-edition-help">Optional. Describe this physical copy’s edition or variant.</p></Fragment> : null;
        if(!activeFields.includes(key as never) && !values[key] && !observed[key])return null;
        const field=types?.[recordType]?.fields.find(field=>field.key===key) || Object.values(types || {}).flatMap(type=>type.fields).find(field=>field.key===key);
        return field ? <Fragment key={key}><label htmlFor={`copy-${key}`}>{field.label} (optional)</label><ObservationInput key={`${key}-${copy.id}-${copy.details_revision}`} id={`copy-${key}`} field={field} value={values[key]} change={value=>{setters[key](value);setNotice('');}} /></Fragment> : null;
      })}
      {customCollection?.proposal.type_definition.optional_fields.map(f=><CustomField key={f.id} field={f} value={customValues[f.id]} change={value=>setCustomValues(v=>replaceCustomValue(v,f.id,value))} />)}
      {!copy.custom_collection_id&&<>
      <details className="change-collection-type"><summary>Change collection type</summary><label htmlFor="copy-type">Collection type</label><select disabled={!!copy.custom_collection_id} id="copy-type" value={recordType} onChange={event=>{setCatalogCover(null);setRecordType(event.target.value as CollectionTypeId);setNotice('');}}>{copy.custom_collection_id?<option value="other">{customCollection?.proposal.type_definition.label||'Custom collection'}</option>:types ? Object.values(types).map(type=><option key={type.id} value={type.id}>{type.label}</option>) : <option value={recordType}>{recordType}</option>}</select>
      {recordType!==copy.collection_type && <p className="hint">Changing type keeps this physical copy and its saved details. Save changes to apply it.</p>}</details>
      </>}
      <details onToggle={event=>setBarcodeOpen(event.currentTarget.open)}><summary>Barcode (optional)</summary>{barcodeOpen&&<BarcodeInput saved={!barcodeChanged} key={`${copy.id}-${copy.details_revision}-${recordType}-${JSON.stringify(types?.[recordType]?.lookup)}`} definition={types?.[recordType]} values={{title,artist,format,media_format:mediaFormat,studio,edition,issue_number:issueNumber,publisher}} cover={catalogCover} removeCover={()=>setCatalogCover(null)} apply={(fields,cover)=>{if(cover)setCatalogCover(cover);const setters:Record<string,(value:string)=>void>={title:setTitle,artist:setArtist,format:setFormat,media_format:setMediaFormat,studio:setStudio,edition:setEdition,issue_number:setIssueNumber,publisher:setPublisher};for(const [key,value] of Object.entries(fields))setters[key]?.(value);setNotice('');titleInput.current?.focus();}} value={barcode} change={value=>{setCatalogCover(null);setBarcode(value);setNotice('');}} formats={types?.[recordType]?.barcode_formats || []} locked={locked || !ready || !editing || !active}/>}</details>
      {recordType!=='other' && <p className="hint">Saved details stay editable even when hidden from new entry forms.</p>}
      {copy.edition_label !== null && copy.release_id && <p className="hint">Your edition label is used for this copy. Shared catalog information is under Advanced.</p>}
      <div className="edit-actions"><button className="primary" type="submit" disabled={!dirty||needsReview}>Save changes</button>{cancel&&<button type="button" disabled={needsReview} onClick={()=>{if(!dirty||window.confirm('Discard the unsaved details for this copy?')){setRefresh(v=>v+1);cancel();}}}>Cancel</button>}</div>
    </fieldset></form>
    {!ready && !error && <p role="status">Loading saved edition…</p>}
    {error && <p className="error" role="alert">{error} {!ready&&<button type="button" className="quiet" disabled={locked} onClick={() => setRefresh(value => value + 1)}>Reload edition</button>}</p>}
    {dirty && ready && !needsReview && <p className="hint">Unsaved changes to this copy.</p>}
    <p className="notice" role="status">{notice}</p>
    </div><details hidden={editing} className="movement-history" onToggle={event => setHistoryOpen(event.currentTarget.open)}><summary>Copy edit history</summary>
      <p className="hint">Oldest first. Earlier titles and edition labels are kept.</p>
      {history.busy ? <p role="status">Loading copy edit history…</p> : history.error ? <p role="alert" className="error">{history.error} Use Reload copy.</p> : history.items.length ? <ol>{history.items.map(edit => <li key={edit.id}>
        <span>{edit.before_title || 'No title'} to {edit.after_title || 'No title'}</span>
        {edit.before_edition_label !== edit.after_edition_label && <small>Edition label: {edit.before_edition_label || 'Not entered'} to {edit.after_edition_label || 'Not entered'}</small>}
        {edit.before_collection_type!==edit.after_collection_type && <small>Type: {edit.before_collection_type ? types?.[edit.before_collection_type as CollectionTypeId]?.label || edit.before_collection_type : 'Other'} to {edit.after_collection_type ? types?.[edit.after_collection_type as CollectionTypeId]?.label || edit.after_collection_type : 'Other'}</small>}
        {(['artist','format'] as const).filter(key=>edit.before_record_details?.[key]!==edit.after_record_details?.[key]).map(key=><small key={key}>{key==='artist' ? 'Artist' : 'Format'}: {edit.before_record_details?.[key] || 'Not entered'} to {edit.after_record_details?.[key] || 'Not entered'}</small>)}
        {(['issue_number','publisher'] as const).filter(key=>edit.before_comic_details?.[key]!==edit.after_comic_details?.[key]).map(key=><small key={key}>{key==='publisher' ? 'Publisher' : 'Issue number'}: {edit.before_comic_details?.[key] || 'Not entered'} to {edit.after_comic_details?.[key] || 'Not entered'}</small>)}
        {(['media_format','studio'] as const).filter(key=>edit.before_movie_details?.[key]!==edit.after_movie_details?.[key]).map(key=><small key={key}>{key==='studio' ? 'Studio' : 'Movie format'}: {edit.before_movie_details?.[key] || 'Not entered'} to {edit.after_movie_details?.[key] || 'Not entered'}</small>)}
        {(edit.before_barcode?.value!==edit.after_barcode?.value || edit.before_barcode?.format!==edit.after_barcode?.format || edit.before_barcode?.supplement!==edit.after_barcode?.supplement) && <small>Barcode: {edit.before_barcode?.value || 'Not entered'} ({edit.before_barcode?.format || 'Unknown format'}; supplement {edit.before_barcode?.supplement || 'not detected'}) to {edit.after_barcode?.value || 'Not entered'} ({edit.after_barcode?.format || 'Unknown format'}; supplement {edit.after_barcode?.supplement || 'not detected'})</small>}
        {Array.from(new Set([...Object.keys(edit.before_custom_details||{}),...Object.keys(edit.after_custom_details||{})])).filter(key=>JSON.stringify(edit.before_custom_details?.[key])!==JSON.stringify(edit.after_custom_details?.[key])).map(key=><small key={key}>{customCollection?.proposal.type_definition.optional_fields.find(f=>f.id===key)?.label||key}: {customValueText(edit.before_custom_details?.[key])} to {customValueText(edit.after_custom_details?.[key])}</small>)}
        <small>Revision {edit.after_revision} · {new Date(edit.created_at).toLocaleString()}</small>
      </li>)}</ol> : <p>No copy edits recorded.</p>}
      <Pages label="Copy edit history pages" page={page} more={history.more} disabled={locked || history.busy} select={setPage} />
    </details>
  </div>;
}
