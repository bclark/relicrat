'use client';

import BarcodeScanner from './barcode-scanner';
import type { BarcodeReading } from '../lib/inventory-client';

type Props = {
 value: BarcodeReading | null; change: (value: BarcodeReading | null) => void;
 formats: string[]; locked: boolean; saved?:boolean;
};

/** A page-local observation. Only the enclosing copy form persists it. */
export default function BarcodeInput({value,change,formats,locked,saved=false}:Props){
 return <div className="barcode-input">
  <BarcodeScanner disabled={locked || !formats.length} formats={formats} onUse={change} replacing={!!value}/>
  {value && <div>
   <p><strong>{saved?'Saved barcode':'Barcode in this draft'}</strong></p>
   <dl><dt>Barcode</dt><dd>{value.value}</dd><dt>Format</dt><dd>{value.format.replaceAll('_','-')}</dd><dt>Supplement</dt><dd>{value.supplement || 'Not detected'}</dd></dl>
   <p className="hint">{saved?'A barcode is an observation, not a confirmed edition.':'Use the form’s save button to keep this change. A barcode does not confirm the edition.'}</p>
   <button type="button" disabled={locked} onClick={()=>change(null)}>Remove barcode from draft</button>
  </div>}
 </div>;
}
