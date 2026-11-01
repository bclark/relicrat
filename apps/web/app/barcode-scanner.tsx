'use client';
import {useEffect,useRef,useState} from 'react';
import type {BarcodeReading} from '../lib/inventory-client';
import {readBarcode,startBarcodeCamera} from '../lib/barcode-camera.mjs';

type Props={disabled?:boolean;formats?:string[];onUse?:(reading:BarcodeReading)=>void;replacing?:boolean};
export default function BarcodeScanner({disabled=false,formats,onUse,replacing=false}:Props){
 const [open,setOpen]=useState(false),[phase,setPhase]=useState<'off'|'starting'|'scanning'|'read'>('off');
 const [reading,setReading]=useState<ReturnType<typeof readBarcode>>(null),[error,setError]=useState('');
 const container=useRef<HTMLDivElement>(null),session=useRef<ReturnType<typeof startBarcodeCamera>|null>(null),resultHeading=useRef<HTMLHeadingElement>(null),launchButton=useRef<HTMLButtonElement>(null);
 const active=phase==='starting'||phase==='scanning';
 useEffect(()=>{if(disabled){session.current?.stop();session.current=null;setPhase('off');}},[disabled]);
 function stop(){session.current?.stop();session.current=null;setPhase('off');}
 useEffect(()=>{
  function leave(){session.current?.stop();session.current=null;setPhase('off');}
  function hidden(){if(document.hidden)leave();}
  document.addEventListener('visibilitychange',hidden);window.addEventListener('pagehide',leave);
  return()=>{session.current?.stop();document.removeEventListener('visibilitychange',hidden);window.removeEventListener('pagehide',leave);};
 },[]);
 useEffect(()=>{if(phase==='read')resultHeading.current?.focus();},[phase]);
 function start(){
  if(disabled||session.current||!container.current)return;
  setOpen(true);setReading(null);setError('');setPhase('starting');
  session.current=startBarcodeCamera(container.current,{
   onReady:()=>setPhase('scanning'),
   onResult:value=>{session.current=null;if(formats && !formats.includes(value.format)){setError('This barcode format is not supported for this collection type.');setPhase('off');return;}setReading(value);setPhase('read');},
   onError:message=>{session.current=null;setError(message);setPhase('off');},
  });
 }
 function close(){stop();setOpen(false);setReading(null);setError('');launchButton.current?.focus();}
 return <section className="barcode-scanner" aria-label="Barcode scanning trial">
  <button type="button" disabled={disabled} ref={launchButton} onClick={active?stop:start}>{active?'Stop camera':reading?'Scan another barcode':open?'Start camera':'Scan barcode'}</button>
  <div hidden={!open}>
   <h2>Scan a barcode</h2><p>Read a UPC or EAN barcode. Nothing is saved or sent for lookup. {onUse && "Choose Use barcode, then save the copy to keep it."}</p>
   <div className="barcode-camera" ref={container} hidden={phase!=='starting'&&phase!=='scanning'}/>
   {active&&<p role="status">{phase==='starting'?'Waiting for camera access…':'Hold the barcode steady and keep the bars in view.'}</p>}
   <button type="button" onClick={close}>Close scanner</button>
   {error&&<p className="error" role="alert">{error}</p>}
   {reading&&<div><h3 tabIndex={-1} ref={resultHeading}>Barcode read</h3><p role="status">Camera stopped. This reading has not been saved.</p><dl><dt>Barcode</dt><dd>{reading.value}</dd><dt>Format</dt><dd>{reading.format.replaceAll('_','-')}</dd><dt>Supplement</dt><dd>{reading.supplement||'Not detected'}</dd></dl><p>A barcode is a clue, not a confirmed edition. Comics may have a separate small supplement identifying an issue or variant; this scanner does not identify the comic.</p>{onUse&&<button type="button" disabled={disabled} onClick={()=>{const value=reading;close();onUse(value);}}>{replacing?'Replace draft barcode':'Use barcode'}</button>}</div>}
  </div>
 </section>;
}
