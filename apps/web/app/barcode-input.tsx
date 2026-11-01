'use client';

import {useState} from 'react';
import BarcodeLookup from './barcode-lookup';
import BarcodeScanner from './barcode-scanner';
import type { BarcodeReading,CollectionType } from '../lib/inventory-client';

type Props = {
 value: BarcodeReading | null; change: (value: BarcodeReading | null) => void;
 formats: string[]; locked: boolean; saved?:boolean; definition?:CollectionType; values?:Record<string,string>; apply?:(fields:Record<string,string>)=>void;
};

/** A page-local observation. Only the enclosing copy form persists it. */
export default function BarcodeInput({value,change,formats,locked,saved=false,definition,values,apply}:Props){
 const [requested,setRequested]=useState(0),[scannerOpen,setScannerOpen]=useState(false);
 const lookup=definition?.lookup&&apply&&values;
 return <div className="barcode-input">
  <BarcodeScanner disabled={locked || !formats.length} formats={formats} onUse={reading=>{setRequested(0);change(reading);}} replacing={!!value} onOpenChange={open=>{setScannerOpen(open);if(open)setRequested(0);}} onLookup={lookup?reading=>{change(reading);setRequested(n=>n+1);}:undefined}/>
  {value && <div>
   <p><strong>{saved?'Saved barcode':'Barcode in this draft'}</strong></p>
   <dl><dt>Barcode</dt><dd>{value.value}</dd><dt>Format</dt><dd>{value.format.replaceAll('_','-')}</dd><dt>Supplement</dt><dd>{value.supplement || 'Not detected'}</dd></dl>
   <p className="hint">{saved?'A barcode is an observation, not a confirmed edition.':'Use the form’s save button to keep this change. A barcode does not confirm the edition.'}</p>
   <button type="button" disabled={locked} onClick={()=>{setRequested(0);change(null);}}>Remove barcode from draft</button>
   {lookup&&!scannerOpen&&<BarcodeLookup key={`${definition.id}-${value.value}-${value.format}-${value.supplement||''}`} definition={definition} reading={value} values={values} apply={apply} requested={requested} locked={locked}/>}
  </div>}
 </div>;
}
