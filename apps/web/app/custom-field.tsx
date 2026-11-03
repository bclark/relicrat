'use client';
import {useId} from 'react';
export type CustomValue=string|boolean|string[];
export type CustomValues=Record<string,CustomValue>;
export type CustomFieldDefinition={id:string;label:string;input?:'text'|'select'|'radio'|'checkbox'|'checkboxes';max_length:number;options?:string[]};
export type CustomTypeDefinition={id:string;label:string;plural_label:string;title:{label:string;required:true;max_length:number};optional_fields:CustomFieldDefinition[];shared_copy_fields:string[];lookup:null};
export function normalizeCustomValues(values:CustomValues):CustomValues{return Object.fromEntries(Object.entries(values).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,typeof v==='string'?v.trim():v]).filter(([,v])=>typeof v!=='string'||v!==''));}
export function replaceCustomValue(values:CustomValues,key:string,value:CustomValue|undefined):CustomValues{const next={...values};if(value===undefined)delete next[key];else next[key]=value;return next;}
export function customValueText(value:CustomValue|undefined|null):string{return value==null?'Not recorded':typeof value==='boolean'?(value?'Yes':'No'):Array.isArray(value)?(value.length?value.join(', '):'None selected'):value;}
export default function CustomField({field,value,change}:{field:CustomFieldDefinition;value:CustomValue|undefined;change:(value:CustomValue|undefined)=>void}){
 const id=useId(),options=field.options||[],control=field.input||'text',label=field.label+' (optional)';
 const invalidScalar=value!==undefined&&(control==='checkbox'?typeof value!=='boolean':typeof value!=='string');
 const warning=invalidScalar&&<p role="status">Value needs review: {customValueText(value)}. <button type="button" onClick={()=>change(undefined)}>Clear {field.label}</button></p>;
 if(control==='text')return <>{warning}<label>{label}<input maxLength={field.max_length} value={typeof value==='string'?value:''} onChange={e=>change(e.target.value||undefined)} /></label></>;
 if(control==='select')return <>{warning}<label htmlFor={id}>{label}</label><select id={id} value={typeof value==='string'?value:''} onChange={e=>change(e.target.value||undefined)}><option value="">Not recorded</option>{typeof value==='string'&&!options.includes(value)&&<option value={value}>{value} — review this value</option>}{options.map(option=><option key={option} value={option}>{option}</option>)}</select></>;
 if(control==='checkbox')return <fieldset><legend>{label}</legend>{warning}<label className="custom-choice"><input type="checkbox" checked={value===true} aria-checked={value===undefined?'mixed':value===true} ref={node=>{if(node)node.indeterminate=value===undefined;}} onChange={e=>change(e.target.checked)} />{field.label}</label><p className="hint">{customValueText(value)}</p><button type="button" disabled={value===undefined} onClick={()=>change(undefined)}>Clear {field.label}</button></fieldset>;
 const multiple=control==='checkboxes',selected=Array.isArray(value)?value:[];
 const unsupported=value!==undefined&&(multiple?(!Array.isArray(value)||selected.some(v=>!options.includes(v))):(typeof value!=='string'||!options.includes(value)));
 return <fieldset><legend>{label}</legend>{unsupported&&<p role="status">Value needs review: {customValueText(value)}. Choose a supported value or clear it.</p>}
 {!multiple&&<label className="custom-choice"><input type="radio" name={id} checked={value===undefined} onChange={()=>change(undefined)} />Not recorded</label>}
 {options.map(option=><label className="custom-choice" key={option}><input type={multiple?'checkbox':'radio'} name={id} checked={multiple?selected.includes(option):value===option} onChange={e=>change(multiple?options.filter(v=>v===option?e.target.checked:selected.includes(v)):option)} />{option}</label>)}
 {multiple&&<><p className="hint">{customValueText(value)}</p><button type="button" disabled={value===undefined} onClick={()=>change(undefined)}>Clear {field.label}</button></>}
 </fieldset>;
}
