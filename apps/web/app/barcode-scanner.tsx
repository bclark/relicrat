'use client';
import {useEffect,useRef,useState} from 'react';
import {readBarcode,startBarcodeCamera} from '../lib/barcode-camera.mjs';

export default function BarcodeScanner(){
 const [open,setOpen]=useState(false),[phase,setPhase]=useState<'off'|'starting'|'scanning'|'read'>('off');
 const [reading,setReading]=useState<ReturnType<typeof readBarcode>>(null),[error,setError]=useState('');
 const container=useRef<HTMLDivElement>(null),session=useRef<ReturnType<typeof startBarcodeCamera>|null>(null),resultHeading=useRef<HTMLHeadingElement>(null),launchButton=useRef<HTMLButtonElement>(null);
 const active=phase==='starting'||phase==='scanning';
 function stop(){session.current?.stop();session.current=null;setPhase('off');}
 useEffect(()=>{
  function leave(){session.current?.stop();session.current=null;setPhase('off');}
  function hidden(){if(document.hidden)leave();}
  document.addEventListener('visibilitychange',hidden);window.addEventListener('pagehide',leave);
  return()=>{session.current?.stop();document.removeEventListener('visibilitychange',hidden);window.removeEventListener('pagehide',leave);};
 },[]);
 useEffect(()=>{if(phase==='read')resultHeading.current?.focus();},[phase]);
 function start(){
  if(session.current||!container.current)return;
  setOpen(true);setReading(null);setError('');setPhase('starting');
  session.current=startBarcodeCamera(container.current,{
   onReady:()=>setPhase('scanning'),
   onResult:value=>{session.current=null;setReading(value);setPhase('read');},
   onError:message=>{session.current=null;setError(message);setPhase('off');},
  });
 }
 function close(){stop();setOpen(false);setReading(null);setError('');launchButton.current?.focus();}
 return <section className="barcode-scanner" aria-label="Barcode scanning trial">
  <button type="button" ref={launchButton} onClick={active?stop:start}>{active?'Stop camera':reading?'Scan another barcode':open?'Start camera':'Scan barcode'}</button>
  <div hidden={!open}>
   <h2>Try barcode scanning</h2><p>Read a UPC or EAN barcode. This trial keeps the reading on this page; nothing is added to your collection or sent for lookup.</p>
   <div className="barcode-camera" ref={container} hidden={phase!=='starting'&&phase!=='scanning'}/>
   {active&&<p role="status">{phase==='starting'?'Waiting for camera access…':'Hold the barcode steady and keep the bars in view.'}</p>}
   <button type="button" onClick={close}>Close scanner</button>
   {error&&<p className="error" role="alert">{error}</p>}
   {reading&&<div><h3 tabIndex={-1} ref={resultHeading}>Barcode read</h3><p role="status">Camera stopped. This reading has not been saved.</p><dl><dt>Barcode</dt><dd>{reading.value}</dd><dt>Format</dt><dd>{reading.format.replaceAll('_','-')}</dd><dt>Supplement</dt><dd>{reading.supplement||'Not detected'}</dd></dl><p>A barcode is a clue, not a confirmed edition. Comics may have a separate small supplement identifying an issue or variant; this trial does not identify the comic.</p></div>}
  </div>
 </section>;
}
