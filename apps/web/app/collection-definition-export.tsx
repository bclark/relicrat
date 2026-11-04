'use client';
import {useEffect,useRef,useState} from 'react';
import {api,errorText,jsonSave} from '../lib/inventory-client';

export default function CollectionDefinitionExport({collectionId,locked}:{collectionId:string;locked:boolean}){
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const pending=useRef<AbortController|null>(null);
 useEffect(()=>()=>pending.current?.abort(),[]);
 async function download(){
  if(locked||pending.current)return;
  const controller=new AbortController();pending.current=controller;setBusy(true);setError('');setNotice('');
  try{
   const saved=await api<{proposal:Record<string,unknown>}>(`custom-collections/${collectionId}`,{signal:controller.signal});
   const {draft_format,status,type_definition,collection,sources,uncertainties}=saved.proposal;
   const checked=await api<{proposal:Record<string,unknown>}>('collection-proposals/preview',{...jsonSave({draft_format,status,type_definition,collection,sources,uncertainties}),signal:controller.signal});
   let contents=JSON.stringify(checked.proposal,null,2);
   if(new TextEncoder().encode(contents).length>65536)contents=JSON.stringify(checked.proposal);
   if(new TextEncoder().encode(contents).length>65536)throw new Error('This definition exceeds the 64 KiB import limit. No file was downloaded.');
   if(controller.signal.aborted)return;
   const url=URL.createObjectURL(new Blob([contents],{type:'application/json'}));
   try{const link=document.createElement('a');link.href=url;link.download='relicrat-collection.json';link.click();}
   finally{setTimeout(()=>URL.revokeObjectURL(url),1000);}
   setNotice('Collection JSON downloaded. Use Start a new collection to import, validate and review it.');
  }catch(e){if(!controller.signal.aborted)setError(errorText(e));}
  finally{if(!controller.signal.aborted){pending.current=null;setBusy(false);}}
 }
 return <section aria-label="Export collection definition"><button type="button" disabled={locked||busy} onClick={()=>void download()}>{busy?'Preparing collection JSON…':'Export collection JSON'}</button><p>Includes saved field controls, checklist, scope and sources. Owned figures and their personal details are excluded.</p>{error&&<p role="alert" className="error">Collection JSON could not be exported. {error} Your saved collection and drafts are unchanged.</p>}{notice&&<p role="status">{notice}</p>}</section>;
}
