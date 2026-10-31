"""Bounded, explicit CSV intake. Source rows are evidence, never catalog authority."""
import csv
import hashlib
import io
import json
import uuid
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from relicrat.database import get_db
from relicrat.intake import CreateProvisionalCopy, stage_copy
from relicrat.models import ImportBatch, ImportCopy

router=APIRouter(prefix='/api/v1/imports',tags=['imports'])
MAX_BYTES=4*1024*1024
Source=Literal['clz','discogs']
MAPPINGS={
 'clz':{'Series':'Title','Issue':'Issue number','Publisher':'Publisher','Variant Description':'Edition (falls back to Variant)','Notes':'Notes','Quantity':'Physical copies'},
 'discogs':{'Title':'Title','Artist':'Artist','Format':'Format (full description)','Collection Notes':'Notes'},
}
REQUIRED={'clz':{'Series','Issue','Publisher','Quantity','Collection Status'},'discogs':{'Title','Artist','Format','release_id'}}


def parse_csv(source: Source, raw: bytes):
    if not raw or len(raw)>MAX_BYTES:
        raise HTTPException(413,'Choose a nonempty CSV of at most 4 MiB')
    try:
        text=raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise HTTPException(422,'Export a UTF-8 CSV file') from None
    if '\x00' in text:
        raise HTTPException(422,'CSV contains unsupported NUL characters')
    reader=csv.reader(io.StringIO(text,newline=''),strict=True)
    try:
        headers=next(reader)
        if not headers or len(headers)>100 or len(set(headers))!=len(headers) or any(not h.strip() or len(h)>120 for h in headers):
            raise HTTPException(422,'Use unique nonempty column headers (at most 100 columns)')
        if not REQUIRED[source].issubset(headers):
            raise HTTPException(422,'Required columns are missing. Choose the matching CLZ or Discogs export format.')
        rows=[];errors=[];copies=0;ids=set();repeated=0;retained_bytes=0
        for number,values in enumerate(reader,2):
            if number>5001:
                raise HTTPException(422,'Import at most 5,000 rows per file')
            if len(values)!=len(headers):
                raise HTTPException(422,f'Row {number} has a different number of columns')
            original=dict(zip(headers,values))
            value=lambda key: original.get(key,'').strip()
            try:
                if source=='clz':
                    if value('Collection Status')!='In Collection':
                        raise ValueError('Only In Collection rows can create owned copies')
                    q=value('Quantity')
                    if not q.isascii() or not q.isdecimal() or not 1<=int(q)<=10000:
                        raise ValueError('Quantity must be a whole number from 1 to 10,000')
                    quantity=int(q)
                    payload=CreateProvisionalCopy(title=value('Series'),collection_type='comic',comic_details={k:v for k,v in {'issue_number':value('Issue'),'publisher':value('Publisher')}.items() if v},edition_label=value('Variant Description') or value('Variant') or None,description=value('Notes') or None)
                    external=value('Core ComicID')
                else:
                    quantity=1
                    payload=CreateProvisionalCopy(title=value('Title'),collection_type='record',record_details={k:v for k,v in {'artist':value('Artist'),'format':value('Format')}.items() if v},description=value('Collection Notes') or None)
                    external=value('release_id')
                if not payload.title:
                    raise ValueError('A series or album title is required')
            except (ValueError,ValidationError):
                if len(errors)<50: errors.append({'row':number,'message':'Check title, field lengths, ownership status and positive whole quantity.'})
                continue
            if external:
                repeated+=external in ids;ids.add(external)
            retained_bytes+=len(json.dumps(original).encode())*quantity
            if retained_bytes>16*1024*1024: raise HTTPException(422,'Expanded source data exceeds 16 MiB; split the file into smaller imports')
            copies+=quantity
            if copies>10000: raise HTTPException(422,'Import at most 10,000 physical copies per file')
            rows.append((number,original,payload,quantity))
    except (csv.Error,StopIteration):
        raise HTTPException(422,'CSV is empty, malformed or contains an oversized field') from None
    if not rows and not errors: raise HTTPException(422,'CSV has no inventory rows')
    return {'sha256':hashlib.sha256(raw).hexdigest(),'rows':rows,'copy_count':copies,'errors':errors,'repeated_external_ids':repeated,'headers':headers}


def batch_info(batch):
    return {'id':str(batch.id),'source':batch.source,'sha256':batch.sha256,'parser_version':batch.parser_version,'row_count':batch.row_count,'copy_count':batch.copy_count,'created_at':batch.created_at}


def preview_import(source,raw,db):
    parsed=parse_csv(source,raw)
    existing=db.scalar(select(ImportBatch).where(ImportBatch.source==source,ImportBatch.sha256==parsed['sha256']))
    return {'sha256':parsed['sha256'],'parser_version':1,'row_count':len(parsed['rows']),'copy_count':parsed['copy_count'],'errors':parsed['errors'],'repeated_external_ids':parsed['repeated_external_ids'],'mapping':MAPPINGS[source],'preserved_columns':parsed['headers'],'existing_batch':batch_info(existing) if existing else None,'sample':[{'row':n,'quantity':q,**p.model_dump()} for n,_,p,q in parsed['rows'][:10]]}


def commit_import(source,raw,reviewed_sha256,db):
    parsed=parse_csv(source,raw)
    if reviewed_sha256!=parsed['sha256']:
        raise HTTPException(409,'The file changed. Preview it again before importing.')
    if parsed['errors']:
        raise HTTPException(422,'Correct every reported row before importing. No copies were imported.')
    try:
        # The unique insert serializes simultaneous retries, including an uncertain
        # response. Everything is committed together; matching catalog IDs do not deduplicate ownership.
        ident=db.scalar(insert(ImportBatch).values(id=uuid.uuid4(),source=source,sha256=parsed['sha256'],parser_version=1,row_count=len(parsed['rows']),copy_count=parsed['copy_count']).on_conflict_do_nothing(index_elements=['source','sha256']).returning(ImportBatch.id))
        if ident is None:
            batch=db.scalar(select(ImportBatch).where(ImportBatch.source==source,ImportBatch.sha256==parsed['sha256']))
            result={'batch':batch_info(batch),'already_imported':True};db.commit();return result
        for number,original,payload,quantity in parsed['rows']:
            for index in range(1,quantity+1):
                copy=stage_copy(db,payload);db.flush()
                db.add(ImportCopy(owned_copy_id=copy.id,batch_id=ident,row_number=number,copy_number=index,source_row=original))
        db.flush();result={'batch':batch_info(db.get(ImportBatch,ident)),'already_imported':False};db.commit();return result
    except Exception:
        db.rollback();raise


async def csv_body(request: Request):
    if request.headers.get('content-type','').split(';')[0].strip()!='text/csv':
        raise HTTPException(415,'Choose a CSV file')
    raw=bytearray()
    async for chunk in request.stream():
        if len(raw)+len(chunk)>MAX_BYTES: raise HTTPException(413,'CSV must be at most 4 MiB')
        raw.extend(chunk)
    return bytes(raw)


@router.post('/preview')
async def preview(request: Request,source: Source,db: Session=Depends(get_db)):
    raw=await csv_body(request)
    return await run_in_threadpool(preview_import,source,raw,db)


@router.post('/commit')
async def commit(request: Request,source: Source,reviewed_sha256: str=Query(pattern='^[0-9a-f]{64}$'),db: Session=Depends(get_db)):
    raw=await csv_body(request)
    return await run_in_threadpool(commit_import,source,raw,reviewed_sha256,db)


@router.get('')
def batches(limit: int=Query(default=20,ge=1,le=100),offset: int=Query(default=0,ge=0),db: Session=Depends(get_db)):
    return [batch_info(b) for b in db.scalars(select(ImportBatch).order_by(ImportBatch.created_at.desc(),ImportBatch.id.desc()).limit(limit).offset(offset))]


@router.get('/{batch_id}/rows')
def source_rows(batch_id: UUID,limit: int=Query(default=20,ge=1,le=100),offset: int=Query(default=0,ge=0),db: Session=Depends(get_db)):
    if db.get(ImportBatch,batch_id) is None: raise HTTPException(404,'Import batch not found')
    return [{'copy_id':str(r.owned_copy_id),'row':r.row_number,'copy_number':r.copy_number,'source':r.source_row} for r in db.scalars(select(ImportCopy).where(ImportCopy.batch_id==batch_id).order_by(ImportCopy.row_number,ImportCopy.copy_number).limit(limit).offset(offset))]
