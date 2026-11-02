import {useId} from 'react';
import {copyName,type CollectionTypeId,type CollectionTypes,type InventoryCopy} from '../lib/inventory-client';

type Props={items:InventoryCopy[];busy:boolean;selected:string|null;open:(id:string)=>void;groupByType?:boolean;types?:CollectionTypes|null};

export default function CollectionRows({items,busy,selected,open,groupByType=false,types}:Props){
 const headingId=useId();
 function rows(copies:InventoryCopy[]){
  return <ul className="inventory-list">{copies.map(copy=><li key={copy.id}>
   <button disabled={busy} className="inventory-row copy-row" aria-label={`Open ${copyName(copy)}${copy.edition_label?` · ${copy.edition_label}`:''}`} aria-pressed={copy.id===selected} onClick={()=>open(copy.id)}>
    <span className="copy-identity"><strong>{copyName(copy)}</strong>{copy.edition_label&&<span className="copy-edition">{copy.edition_label}</span>}</span>
    <span className="copy-location">{copy.storage_location_id?'Location assigned':'Unassigned'}</span>
   </button>
  </li>)}</ul>;
 }
 if(!groupByType)return rows(items);
 const labels:Record<CollectionTypeId,string>={record:'Albums',comic:'Comics',movie:'Movies',other:'Other finds'};
 return <div className="copy-type-groups">{(Object.keys(labels) as CollectionTypeId[]).map(type=>{
  const copies=items.filter(copy=>copy.collection_type===type);
  return copies.length?<section className="copy-type-group" key={type} aria-labelledby={`${headingId}-${type}`}>
   <div className="copy-group-heading"><h3 id={`${headingId}-${type}`}>{types?.[type]?.plural_label||labels[type]}</h3><span>{copies.length} on this page</span></div>
   {rows(copies)}
  </section>:null;
 })}</div>;
}
