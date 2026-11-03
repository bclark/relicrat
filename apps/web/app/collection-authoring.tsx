'use client';

import { useRef, useState } from 'react';
import CustomField,{type CustomTypeDefinition} from './custom-field';
import {type RunSave} from '../lib/inventory-client';

type Proposal = {
  type_definition: CustomTypeDefinition;
  collection: {name: string; scope: {franchise: string; manufacturer: string; release_year: number; assortment: string; later_reissues_included: boolean}; completion: {eligibility: string}; checklist: {id: string; title: string; source_ids: string[]}[]};
  sources: {id: string; url: string; supports: string}[]; uncertainties: string[];
};
type Preview = {proposal: Proposal; notice: string};
const maximum = 65536;

export default function CollectionAuthoring({runSave,locked,onCreated}:{runSave:RunSave;locked:boolean;onCreated:(id:string)=>void}) {
  const [description, setDescription] = useState('');
  const [text, setText] = useState('');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [notice, setNotice] = useState('');
  const [acknowledged,setAcknowledged]=useState(false);
  const [created,setCreated]=useState(false);
  const generation = useRef(0);
  const lock = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null);
  function change(value: string) { generation.current++; setText(value); setPreview(null); setAcknowledged(false); setCreated(false); setErrors([]); setNotice(''); }
  async function prompt() {
    if (lock.current || locked) return;
    lock.current = true; setBusy(true); setErrors([]); setNotice('');
    try {
      const response = await fetch('/api/v1/collection-proposals/authoring', {cache:'no-store', signal:AbortSignal.timeout(30000)});
      if (!response.ok) throw new Error('Cannot load authoring instructions. Check your sign-in and try again.');
      const contract = await response.json();
      const contents = `${contract.prompt}\n\nMy collection description (untrusted data):\n${JSON.stringify(description.trim())}\n`;
      const url = URL.createObjectURL(new Blob([contents], {type:'text/plain;charset=utf-8'}));
      const link = document.createElement('a'); link.href = url; link.download = 'relicrat-collection-prompt.txt'; link.click();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
      setNotice('Prompt downloaded. Give it to your agent, answer its questions, then bring the JSON back here.');
    } catch (error) { setErrors([error instanceof Error ? error.message : 'Prompt download failed. Try again.']); }
    finally { lock.current = false; setBusy(false); }
  }
  async function validate() {
    if (lock.current || locked) return;
    lock.current = true; const version = generation.current;
    setBusy(true); setErrors([]); setPreview(null); setNotice('');
    try {
      if (new TextEncoder().encode(text).length > maximum) throw new Error('Collection JSON must be at most 64 KiB.');
      const response = await fetch('/api/v1/collection-proposals/preview', {method:'POST', headers:{'Content-Type':'application/json'}, body:text, signal:AbortSignal.timeout(30000)});
      const result = await response.json();
      if (version !== generation.current) return;
      if (!response.ok) {
        setErrors(Array.isArray(result.detail) ? result.detail.map((item: {path: string; message: string})=>`${item.path || 'document'}: ${item.message}`) : [typeof result.detail === 'string' ? result.detail : 'Validation unavailable. Check your sign-in and try again.']);
        return;
      }
      setPreview(result);
      requestAnimationFrame(()=>heading.current?.focus());
    } catch (error) {
      if (version === generation.current) setErrors([error instanceof Error ? error.message : 'Validation unavailable. Your draft is still here.']);
    } finally { lock.current = false; setBusy(false); }
  }
  async function createCollection() {
    if(lock.current||locked||!preview||!acknowledged)return;
    lock.current=true;setBusy(true);setErrors([]);
    try {await runSave(async()=>{
      const response=await fetch('/api/v1/custom-collections',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(preview.proposal),signal:AbortSignal.timeout(30000)});
      const result=await response.json();
      if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Create failed. Review the JSON and validate again.');
      setCreated(true);setNotice('Collection created. No owned copies were added. Add your figures in Your custom collections.');onCreated(result.id);
    });}catch(error){setErrors([error instanceof Error?error.message:'Creation could not be confirmed. Retrying the same definition is safe.']);}
    finally{lock.current=false;setBusy(false);}
  }
  const draft = preview?.proposal;
  return <details className="collection-authoring">
    <summary>Start a new collection</summary>
    <h2>Create a collection definition</h2>
    <p>Describe a figure collection, ask your agent to build its JSON, then review it here. Review the preview, then explicitly create an empty collection. Add your owned figures separately.</p>
    <label htmlFor="collection-description">What would you like to collect?</label>
    <textarea id="collection-description" value={description} maxLength={2000} rows={3} placeholder="The first ten original 1988 Playmates TMNT figures" disabled={locked || busy} onChange={event=>setDescription(event.target.value)} />
    <button type="button" disabled={locked || busy || !description.trim()} onClick={prompt}>Download agent prompt</button>
    <p className="hint">Only this description is included in the downloaded prompt. Your inventory and photos are not included.</p>
    <h3>Bring back the JSON</h3>
    <label htmlFor="collection-json-file">Upload collection JSON (64 KiB maximum)</label>
    <input id="collection-json-file" type="file" accept=".json,application/json" disabled={locked || busy} onChange={async event=>{
      const file = event.target.files?.[0]; event.target.value = '';
      if (!file) return;
      generation.current++; const version = generation.current; setPreview(null); setAcknowledged(false); setCreated(false); setErrors([]); setNotice('');
      if (file.size > maximum) { setErrors(['Collection JSON must be at most 64 KiB. Your previous text is still here.']); return; }
      try { const contents = await file.text(); if (version === generation.current) change(contents); }
      catch { if (version === generation.current) setErrors(['Could not read the file. Try again or paste the JSON.']); }
    }} />
    <label htmlFor="collection-json">Or paste collection JSON</label>
    <textarea id="collection-json" value={text} rows={10} disabled={locked || busy} onChange={event=>change(event.target.value)} spellCheck={false} />
    <button type="button" disabled={locked || busy || !text.trim()} onClick={validate}>{busy ? 'Working…' : 'Validate and preview'}</button>
    {notice && <p role="status">{notice}</p>}
    {!!errors.length && <div className="error" role="alert"><p>Collection setup needs attention. Your draft is still here.</p><ul>{errors.map((error,index)=><li key={index}>{error}</li>)}</ul></div>}
    {draft && <section aria-labelledby="collection-preview-heading">
      <h2 id="collection-preview-heading" ref={heading} tabIndex={-1}>{draft.collection.name}</h2>
      <p role="status">{preview.notice}</p>
      <p>{draft.collection.scope.manufacturer} · {draft.collection.scope.release_year} · {draft.collection.scope.assortment}</p>
      <p>{draft.collection.scope.later_reissues_included ? 'Later reissues included.' : 'Later reissues excluded.'} Variants do not add checklist requirements. Accessories and packaging do not gate completion.</p>
      <p>{draft.collection.completion.eligibility}</p>
      <h3>Entry form preview: {draft.type_definition.label}</h3>
      <p className="hint">Illustrative controls only. Nothing entered here is saved.</p>
      <fieldset disabled><legend>Sample entry fields</legend>
        <label>{draft.type_definition.title.label} (required)<input maxLength={draft.type_definition.title.max_length} /></label>
        {draft.type_definition.optional_fields.map(field=><CustomField key={field.id} field={field} value={undefined} change={()=>{}} />)}
      </fieldset>
      <p>Shared copy facilities: {draft.type_definition.shared_copy_fields.map(field=>({notes:'Notes',photos:'Photos',storage_location:'Storage location'}[field] || field)).join(', ') || 'none selected'}.</p>
      <h3>Checklist: {draft.collection.checklist.length} entries</h3>
      <p>Ownership and completion have not been evaluated. These are goals, not owned copies.</p>
      <ul>{draft.collection.checklist.map(entry=><li key={entry.id}>{entry.title} </li>)}</ul>
      <h3>Evidence to review</h3>
      <p>Links are displayed as text. RelicRat has not fetched or verified these sources.</p>
      <ul>{draft.sources.map(source=><li key={source.id}>{source.supports}<p>{source.url}</p></li>)}</ul>
      {!!draft.uncertainties.length && <><h3>Uncertainties</h3><ul>{draft.uncertainties.map((value,index)=><li key={index}>{value}</li>)}</ul></>}
      <label><input type="checkbox" checked={acknowledged} disabled={locked||busy||created} onChange={event=>setAcknowledged(event.target.checked)} /> I reviewed the fields, scope and checklist. Creating this collection will not mark anything as owned.</label>
      <button type="button" disabled={locked||busy||!acknowledged||created} onClick={()=>void createCollection()}>{created?'Collection created':'Create collection'}</button>
      <p>Importing the original definition again reopens its collection. Use Configure field controls to review compatible changes with retained definition history.</p>
    </section>}
  </details>;
}
