'use client';
import {useRef,useState} from 'react';
import {api,errorText,type RunSave} from '../lib/inventory-client';
type Batch={id:string;source:'clz'|'discogs';row_count:number;copy_count:number;created_at:string};
type Preview={sha256:string;row_count:number;copy_count:number;errors:{row:number;message:string}[];repeated_external_ids:number;mapping:Record<string,string>;preserved_columns:string[];existing_batch:Batch|null;sample:{row:number;quantity:number;title:string;edition_label:string|null;record_details:{artist?:string;format?:string};comic_details:{issue_number?:string;publisher?:string}}[]};
type SourceRow={copy_id:string;row:number;copy_number:number;source:Record<string,string>};
const names={clz:'CLZ Comics',discogs:'Discogs Albums'};
export default function CsvImport({runSave,locked,changed,openCopy}:{runSave:RunSave;locked:boolean;changed:()=>void;openCopy:(id:string)=>void}){
 const [open,setOpen]=useState(false),[source,setSource]=useState<'clz'|'discogs'>('clz'),[file,setFile]=useState<File|null>(null);
 const [preview,setPreview]=useState<Preview|null>(null),[reviewed,setReviewed]=useState(false),[working,setWorking]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [batches,setBatches]=useState<Batch[]>([]),[batchPage,setBatchPage]=useState(0),[historyLoaded,setHistoryLoaded]=useState(false),[selected,setSelected]=useState<Batch|null>(null),[rows,setRows]=useState<SourceRow[]>([]),[rowPage,setRowPage]=useState(0);
 const pending=useRef(false);const disabled=locked||working;
 function reset(){setPreview(null);setReviewed(false);setError('');setNotice('');}
 async function task(action:()=>Promise<void>){if(pending.current||locked)return;pending.current=true;setWorking(true);setError('');try{await action();}catch(e){setError(errorText(e));}finally{pending.current=false;setWorking(false);}}
 async function history(page:number){const result=await api<Batch[]>(`imports?limit=21&offset=${page*20}`);setBatches(result);setBatchPage(page);setHistoryLoaded(true);}
 async function sourceRows(batch:Batch,page:number){const result=await api<SourceRow[]>(`imports/${batch.id}/rows?limit=21&offset=${page*20}`);setRows(result);setSelected(batch);setRowPage(page);}
 async function inspect(){await task(async()=>{
  setPreview(null);setReviewed(false);setNotice('');
  if(!file||!file.size||file.size>4*1024*1024)throw new Error('Choose a nonempty UTF-8 CSV file of at most 4 MiB.');
  const result=await api<Preview>(`imports/preview?source=${source}`,{method:'POST',headers:{'Content-Type':'text/csv'},body:file});setPreview(result);
 });}
 async function commit(){if(!file||!preview||!reviewed||preview.errors.length||preview.existing_batch)return;
  await task(async()=>{try{await runSave(async()=>{
   const result=await api<{batch:Batch;already_imported:boolean}>(`imports/commit?source=${source}&reviewed_sha256=${preview.sha256}`,{method:'POST',headers:{'Content-Type':'text/csv'},body:file!});
   setPreview(null);setReviewed(false);setNotice(result.already_imported?'This exact file was already imported. No additional copies were created.':`Imported ${result.batch.copy_count} physical copies into ${source==='clz'?'Comics':'Albums'}. Choose that type or All types in Your collection to see them.`);changed();
  });}catch(e){setPreview(null);setReviewed(false);throw e;}
  // History loading is separate from the committed import. A failed read must
  // never imply that the write failed or invite a duplicate retry.
  try{await history(0);}catch{setError('Import completed; history could not be loaded. Reload import history.');}
  });
 }
 return <section className="collection-setup" aria-label="CSV imports">
  <button disabled={disabled} onClick={()=>setOpen(!open)} aria-expanded={open}>{open?'Close imports':'Import CSV'}</button>
  {open&&<><h2>Bring in your collection</h2><p>Preview a CLZ Comics or Discogs collection export, then choose when to import. Nothing is saved by previewing.</p>
   <fieldset disabled={disabled}><legend>Choose an export</legend>
    <label htmlFor="csv-source">Export format</label><select id="csv-source" value={source} onChange={e=>{setSource(e.target.value as 'clz'|'discogs');reset();}}><option value="clz">CLZ Comics</option><option value="discogs">Discogs Albums</option></select>
    <label htmlFor="csv-file">CSV file</label><input id="csv-file" type="file" accept=".csv,text/csv" onChange={e=>{setFile(e.target.files?.[0]||null);reset();}} aria-describedby="csv-limits"/>
    <p id="csv-limits" className="hint">UTF-8, comma-separated, up to 4 MiB and 5,000 rows. Up to 10,000 physical copies per import.</p>
    <button onClick={()=>void inspect()} disabled={!file}>Preview import</button>
   </fieldset>
   {preview&&<div><h3>Review the import</h3><p>{preview.row_count} valid rows → {preview.copy_count} physical copies in {source==='clz'?'Comics':'Albums'}.</p>
    <p>Each row stays separate, even when catalog IDs repeat. Exact-file retries create no additional copies. A changed export is a new import and can duplicate previously imported items.</p>
    <p>Every original column is retained as source information. Storage boxes and folders are retained without assigning locations. Prices, grades, dates and external IDs are not converted into authoritative valuations or catalog matches.</p>
    {preview.repeated_external_ids>0&&<p>{preview.repeated_external_ids} repeated external IDs found. These copies will remain separate.</p>}
    <details><summary>Field mapping and retained columns</summary><dl>{Object.entries(preview.mapping).map(([from,to])=><div key={from}><dt>{from}</dt><dd>{to}</dd></div>)}</dl><p>{preview.preserved_columns.join(', ')}</p></details>
    <ol>{preview.sample.map(r=><li key={r.row}><strong>{r.record_details.artist?`${r.record_details.artist} — `:''}{r.title}{r.comic_details.issue_number?` #${r.comic_details.issue_number}`:''}</strong><p>{r.edition_label||r.record_details.format||'Edition not specified'} · {r.quantity} {r.quantity===1?'copy':'copies'} · CSV row {r.row}</p></li>)}</ol>
    {preview.errors.length>0&&<div className="error" role="alert"><p>No import is available until every row is valid. Showing up to 50 errors.</p><ul>{preview.errors.map(e=><li key={e.row}>Row {e.row}: {e.message}</li>)}</ul></div>}
    {preview.existing_batch?<p role="status">This exact file was already imported ({preview.existing_batch.copy_count} copies). No additional copies will be created.</p>:!preview.errors.length&&<><label><input type="checkbox" checked={reviewed} disabled={disabled} onChange={e=>setReviewed(e.target.checked)}/> I reviewed the preview and want to create these {preview.copy_count} physical copies.</label><button className="primary" disabled={disabled||!reviewed} onClick={()=>void commit()}>Import {preview.copy_count} copies</button></>}
   </div>}
   {working&&<p role="status">Working… Keep this page open.</p>}{notice&&<p role="status">{notice}</p>}{error&&<p className="error" role="alert">{error} Preview the same file again to check whether an import completed. Saves are never retried automatically.</p>}
   <h3>Import history</h3><button disabled={disabled} onClick={()=>void task(()=>history(0))}>Reload import history</button>
   {historyLoaded&&<>{!batches.length?<p>No imports recorded.</p>:<ul>{batches.slice(0,20).map(b=><li key={b.id}><button disabled={disabled} onClick={()=>void task(()=>sourceRows(b,0))}>{names[b.source]} · {b.copy_count} copies · {new Date(b.created_at).toLocaleString()}</button></li>)}</ul>}<nav aria-label="Import history pages"><button disabled={disabled||!batchPage} onClick={()=>void task(()=>history(batchPage-1))}>Previous imports</button><span>Page {batchPage+1}</span><button disabled={disabled||batches.length<=20} onClick={()=>void task(()=>history(batchPage+1))}>Next imports</button></nav></>}
   {selected&&<><h4>Original source rows · {names[selected.source]}</h4><ul>{rows.slice(0,20).map(r=><li key={r.copy_id}><button disabled={disabled} onClick={()=>openCopy(r.copy_id)}>Open copy from row {r.row}, copy {r.copy_number}</button><details><summary>View retained fields</summary><dl>{Object.entries(r.source).map(([key,value])=><div key={key}><dt>{key}</dt><dd style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{value||'(empty)'}</dd></div>)}</dl></details></li>)}</ul><nav aria-label="Source row pages"><button disabled={disabled||!rowPage} onClick={()=>void task(()=>sourceRows(selected,rowPage-1))}>Previous source rows</button><span>Page {rowPage+1}</span><button disabled={disabled||rows.length<=20} onClick={()=>void task(()=>sourceRows(selected,rowPage+1))}>Next source rows</button></nav></>}
  </>}
 </section>;
}
