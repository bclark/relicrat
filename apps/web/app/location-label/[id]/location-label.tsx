'use client';
import {BarcodeFormat,QRCodeWriter} from '@zxing/library';
import {useEffect,useMemo,useState} from 'react';
import {api,errorText,type Location} from '../../../lib/inventory-client';
import {locationLink} from '../../../lib/location-link';

export default function LocationLabel({id,url}: {id:string;url:string}) {
  const [location,setLocation]=useState<Location|null>(null);
  const [error,setError]=useState('');
  useEffect(()=>{
    const controller=new AbortController();
    api<Location>(`storage-locations/${id}`,{signal:controller.signal})
      .then(place=>{if(!controller.signal.aborted)setLocation(place);})
      .catch(problem=>{if(!controller.signal.aborted)setError(errorText(problem));});
    return ()=>controller.abort();
  },[id]);

  const qr=useMemo(()=>{
    const matrix=new QRCodeWriter().encode(url,BarcodeFormat.QR_CODE,0,0,new Map());
    let path='';
    for(let y=0;y<matrix.getHeight();y++){
      for(let x=0;x<matrix.getWidth();x++){
        if(matrix.get(x,y))path+=`M${x} ${y}h1v1h-1z`;
      }
    }
    return {size:matrix.getWidth(),path};
  },[url]);

  return <main className="location-label">
    <div className="location-label-controls">
      <a href={locationLink(id)}>Back to location</a>
      <button type="button" disabled={!location} onClick={()=>window.print()}>Print label</button>
    </div>
    {error?<p role="alert" className="error">{error}</p>:!location?<p role="status">Loading label…</p>:
      <article className="location-label-card">
        <h1>{location.name}</h1>
        <svg role="img" aria-label="Location QR code" xmlns="http://www.w3.org/2000/svg" width="160" height="160"
          viewBox={`0 0 ${qr.size} ${qr.size}`} shapeRendering="crispEdges">
          <rect width={qr.size} height={qr.size} fill="white" />
          <path d={qr.path} fill="black" />
        </svg>
        <p className="location-label-controls">Scan with your phone camera on your private RelicRat network.</p>
      </article>}
  </main>;
}
