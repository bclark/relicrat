'use client';
import {useEffect,useState} from 'react';
import {api,errorText,type CollectionTypeId,type InventoryCopy} from '../lib/inventory-client';
import CollectionRows from './collection-rows';
type Group={collection_type:CollectionTypeId;value:string|null;label:string;copy_count:number};
export default function GroupedCollection({type,noun,filters,refresh,busy,selected,open,chooseType}:{type:''|'comic'|'record'|'movie';noun:string;filters:string;refresh:number;busy:boolean;selected:string|null;open:(id:string)=>void;chooseType:(type:CollectionTypeId)=>void}){
 const [groups,setGroups]=useState<Group[]>([]),[groupPage,setGroupPage]=useState(0),[active,setActive]=useState<Group|null>(null),[page,setPage]=useState(0);
 const [items,setItems]=useState<InventoryCopy[]>([]),[more,setMore]=useState(false),[loading,setLoading]=useState(true),[error,setError]=useState(''),[reading,setReading]=useState(false),[readError,setReadError]=useState('');
 useEffect(()=>{const controller=new AbortController();setLoading(true);setError('');
  api<Group[]>(`collection-groups?limit=21&offset=${groupPage*20}${filters}`,{signal:controller.signal}).then(result=>{if(!controller.signal.aborted)setGroups(result);}).catch(e=>{if(!controller.signal.aborted)setError(errorText(e));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();
 },[filters,groupPage,refresh]);
 useEffect(()=>{if(!active)return;const controller=new AbortController();setReading(true);setReadError('');
  api<InventoryCopy[]>(`inventory?limit=21&offset=${page*20}${filters}&group=${encodeURIComponent(active.value||'')}`,{signal:controller.signal}).then(result=>{if(!controller.signal.aborted){setItems(result.slice(0,20));setMore(result.length>20);}}).catch(e=>{if(!controller.signal.aborted)setReadError(errorText(e));}).finally(()=>{if(!controller.signal.aborted)setReading(false);});return()=>controller.abort();
 },[active,filters,page,refresh]);
 const label=type?noun.toLowerCase():'collection types';
 return <div><p className="hint">{type?`Browse saved ${label}.`:'Choose a collection type to browse its groups.'} Grouping never merges physical copies.</p>
  <p role="status">{loading?'Loading groups…':error?'Groups unavailable':`${label.charAt(0).toUpperCase()+label.slice(1)} on this page: ${Math.min(groups.length,20)}`}</p>
  {error?<p className="error" role="alert">{error} Use Reload inventory to try again.</p>:loading?null:!groups.length?<p>No matching groups. Try another type, search or storage filter.</p>:<ul className="inventory-list">{groups.slice(0,20).map(group=>{
   const expanded=!!active&&active.value===group.value&&active.collection_type===group.collection_type;
   return <li key={JSON.stringify([group.collection_type,group.value])}><button className="inventory-row" disabled={busy} aria-expanded={type?expanded:undefined} onClick={()=>{if(!type){chooseType(group.collection_type);return;}setReading(!expanded);setItems([]);setMore(false);setActive(expanded?null:group);setPage(0);}}><strong>{group.label}</strong><span>{group.copy_count} {group.copy_count===1?'copy':'copies'}{type?expanded?' · Close group':' · Open group':' · Browse collection'}</span></button>
    {expanded&&<section className="collection-group-members" aria-label={`${group.label} copies`}>
     <div role="status">{reading?'Loading group copies…':readError?'Group unavailable':`${items.length} ${items.length===1?'copy':'copies'} on this group page`}</div>
     {readError?<p className="error" role="alert">{readError} Use Reload inventory to try again.</p>:reading?null:!items.length?<p>No copies on this page. Go back a page or reload the inventory.</p>:<CollectionRows items={items} busy={busy} selected={selected} open={open}/>}
     <nav className="pagination" aria-label="Group copy pages"><button disabled={busy||reading||!page} onClick={()=>{setReading(true);setItems([]);setPage(page-1);}}>Previous copies</button><span>Copy page {page+1}</span><button disabled={busy||reading||!!readError||!more} onClick={()=>{setReading(true);setItems([]);setPage(page+1);}}>Next copies</button></nav>
    </section>}
   </li>;
  })}</ul>}
  <nav className="pagination" aria-label="Collection group pages"><button disabled={busy||loading||!groupPage} onClick={()=>{setGroupPage(groupPage-1);setActive(null);}}>Previous groups</button><span>Group page {groupPage+1}</span><button disabled={busy||loading||!!error||groups.length<=20} onClick={()=>{setGroupPage(groupPage+1);setActive(null);}}>Next groups</button></nav>
 </div>;
}
