'use client';
import {useEffect,useRef,useState} from 'react';
import ImportStorage from './import-storage';
import {api,ApiError,errorText,type CollectionTypeId,type RunSave} from '../lib/inventory-client';
type Batch={id:string;source:'clz'|'discogs'|'bluray';row_count:number;copy_count:number;created_at:string};
type Preview={sha256:string;row_count:number;copy_count:number;errors:{row:number;message:string}[];warnings?:{row:number;message:string}[];repeated_external_ids:number;mapping:Record<string,string>;preserved_columns:string[];existing_batch:Batch|null;sample:{movie_details?:{media_format?:string;studio?:string};row:number;quantity:number;title:string;edition_label:string|null;record_details:{artist?:string;format?:string};comic_details:{issue_number?:string;publisher?:string}}[]};
type SourceRow={copy_id:string;row:number;copy_number:number;source:Record<string,string>};
const names={clz:'CLZ Comics',discogs:'Discogs Albums',bluray:'Blu-ray.com Movies'};
const collections={clz:'Comics',discogs:'Albums',bluray:'Movies'};
const collectionTypes = { clz: 'comic', discogs: 'record', bluray: 'movie' } as const;
const steps = ['Choose export', 'Review', 'Result'] as const;
type Step = 'choose' | 'review' | 'result' | 'recover';
export default function CsvImport({runSave,locked,changed,openCopy,browse}:{runSave:RunSave;locked:boolean;changed:()=>void;openCopy:(id:string)=>void;browse:(type:CollectionTypeId)=>void}){
 const [open,setOpen]=useState(false),[source,setSource]=useState<'clz'|'discogs'|'bluray'>('clz'),[file,setFile]=useState<File|null>(null);
 const [preview,setPreview]=useState<Preview|null>(null),[reviewed,setReviewed]=useState(false),[working,setWorking]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [batches,setBatches]=useState<Batch[]>([]),[batchPage,setBatchPage]=useState(0),[historyLoaded,setHistoryLoaded]=useState(false),[selected,setSelected]=useState<Batch|null>(null),[rows,setRows]=useState<SourceRow[]>([]),[rowPage,setRowPage]=useState(0);
 const [mappingBatch,setMappingBatch]=useState<Batch|null>(null);
 const [step,setStep]=useState<Step>('choose');
 const [result,setResult]=useState<{batch:Batch;reopened:boolean}|null>(null);
 const input=useRef<HTMLInputElement>(null), heading=useRef<HTMLHeadingElement>(null);
 const pending=useRef(false);const disabled=locked||working;
 useEffect(()=>{if(open)heading.current?.focus();},[open,step]);
 function reset(){setPreview(null);setReviewed(false);setError('');setNotice('');}
 async function task(action:()=>Promise<void>){if(pending.current||locked)return;pending.current=true;setWorking(true);setError('');try{await action();}catch(e){setError(errorText(e));}finally{pending.current=false;setWorking(false);}}
 async function history(page:number){const result=await api<Batch[]>(`imports?limit=21&offset=${page*20}`);setBatches(result);setBatchPage(page);setHistoryLoaded(true);}
 async function sourceRows(batch:Batch,page:number){const result=await api<SourceRow[]>(`imports/${batch.id}/rows?limit=21&offset=${page*20}`);setRows(result);setSelected(batch);setRowPage(page);}
 function chooseFile(clear=false){
  reset();
  if(clear){
   setFile(null);setSelected(null);setMappingBatch(null);
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
   setReviewed(false);setNotice('');setPreview(checked);setStep('review');
   if(step==='recover'&&!checked.existing_batch)setNotice('No completed import was found for this file. Review this fresh preview before deciding whether to import.');
  });
 }
 function showResult(batch:Batch,reopened:boolean){
  setResult({batch,reopened});setSelected(null);setMappingBatch(null);
  setError('');setNotice('');setStep('result');
 }
 async function commit(){
  if(step!=='review'||!file||!preview||!reviewed||preview.errors.length||preview.existing_batch)return;
  await task(async()=>{
   try{
    await runSave(async()=>{
     const saved=await api<{batch:Batch;already_imported:boolean}>(`imports/commit?source=${source}&reviewed_sha256=${preview.sha256}`,{method:'POST',headers:{'Content-Type':'text/csv'},body:file});
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
    <p>A changed export can duplicate previously imported items. Repeated catalog IDs remain separate physical copies.</p>
    <p>Every original column is retained as source information, including storage labels, prices and external IDs.</p>
    {source==='bluray'&&<p>A movie or box set counts as one owned item, regardless of disc count.</p>}
    {!!preview.warnings?.length&&<div role="status"><p>Review these notes (up to 50):</p><ul>{preview.warnings.map((warning,index)=><li key={index}>Row {warning.row}: {warning.message}</li>)}</ul></div>}
    {preview.repeated_external_ids>0&&<p>{preview.repeated_external_ids} repeated external IDs found. These copies will remain separate.</p>}
    <details><summary>Field mapping and retained columns</summary><dl>{Object.entries(preview.mapping).map(([from,to])=><div key={from}><dt>{from}</dt><dd>{to}</dd></div>)}</dl><p>{preview.preserved_columns.join(', ')}</p></details>
    <ol className="csv-sample" aria-label="Sample from the export">{preview.sample.map(r=><li key={r.row}><strong>{r.record_details.artist?`${r.record_details.artist} — `:''}{r.title}{r.comic_details.issue_number?` #${r.comic_details.issue_number}`:''}</strong><p>{r.edition_label||r.movie_details?.media_format||r.record_details.format||'Edition not specified'} · {r.quantity} {r.quantity===1?'copy':'copies'} · CSV row {r.row}</p></li>)}</ol>
    {preview.errors.length>0&&<div className="error" role="alert"><p>No import is available until every row is valid. Showing up to 50 errors.</p><ul>{preview.errors.map(e=><li key={e.row}>Row {e.row}: {e.message}</li>)}</ul></div>}
    {preview.existing_batch?<><p role="status">This exact file was already imported ({preview.existing_batch.copy_count} copies). No additional copies will be created.</p>
      <button disabled={disabled} onClick={()=>showResult(preview.existing_batch!,true)}>View previous import</button></>
      :!preview.errors.length&&<><label><input type="checkbox" checked={reviewed} disabled={disabled} onChange={e=>setReviewed(e.target.checked)}/> I reviewed the preview and want to create these {preview.copy_count} physical copies.</label><button className="primary" disabled={disabled||!reviewed} onClick={()=>void commit()}>Import {preview.copy_count} copies</button></>}
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
     <button className="primary" disabled={disabled} onClick={()=>{setOpen(false);browse(collectionTypes[result.batch.source]);}}>View {collections[result.batch.source]}</button>
     <button disabled={disabled} onClick={()=>void task(()=>sourceRows(result.batch,0))}>View original rows</button>
     {result.batch.source==='clz'&&<button disabled={disabled} onClick={()=>setMappingBatch(result.batch)}>Review imported storage labels</button>}
     <button disabled={disabled} onClick={()=>chooseFile(true)}>Import another file</button>
    </div>
   </section>}
   {working&&<p role="status">Working… Keep this page open.</p>}{notice&&<p role="status">{notice}</p>}
   {error&&<p className="error" role="alert">{error}{step==='recover'?' Preview the same file again to check whether an import completed.':''}</p>}
   <details className="csv-history"><summary>Import history</summary><button disabled={disabled} onClick={()=>void task(()=>history(0))}>Reload import history</button>
   {historyLoaded&&<>{!batches.length?<p>No imports recorded.</p>:<ul>{batches.slice(0,20).map(b=><li key={b.id}><button disabled={disabled} onClick={()=>void task(()=>sourceRows(b,0))}>{names[b.source]} · {b.copy_count} copies · {new Date(b.created_at).toLocaleString()}</button>{b.source==='clz'?<button disabled={disabled} onClick={()=>setMappingBatch(b)}>Map storage boxes</button>:<span> · {b.source==='discogs' ? 'Discogs folders are source information, not physical locations.' : 'Original packaging and disc details are retained as source information.'}</span>}</li>)}</ul>}<nav aria-label="Import history pages"><button disabled={disabled||!batchPage} onClick={()=>void task(()=>history(batchPage-1))}>Previous imports</button><span>Page {batchPage+1}</span><button disabled={disabled||batches.length<=20} onClick={()=>void task(()=>history(batchPage+1))}>Next imports</button></nav></>}</details>
   {mappingBatch&&<ImportStorage key={mappingBatch.id} batchId={mappingBatch.id} locked={disabled} runSave={runSave} changed={changed}/>}
   {selected&&<><h4>Original source rows · {names[selected.source]}</h4><ul>{rows.slice(0,20).map(r=><li key={r.copy_id}><button disabled={disabled} onClick={()=>openCopy(r.copy_id)}>Open copy from row {r.row}, copy {r.copy_number}</button><details><summary>View retained fields</summary><dl>{Object.entries(r.source).map(([key,value])=><div key={key}><dt>{key}</dt><dd style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{value||'(empty)'}</dd></div>)}</dl></details></li>)}</ul><nav aria-label="Source row pages"><button disabled={disabled||!rowPage} onClick={()=>void task(()=>sourceRows(selected,rowPage-1))}>Previous source rows</button><span>Page {rowPage+1}</span><button disabled={disabled||rows.length<=20} onClick={()=>void task(()=>sourceRows(selected,rowPage+1))}>Next source rows</button></nav></>}
  </div>
 </section>;
}
