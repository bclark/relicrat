'use client';
import {useEffect,useRef,useState} from 'react';
import ImportStorage from './import-storage';
import {api,ApiError,errorText,jsonSave,type CollectionTypeId,type RunSave} from '../lib/inventory-client';
type Batch={id:string;source:'clz'|'discogs'|'bluray';row_count:number;copy_count:number;created_at:string};
type PreviewDuplicateReview = {
 digest:string;
 rows:{row:number;group:number;quantity:number;title:string;edition:string|null;issue:string|null}[];
 groups:{count:number;copies:{copy_id:string;title:string|null;edition:string|null;format:string|null;storage:string|null}[]}[];
};
type Preview={duplicate_review:PreviewDuplicateReview|null;sha256:string;row_count:number;copy_count:number;errors:{row:number;message:string}[];warnings?:{row:number;message:string}[];repeated_external_ids:number;mapping:Record<string,string>;preserved_columns:string[];existing_batch:Batch|null;sample:{movie_details?:{media_format?:string;studio?:string};row:number;quantity:number;title:string;edition_label:string|null;record_details:{artist?:string;format?:string};comic_details:{issue_number?:string;publisher?:string}}[]};
type DuplicateGroup = {anchor:string; title:string|null; selected_count:number; other_count:number};
type DuplicateCopy = {
 copy_id:string; updated_at:string; selected_import:boolean; imported_at:string; row:number; copy_number:number;
 title:string|null; edition:string|null; artist:string|null; issue:string|null; format:string|null; storage:string|null;
};
type Decision = {
 id:string; archived_id:string|null; left_id:string; created_at:string;
 left_title:string|null; right_title:string|null; left_edition:string|null; right_edition:string|null;
};
type DecisionRequest = {
 request_id:string; first_id:string; second_id:string;
 first_updated_at:string; second_updated_at:string; archive_id:string|null;
};
function copyLabel(copy:DuplicateCopy) {
 return [copy.title||'Untitled copy', copy.edition||copy.format,
  copy.selected_import?'Selected import':'Another import', new Date(copy.imported_at).toLocaleString(),
  'row '+copy.row+', copy '+copy.copy_number]
  .filter(Boolean).join(' · ');
}
function skippedRowsMask(choices:Record<number,'skip'|'import'>) {
 const mask = new Uint8Array(625);
 for(const [row,choice] of Object.entries(choices)){
  if(choice==='skip'){
   const bit=Number(row)-2;
   mask[bit >> 3] |= 1 << (bit % 8);
  }
 }
 return Array.from(mask,value=>value.toString(16).padStart(2,'0')).join('');
}
const matchLabels = {clz:'CLZ comic ID',discogs:'Discogs release ID',bluray:'Blu-ray.com product ID'};
type SourceRow={copy_id:string;row:number;copy_number:number;source:Record<string,string>};
const names={clz:'CLZ Comics',discogs:'Discogs Albums',bluray:'Blu-ray.com Movies'};
const collections={clz:'Comics',discogs:'Albums',bluray:'Movies'};
const collectionTypes = { clz: 'comic', discogs: 'record', bluray: 'movie' } as const;
const steps = ['Choose export', 'Review', 'Result'] as const;
type Step = 'choose' | 'review' | 'result' | 'recover';
export default function CsvImport({runSave,locked,changed,openCopy,browse}:{runSave:RunSave;locked:boolean;changed:()=>void;openCopy:(id:string)=>void;browse:(type:CollectionTypeId,batchId?:string)=>void}){
 const [open,setOpen]=useState(false),[source,setSource]=useState<'clz'|'discogs'|'bluray'>('clz'),[file,setFile]=useState<File|null>(null);
 const [previewChoices,setPreviewChoices] = useState<Record<number,'skip'|'import'>>({});
 const [previewPage,setPreviewPage] = useState(0);
 const [preview,setPreview]=useState<Preview|null>(null),[reviewed,setReviewed]=useState(false),[working,setWorking]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [batches,setBatches]=useState<Batch[]>([]),[batchPage,setBatchPage]=useState(0),[historyLoaded,setHistoryLoaded]=useState(false),[selected,setSelected]=useState<Batch|null>(null),[rows,setRows]=useState<SourceRow[]>([]),[rowPage,setRowPage]=useState(0);
 const [duplicates,setDuplicates] = useState<{batch:Batch; page:number; groups:DuplicateGroup[]} | null>(null);
 const [comparison,setComparison] = useState<{group:DuplicateGroup; page:number; copies:DuplicateCopy[]} | null>(null);
 const [decisionPage,setDecisionPage] = useState({page:0,items:[] as Decision[]});
 const [fromSelected,setFromSelected] = useState<DuplicateCopy|null>(null);
 const [fromOther,setFromOther] = useState<DuplicateCopy|null>(null);
 const [archiveOpen,setArchiveOpen] = useState(false);
 const [keeper,setKeeper] = useState('');
 const [retryDecision,setRetryDecision] = useState<DecisionRequest|null>(null);
 const duplicateHeading = useRef<HTMLHeadingElement>(null);
 const decisionHistory = useRef<HTMLDetailsElement>(null);
 const [mappingBatch,setMappingBatch]=useState<Batch|null>(null);
 const [step,setStep]=useState<Step>('choose');
 const [result,setResult]=useState<{batch:Batch;reopened:boolean}|null>(null);
 const input=useRef<HTMLInputElement>(null), heading=useRef<HTMLHeadingElement>(null);
 const pending=useRef(false);const disabled=locked||working;
 useEffect(()=>{if(open)heading.current?.focus();},[open,step]);
 const duplicateReview=preview?.duplicate_review;
 const remaining=duplicateReview?.rows.filter(row=>!previewChoices[row.row]).length ?? 0;
 const skippedCopies=duplicateReview?.rows.reduce((total,row)=>total+(previewChoices[row.row]==='skip'?row.quantity:0),0) ?? 0;
 const copyCount=(preview?.copy_count??0)-skippedCopies;
 function reset(){setPreview(null);setPreviewChoices({});setPreviewPage(0);setReviewed(false);setError('');setNotice('');}
 async function task(action:()=>Promise<void>){if(pending.current||locked)return;pending.current=true;setWorking(true);setError('');try{await action();}catch(e){setError(errorText(e));}finally{pending.current=false;setWorking(false);}}
 async function history(page:number){const result=await api<Batch[]>(`imports?limit=21&offset=${page*20}`);setBatches(result);setBatchPage(page);setHistoryLoaded(true);}
 async function sourceRows(batch:Batch,page:number){const result=await api<SourceRow[]>(`imports/${batch.id}/rows?limit=21&offset=${page*20}`);setRows(result);setSelected(batch);setRowPage(page);}
 function clearPair(){
  setFromSelected(null);setFromOther(null);setArchiveOpen(false);setKeeper('');setRetryDecision(null);
 }
 async function readDecisions(batch:Batch,page:number){
  return {page,items:await api<Decision[]>(`imports/${batch.id}/duplicate-decisions?limit=21&offset=${page*20}`)};
 }
 async function loadDuplicates(batch:Batch,page:number){
  const [groups,history] = await Promise.all([
   api<DuplicateGroup[]>(`imports/${batch.id}/possible-duplicates?limit=21&offset=${page*20}`),
   readDecisions(batch,0),
  ]);
  setDecisionPage(history);
  clearPair();
  setDuplicates({batch,page,groups});
  setComparison(null);
  requestAnimationFrame(()=>duplicateHeading.current?.focus());
 }
 async function compare(batch:Batch,group:DuplicateGroup,page:number){
  const copies = await api<DuplicateCopy[]>(`imports/${batch.id}/possible-duplicates?anchor=${group.anchor}&limit=21&offset=${page*20}`);
  if(comparison?.group.anchor!==group.anchor)clearPair();
  setComparison({group,page,copies});
  requestAnimationFrame(()=>duplicateHeading.current?.focus());
 }
 async function refreshAfterDecision(batch:Batch){
  changed();
  setComparison(null);
  clearPair();
  try{
   await loadDuplicates(batch,0);
   if(decisionHistory.current)decisionHistory.current.open=true;
  }
  catch{setError('Your decision was saved. Reload possible duplicates to refresh the review.');}
 }
 async function saveDecision(request:DecisionRequest){
  if(!duplicates)return;
  const {batch}=duplicates;
  await task(async()=>{
   try{
    const saved=await runSave(()=>api<{undone_at:string|null}>(`imports/${batch.id}/duplicate-decisions`,jsonSave(request)));
    if(!saved)return;
    setNotice(saved.undone_at?'This decision was already undone.':request.archive_id?'Duplicate archived.':'Both copies kept.');
    await refreshAfterDecision(batch);
   }catch(problem){
    if(problem instanceof ApiError&&problem.uncertain){
     setRetryDecision(request);
     throw new Error('The decision could not be confirmed. Retry the same decision or reload the review to check Decision history.');
    }
    setRetryDecision(null);
    throw problem;
   }
  });
 }
 function decide(archiveId:string|null){
  if(!fromSelected||!fromOther)return;
  void saveDecision({
   request_id:crypto.randomUUID(), archive_id:archiveId,
   first_id:fromSelected.copy_id, first_updated_at:fromSelected.updated_at,
   second_id:fromOther.copy_id, second_updated_at:fromOther.updated_at,
  });
 }
 async function undo(batch:Batch,decision:Decision){
  await task(async()=>{
   const saved=await runSave(()=>api(`imports/${batch.id}/duplicate-decisions/${decision.id}/undo`,jsonSave({})));
   if(!saved)return;
   setNotice(decision.archived_id?'Archived copy restored.':'Keep both decision undone.');
   await refreshAfterDecision(batch);
  });
 }
 function chooseFile(clear=false){
  reset();
  if(clear){
   setFile(null);setSelected(null);setMappingBatch(null);setDuplicates(null);setComparison(null);
   if(input.current)input.current.value='';
  }
  setResult(null);setStep('choose');
 }
 async function inspect(){
  if(!file)return;
  const selectedFile=file;
  await task(async()=>{
   if(!selectedFile.size||selectedFile.size>4*1024*1024)throw new Error('Choose a nonempty UTF-8 CSV file of at most 4 MiB.');
   const checked=await api<Preview>(`imports/preview?source=${source}`,{method:'POST',headers:{'Content-Type':'text/csv'},body:selectedFile});
   setPreviewChoices({});setPreviewPage(0);setReviewed(false);setNotice('');setPreview(checked);setStep('review');
   if(step==='recover'&&!checked.existing_batch)setNotice('No completed import was found for this file. Review this fresh preview before deciding whether to import.');
  });
 }
 function showResult(batch:Batch,reopened:boolean){
  setResult({batch,reopened});setSelected(null);setMappingBatch(null);setDuplicates(null);setComparison(null);
  setError('');setNotice('');setStep('result');
 }
 async function commit(){
  if(step!=='review'||!file||!preview||!duplicateReview||remaining||!copyCount||!reviewed||preview.errors.length||preview.existing_batch)return;
  await task(async()=>{
   try{
    await runSave(async()=>{
     const query=new URLSearchParams({source,reviewed_sha256:preview.sha256,
      duplicate_digest:duplicateReview.digest,skip_mask:skippedRowsMask(previewChoices)});
     const saved=await api<{batch:Batch;already_imported:boolean}>(`imports/commit?${query}`,{method:'POST',headers:{'Content-Type':'text/csv'},body:file});
     showResult(saved.batch,saved.already_imported);changed();
    });
   }catch(problem){
    setReviewed(false);
    if(problem instanceof ApiError&&problem.uncertain)setStep('recover');
    else chooseFile();
    throw problem;
   }
   try{await history(0);}catch{setError('Import completed; history could not be loaded. Reload import history.');}
  });
 }
 return <section className="collection-setup csv-import" aria-label="CSV imports">
  <button disabled={disabled} onClick={()=>setOpen(!open)} aria-expanded={open} aria-controls="csv-task">{open?'Close imports':'Import CSV'}</button>
  <div id="csv-task" hidden={!open}>
   <h2>Import a collection</h2>
   <p>Review the file before adding copies to your collection.</p>
   <ol className="csv-steps" aria-label="Import steps">{steps.map((label,index)=><li key={label} aria-current={index===(step==='choose'?0:step==='result'?2:1)?'step':undefined}>{label}</li>)}</ol>
   <fieldset disabled={disabled} hidden={step!=='choose'}>
    <legend>Choose an export</legend>
    <label htmlFor="csv-source">Export format</label><select id="csv-source" value={source} onChange={e=>{setSource(e.target.value as Batch['source']);chooseFile(true);}}><option value="clz">CLZ Comics</option><option value="discogs">Discogs Albums</option><option value="bluray">Blu-ray.com Movies</option></select>
    <p>Collection: <strong>{collections[source]}</strong></p>
    <label htmlFor="csv-file">CSV file</label><input ref={input} id="csv-file" type="file" accept=".csv,text/csv" onChange={e=>{setFile(e.target.files?.[0]||null);reset();}} aria-describedby="csv-limits"/>
    <p id="csv-limits" className="hint">UTF-8, comma-separated, up to 4 MiB and 5,000 rows. Up to 10,000 physical copies per import.</p>
    <button className="primary" onClick={()=>void inspect()} disabled={!file}>Preview import</button>
   </fieldset>
   {step==='review'&&preview&&<section aria-labelledby="csv-review-heading">
    <button className="text-button" disabled={disabled} onClick={()=>chooseFile()}>Back to file</button>
    <h3 ref={heading} tabIndex={-1} id="csv-review-heading">Review the import</h3>
    <p>{file?.name}</p>
    <p><strong>{preview.row_count} valid rows → {preview.copy_count} physical copies in {collections[source]}.</strong></p>
    <p>A shared catalog ID may refer to more than one physical copy.</p>
    <p>Every original column is retained as source information, including storage labels, prices and external IDs.</p>
    {source==='bluray'&&<p>A movie or box set counts as one owned item, regardless of disc count.</p>}
    {!!preview.warnings?.length&&<div role="status"><p>Review these notes (up to 50):</p><ul>{preview.warnings.map((warning,index)=><li key={index}>Row {warning.row}: {warning.message}</li>)}</ul></div>}
    {preview.repeated_external_ids>0&&<p>{preview.repeated_external_ids} repeated external IDs found. These copies will remain separate.</p>}
    <details><summary>Field mapping and retained columns</summary><dl>{Object.entries(preview.mapping).map(([from,to])=><div key={from}><dt>{from}</dt><dd>{to}</dd></div>)}</dl><p>{preview.preserved_columns.join(', ')}</p></details>
    <ol className="csv-sample" aria-label="Sample from the export">{preview.sample.map(r=><li key={r.row}><strong>{r.record_details.artist?`${r.record_details.artist} — `:''}{r.title}{r.comic_details.issue_number?` #${r.comic_details.issue_number}`:''}</strong><p>{r.edition_label||r.movie_details?.media_format||r.record_details.format||'Edition not specified'} · {r.quantity} {r.quantity===1?'copy':'copies'} · CSV row {r.row}</p></li>)}</ol>
    {preview.errors.length>0&&<div className="error" role="alert"><p>No import is available until every row is valid. Showing up to 50 errors.</p><ul>{preview.errors.map(e=><li key={e.row}>Row {e.row}: {e.message}</li>)}</ul></div>}
    {!!duplicateReview?.rows.length&&<section className="duplicate-review" aria-labelledby="preview-matches">
     <h4 id="preview-matches">Review possible duplicates before importing</h4>
     <p role="status">{remaining} of {duplicateReview.rows.length} rows still need a decision.</p>
     <p>Matches share a {matchLabels[source]}. Skip a whole CSV row or add its copies to your collection.</p>
     <ul className="duplicate-groups">{duplicateReview.rows.slice(previewPage*20,(previewPage+1)*20).map(row=>{
      const group=duplicateReview.groups[row.group];
      return <li key={row.row}>
       <strong>Row {row.row} · {row.title}{row.issue?' #'+row.issue:''}</strong>
       <p>{row.edition||'Edition not entered'} · {row.quantity} {row.quantity===1?'copy':'copies'} in the file</p>
       <p>{group.count} matching {group.count===1?'copy':'copies'} in your collection{group.count>group.copies.length?' · showing '+group.copies.length:''}</p>
       <ul>{group.copies.map(copy=><li key={copy.copy_id}>
        {copy.title||'Untitled copy'} · {copy.edition||copy.format||'Edition not entered'} · {copy.storage||'Unassigned'}
       </li>)}</ul>
       <label htmlFor={`preview-duplicate-${row.row}`}>Decision for row {row.row}</label>
       <select id={`preview-duplicate-${row.row}`} disabled={disabled} value={previewChoices[row.row]||''}
        onChange={event=>{
         const choice=event.target.value;
         setPreviewChoices(previous=>{
          const next={...previous};
          if(choice==='skip'||choice==='import')next[row.row]=choice;
          else delete next[row.row];
          return next;
         });
         setReviewed(false);
        }}>
        <option value="">Choose what to do</option>
        <option value="skip">Skip row</option>
        <option value="import">{row.quantity===1?'Import as another copy':'Import these copies'}</option>
       </select>
      </li>;
     })}</ul>
     {duplicateReview.rows.length>20&&<nav className="form-actions" aria-label="Duplicate preview pages">
      <button disabled={disabled||previewPage===0} onClick={()=>setPreviewPage(page=>page-1)}>Previous matches</button>
      <span>Page {previewPage+1} of {Math.ceil(duplicateReview.rows.length/20)}</span>
      <button disabled={disabled||(previewPage+1)*20>=duplicateReview.rows.length} onClick={()=>setPreviewPage(page=>page+1)}>Next matches</button>
     </nav>}
     {skippedCopies>0&&<p>Skipping {skippedCopies} {skippedCopies===1?'copy':'copies'}. Once confirmed, this exact file will count as imported.</p>}
     {copyCount===0&&<p>Nothing selected to import. Change a row decision to continue.</p>}
    </section>}
    {preview.existing_batch?<><p role="status">This exact file was already imported ({preview.existing_batch.copy_count} copies). No additional copies will be created.</p>
      <button disabled={disabled} onClick={()=>showResult(preview.existing_batch!,true)}>View previous import</button></>
      :!preview.errors.length&&<><label><input type="checkbox" checked={reviewed} disabled={disabled||!duplicateReview||!!remaining||!copyCount} onChange={e=>setReviewed(e.target.checked)}/> I reviewed the preview and want to create these {copyCount} physical copies.</label><button className="primary" disabled={disabled||!duplicateReview||!!remaining||!copyCount||!reviewed} onClick={()=>void commit()}>Import {copyCount} copies</button></>}
   </section>}
   {step==='recover'&&<section aria-labelledby="csv-recover-heading">
    <h3 ref={heading} tabIndex={-1} id="csv-recover-heading">Import result needs checking</h3>
    <p>Preview the same file again to check whether an import completed. Your selected file is still here.</p>
    <button disabled={disabled} onClick={()=>void inspect()}>Check this exact file</button>
   </section>}
   {step==='result'&&result&&<section aria-labelledby="csv-result-heading">
    <h3 ref={heading} tabIndex={-1} id="csv-result-heading">{result.reopened?'Previous import':'Import complete'}</h3>
    <p className="notice" role="status">{result.reopened?`This exact file was already imported (${result.batch.copy_count} copies).`:`Imported ${result.batch.copy_count} physical copies into ${collections[result.batch.source]}.`}</p>
    <div className="form-actions">
     <button className="primary" disabled={disabled} onClick={()=>browse(collectionTypes[result.batch.source],result.batch.id)}>View imported copies</button>
     <button disabled={disabled} onClick={()=>browse(collectionTypes[result.batch.source])}>View {collections[result.batch.source]}</button>
     <button disabled={disabled} onClick={()=>void task(()=>sourceRows(result.batch,0))}>View original rows</button>
     <button disabled={disabled} onClick={()=>void task(()=>loadDuplicates(result.batch,0))}>Review possible duplicates</button>
     {result.batch.source==='clz'&&<button disabled={disabled} onClick={()=>setMappingBatch(result.batch)}>Review imported storage labels</button>}
     <button disabled={disabled} onClick={()=>chooseFile(true)}>Import another file</button>
    </div>
   </section>}
   {working&&<p role="status">Working… Keep this page open.</p>}{notice&&<p role="status">{notice}</p>}
   {error&&<p className="error" role="alert">{error}{step==='recover'?' Preview the same file again to check whether an import completed.':''}</p>}
   <details className="csv-history"><summary>Import history</summary><button disabled={disabled} onClick={()=>void task(()=>history(0))}>Reload import history</button>
   {historyLoaded&&<>{!batches.length?<p>No imports recorded.</p>:<ul>{batches.slice(0,20).map(b=><li key={b.id}><button disabled={disabled} onClick={()=>void task(()=>sourceRows(b,0))}>{names[b.source]} · {b.copy_count} copies · {new Date(b.created_at).toLocaleString()}</button><button disabled={disabled} onClick={()=>void task(()=>loadDuplicates(b,0))}>Review possible duplicates</button>{b.source==='clz'?<button disabled={disabled} onClick={()=>setMappingBatch(b)}>Map storage boxes</button>:<span> · {b.source==='discogs' ? 'Discogs folders are source information, not physical locations.' : 'Original packaging and disc details are retained as source information.'}</span>}</li>)}</ul>}<nav aria-label="Import history pages"><button disabled={disabled||!batchPage} onClick={()=>void task(()=>history(batchPage-1))}>Previous imports</button><span>Page {batchPage+1}</span><button disabled={disabled||batches.length<=20} onClick={()=>void task(()=>history(batchPage+1))}>Next imports</button></nav></>}</details>
   {duplicates&&<section className="duplicate-review" aria-labelledby="duplicate-review-heading">
    <h3 id="duplicate-review-heading" tabIndex={-1} ref={duplicateHeading}>{comparison?'Compare copies':'Possible duplicates'}</h3>
    <p>{names[duplicates.batch.source]} · {new Date(duplicates.batch.created_at).toLocaleString()}</p>
    <p>Matches share a {matchLabels[duplicates.batch.source]} across imports. You may own more than one copy of the same release.</p>
    {comparison?<>
     <div className="form-actions">
     <button type="button" className="text-button" disabled={disabled} onClick={()=>{
      setComparison(null);clearPair();
      requestAnimationFrame(()=>duplicateHeading.current?.focus());
     }}>Back to possible duplicates</button>
     <button type="button" className="text-button" disabled={disabled} onClick={()=>void task(()=>loadDuplicates(duplicates.batch,0))}>Reload review</button>
     </div>
     <ul className="duplicate-copies" aria-label="Copies that share the source ID">{comparison.copies.slice(0,20).map(copy=><li key={copy.copy_id}>
      <p>{copy.selected_import?'Selected import':'Another import'} · {new Date(copy.imported_at).toLocaleString()}</p>
      <h4>{copy.artist?copy.artist+' — ':''}{copy.title||'Untitled copy'}{copy.issue?' #'+copy.issue:''}</h4>
      <dl>
       <div><dt>Edition</dt><dd>{copy.edition||'Not entered'}</dd></div>
       {copy.format&&<div><dt>Format</dt><dd>{copy.format}</dd></div>}
       <div><dt>Storage</dt><dd>{copy.storage||'Unassigned'}</dd></div>
       <div><dt>CSV source</dt><dd>Row {copy.row}, copy {copy.copy_number}</dd></div>
      </dl>
      <label className="duplicate-pick"><input type="radio"
       aria-label={`Select copy: ${copyLabel(copy)}`}
       name={copy.selected_import?'duplicate-selected-copy':'duplicate-other-copy'}
       checked={(copy.selected_import?fromSelected:fromOther)?.copy_id===copy.copy_id}
       disabled={disabled||!!retryDecision} onChange={()=>{
        (copy.selected_import?setFromSelected:setFromOther)(copy);
        setArchiveOpen(false);setKeeper('');
       }} /> Select copy</label>
      <button type="button" disabled={disabled} onClick={()=>openCopy(copy.copy_id)}>Open copy</button>
     </li>)}</ul>
     {(comparison.page>0||comparison.copies.length>20)&&<nav className="form-actions" aria-label="Matching copy pages">
      <button disabled={disabled||!comparison.page} onClick={()=>void task(()=>compare(duplicates.batch,comparison.group,comparison.page-1))}>Previous copies</button>
      <button disabled={disabled||comparison.copies.length<=20} onClick={()=>void task(()=>compare(duplicates.batch,comparison.group,comparison.page+1))}>Next copies</button>
     </nav>}
     <fieldset disabled={disabled}>
      <legend>Decide what to keep</legend>
      {!fromSelected||!fromOther?<p>Select a copy from this import and a copy from another import.</p>:<>
       <ul><li>{copyLabel(fromSelected)}</li><li>{copyLabel(fromOther)}</li></ul>
       {retryDecision?<button type="button" onClick={()=>void saveDecision(retryDecision)}>Retry same decision</button>:archiveOpen?<>
        <label htmlFor="duplicate-keeper">Which copy should stay in your collection?</label>
        <select id="duplicate-keeper" value={keeper} onChange={event=>setKeeper(event.target.value)}>
         <option value="">Choose the copy to keep</option>
         {[fromSelected,fromOther].map(copy=><option key={copy.copy_id} value={copy.copy_id}>{copyLabel(copy)}</option>)}
        </select>
        <p>The other copy will move out of active inventory. You can restore it from Decision history.</p>
        <div className="form-actions">
         <button type="button" disabled={!keeper} onClick={()=>decide(keeper===fromSelected.copy_id?fromOther.copy_id:fromSelected.copy_id)}>Confirm archive</button>
         <button type="button" onClick={()=>{setArchiveOpen(false);setKeeper('');}}>Cancel</button>
        </div>
       </>:<div className="form-actions">
        <button type="button" onClick={()=>decide(null)}>Keep both</button>
        <button type="button" onClick={()=>setArchiveOpen(true)}>Archive duplicate</button>
       </div>}
      </>}
     </fieldset>
    </>:<>
     {duplicates.groups.length?<ul className="duplicate-groups">{duplicates.groups.slice(0,20).map(group=><li key={group.anchor}>
      <button type="button" className="text-button" disabled={disabled} onClick={()=>void task(()=>compare(duplicates.batch,group,0))}>{group.title||'Untitled copy'}</button>
      <p>{group.selected_count} in this import · {group.other_count} in other imports</p>
     </li>)}</ul>:<p role="status">No possible duplicates need review for this import.</p>}
     {(duplicates.page>0||duplicates.groups.length>20)&&<nav className="form-actions" aria-label="Possible duplicate pages">
      <button disabled={disabled||!duplicates.page} onClick={()=>void task(()=>loadDuplicates(duplicates.batch,duplicates.page-1))}>Previous matches</button>
      <button disabled={disabled||duplicates.groups.length<=20} onClick={()=>void task(()=>loadDuplicates(duplicates.batch,duplicates.page+1))}>Next matches</button>
     </nav>}
    </>}
    <details ref={decisionHistory}>
     <summary>Decision history</summary>
     {decisionPage.items.length?<ul className="duplicate-groups">{decisionPage.items.slice(0,20).map(decision=>{
      const left=[decision.left_title||'Untitled copy',decision.left_edition].filter(Boolean).join(' · ');
      const right=[decision.right_title||'Untitled copy',decision.right_edition].filter(Boolean).join(' · ');
      const archived=decision.archived_id===decision.left_id?left:right;
      return <li key={decision.id}>
       <p>{decision.archived_id?'Archived '+archived:'Kept both copies'} · {new Date(decision.created_at).toLocaleString()}</p>
       <p>{left} / {right}</p>
       <button type="button" disabled={disabled} onClick={()=>void undo(duplicates.batch,decision)}>Undo</button>
      </li>;
     })}</ul>:<p>No active decisions for this import.</p>}
     {(decisionPage.page>0||decisionPage.items.length>20)&&<nav className="form-actions" aria-label="Duplicate decision pages">
      <button disabled={disabled||!decisionPage.page} onClick={()=>void task(async()=>setDecisionPage(await readDecisions(duplicates.batch,decisionPage.page-1)))}>Previous decisions</button>
      <button disabled={disabled||decisionPage.items.length<=20} onClick={()=>void task(async()=>setDecisionPage(await readDecisions(duplicates.batch,decisionPage.page+1)))}>Next decisions</button>
     </nav>}
    </details>
   </section>}
   {mappingBatch&&<ImportStorage key={mappingBatch.id} batchId={mappingBatch.id} locked={disabled} runSave={runSave} changed={changed}/>}
   {selected&&<><h4>Original source rows · {names[selected.source]}</h4><button disabled={disabled} onClick={()=>browse(collectionTypes[selected.source],selected.id)}>Browse copies from these rows</button><ul>{rows.slice(0,20).map(r=><li key={r.copy_id}><button disabled={disabled} onClick={()=>openCopy(r.copy_id)}>Open copy from row {r.row}, copy {r.copy_number}</button><details><summary>View retained fields</summary><dl>{Object.entries(r.source).map(([key,value])=><div key={key}><dt>{key}</dt><dd style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{value||'(empty)'}</dd></div>)}</dl></details></li>)}</ul><nav aria-label="Source row pages"><button disabled={disabled||!rowPage} onClick={()=>void task(()=>sourceRows(selected,rowPage-1))}>Previous source rows</button><span>Page {rowPage+1}</span><button disabled={disabled||rows.length<=20} onClick={()=>void task(()=>sourceRows(selected,rowPage+1))}>Next source rows</button></nav></>}
  </div>
 </section>;
}
