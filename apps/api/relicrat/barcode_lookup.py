"""Owner-only, read-only suggestions. Confirmation changes a browser draft only."""
import re
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel,ConfigDict,Field,ValidationError
from relicrat.barcodes import BarcodeReading
from relicrat.barcode_providers import PROVIDERS
from relicrat.collection_types import COLLECTION_TYPES
from relicrat.barcode_errors import LookupBusy,LookupUnavailable,LookupTimeout

router=APIRouter(prefix='/api/v1/barcode-lookups',tags=['barcode lookup'])

class Candidate(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')
    title:str=Field(min_length=1,max_length=500,pattern=r'^[^\x00]*$')
    description:str=Field(max_length=1000,pattern=r'^[^\x00]*$')
    source_url:str=Field(max_length=1000)
    fields:dict[str,str]=Field(max_length=20)


def configured(collection_type):
    definition=COLLECTION_TYPES[collection_type];config=definition.lookup
    if config is None:raise HTTPException(404,'Barcode lookup is not configured for this collection type.')
    return definition,config,PROVIDERS[config.provider]


@router.post('/{collection_type}')
def lookup(collection_type:Literal['record','comic','other'],reading:BarcodeReading):
    definition,config,provider=configured(collection_type)
    if reading.format not in definition.barcode_formats:raise HTTPException(422,'Barcode format is not supported for this collection type.')
    try:raw=provider['search'](reading,config.max_results)
    except LookupBusy:raise HTTPException(429,'Lookup is busy. Wait a moment, then try again; manual entry is available.',headers={'Retry-After':'1'}) from None
    except LookupTimeout:raise HTTPException(504,'The catalog took too long to respond. Try again or enter details manually.') from None
    except LookupUnavailable:raise HTTPException(503,'Lookup provider is unavailable. Try again later or enter details manually.') from None
    if not isinstance(raw,list):raise HTTPException(502,'Lookup provider returned an invalid response. Manual entry is available.')
    limits={field.key:field.max_length for field in [definition.title,*definition.fields]}
    candidates=[];seen=set()
    for value in raw[:config.max_results]:
        try:row=Candidate.model_validate(value)
        except ValidationError:continue
        try:
            url=urlsplit(row.source_url)
            valid_url=url.scheme=='https' and not url.username and not url.password and url.port in (None,443) and f'https://{url.hostname}'==provider['source_origin']
        except ValueError:valid_url=False
        if not valid_url:continue
        fields={}
        for target,source in config.field_mappings.items():
            text=row.fields.get(source)
            if not isinstance(text,str):continue
            text=config.value_maps.get(target,{}).get(text,text).strip()
            if text and len(text)<=limits[target] and not any(ord(c)<32 for c in text):fields[target]=text
        if not fields.get('title') or row.id in seen:continue
        seen.add(row.id)
        candidates.append({'id':row.id,'title':row.title,'description':row.description,'source_url':row.source_url,'fields':fields,
                           'cover_url':f'/api/v1/barcode-lookups/{collection_type}/{row.id}/cover' if config.cover_art and provider.get('cover') else None})
    return {'provider':config.provider,'provider_label':provider['label'],'candidates':candidates}


@router.get('/{collection_type}/{candidate_id}/cover')
def cover(collection_type:Literal['record','comic','other'],candidate_id:str):
    _,config,provider=configured(collection_type)
    if not config.cover_art or not provider.get('cover') or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',candidate_id):raise HTTPException(404,'Cover preview unavailable.')
    try:content=provider['cover'](candidate_id)
    except LookupUnavailable:raise HTTPException(404,'Cover preview unavailable.') from None
    return Response(content,media_type='image/jpeg',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
