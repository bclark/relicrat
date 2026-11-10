"""Bounded, explicit CSV intake. Source rows are evidence, never catalog authority."""
import base64
import binascii
import csv
import hashlib
import io
import json
import re
import uuid
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy import String, cast, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased
from relicrat.database import get_db
from relicrat.import_duplicates import (
    EXTERNAL_ID_COLUMNS, ID_WHITESPACE, DuplicateDecisionRequest, record_decision, undo_decision,
    import_match_evidence,
)
from relicrat.intake import CreateProvisionalCopy, stage_copy
from relicrat.models import ImportBatch, ImportCopy, ImportDuplicateDecision, OwnedCopy, StorageLocation
from relicrat.barcodes import BarcodeReading
from relicrat.import_recipes import CLZ_GAMES, MAX_RECIPE_BYTES, ImportRecipe, stage_game_release

router=APIRouter(prefix='/api/v1/imports',tags=['imports'])
MAX_BYTES=4*1024*1024
Source=Literal['clz','discogs','bluray','game_recipe']
MAPPINGS={
 'bluray':{'Title':'Movie or box-set title (one owned item per row)','Studio':'Studio','Blu-ray discs / DVD discs':'Format when known; disc counts never expand ownership','Casing':'Edition or packaging','Comment':'Notes','UPC / EAN':'Barcode only when valid and consistent; originals always retained'},
 'clz':{'Series':'Title','Issue':'Issue number','Publisher':'Publisher','Variant Description':'Edition (falls back to Variant)','Notes':'Notes','Quantity':'Physical copies'},
 'discogs':{'Title':'Title','Artist':'Artist','Format':'Format (full description)','Collection Notes':'Notes'},
}
REQUIRED={'bluray':{'Title','Studio','UPC','EAN','Product ID','Blu-ray discs','DVD discs'},'clz':{'Series','Issue','Publisher','Quantity','Collection Status'},'discogs':{'Title','Artist','Format','release_id'}}


def movie_row(value):
    counts=[]
    for key in ('Blu-ray discs','DVD discs'):
        text=value(key)
        if text in ('','-1'):counts.append(None)
        elif text.isascii() and text.isdecimal() and 0<=int(text)<=10000:counts.append(int(text))
        else:raise ValueError('Disc counts must be known whole values or unknown')
    bluray,dvd=counts
    format='Blu-ray + DVD' if bluray and dvd else 'Blu-ray' if bluray else 'DVD' if dvd else None
    warnings=[];codes=[]
    for key,kind in [('UPC','UPC_A'),('EAN','EAN_13')]:
        text=re.sub(r'[\s-]','',value(key))
        if not text:continue
        try:
            reading=BarcodeReading(value=text,format=kind)
            if (sum(int(d)*(3 if i%2==0 else 1) for i,d in enumerate(reversed(text[:-1])))+int(text[-1]))%10:raise ValueError('Invalid checksum')
            codes.append(reading)
        except ValueError:warnings.append('Invalid '+key+' retained in source information; not used as a barcode.')
    barcode=None
    if len(codes)==2 and '0'+codes[0].value!=codes[1].value:
        warnings.append('UPC and EAN differ. Both are retained in source information; no barcode is selected.')
    elif codes:barcode=codes[0]
    if any(count is None for count in counts):warnings.append('Unknown disc counts remain unknown in source information; format uses only known positive counts.')
    details={k:v for k,v in {'media_format':format,'studio':value('Studio')}.items() if v}
    return CreateProvisionalCopy(title=value('Title'),collection_type='movie',movie_details=details,
        edition_label=value('Casing') or None,description=value('Comment') or None,barcode=barcode),warnings


def parse_csv(source: Source, raw: bytes, recipe: ImportRecipe | None = None):
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
        mapping = {column: field for field, column in recipe.columns.model_dump(exclude_none=True).items()} if recipe else MAPPINGS[source]
        required = set(mapping) if recipe else REQUIRED[source]
        if not required.issubset(headers) and recipe:
            raise HTTPException(422, 'The CSV is missing one or more headers named by the recipe')
        if not required.issubset(headers):
            raise HTTPException(422,'Required columns are missing. Choose the matching CLZ, Discogs or Blu-ray.com export format.')
        releases={}
        rows=[];errors=[];warnings=[];copies=0;ids=set();repeated=0;retained_bytes=0
        for number,values in enumerate(reader,2):
            if number>5001:
                raise HTTPException(422,'Import at most 5,000 rows per file')
            if len(values)!=len(headers):
                raise HTTPException(422,f'Row {number} has a different number of columns')
            original=dict(zip(headers,values))
            value=lambda key: original.get(key,'').strip()
            try:
                if recipe:
                    payload, quantity, release = recipe.row(value)
                    if release is not None:
                        releases[number] = release
                elif source=='clz':
                    if value('Collection Status')!='In Collection':
                        raise ValueError('Only In Collection rows can create owned copies')
                    q=value('Quantity')
                    if not q.isascii() or not q.isdecimal() or not 1<=int(q)<=10000:
                        raise ValueError('Quantity must be a whole number from 1 to 10,000')
                    quantity=int(q)
                    payload=CreateProvisionalCopy(title=value('Series'),collection_type='comic',comic_details={k:v for k,v in {'issue_number':value('Issue'),'publisher':value('Publisher')}.items() if v},edition_label=value('Variant Description') or value('Variant') or None,description=value('Notes') or None)
                elif source=='bluray':
                    quantity=1
                    payload,messages=movie_row(value)
                    warnings.extend({'row':number,'message':message} for message in messages if len(warnings)<50)
                else:
                    quantity=1
                    payload=CreateProvisionalCopy(title=value('Title'),collection_type='record',record_details={k:v for k,v in {'artist':value('Artist'),'format':value('Format')}.items() if v},description=value('Collection Notes') or None)
                if not payload.title:
                    raise ValueError('A title is required')
            except (ValueError,ValidationError):
                if len(errors)<50: errors.append({'row':number,'message':'Check title, field lengths, ownership status and positive whole quantity.'})
                continue
            external = value(EXTERNAL_ID_COLUMNS.get(source, ''))
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
    return {'sha256':hashlib.sha256(raw).hexdigest(),'rows':rows,'copy_count':copies,'errors':errors,'warnings':warnings,'repeated_external_ids':repeated,'headers':headers,'mapping':mapping,'releases':releases}


def batch_info(batch):
    return {'id':str(batch.id),'source':batch.source,'sha256':batch.sha256,'parser_version':batch.parser_version,'row_count':batch.row_count,'copy_count':batch.copy_count,'created_at':batch.created_at}


def review_duplicates(db, source, parsed, recipe=None):
    if recipe:
        digest = hashlib.sha256((parsed['sha256'] + recipe.fingerprint).encode()).hexdigest()
        return {'digest': digest, 'rows': [], 'groups': []}
    column = EXTERNAL_ID_COLUMNS[source]
    rows = [(number, original.get(column, '').strip(ID_WHITESPACE), payload, quantity)
            for number, original, payload, quantity in parsed['rows']]
    evidence = import_match_evidence(db, source, {identifier for _, identifier, _, _ in rows if identifier})
    groups = list(evidence.values())
    indexes = {identifier: index for index, identifier in enumerate(evidence)}
    flagged = [
        {'row': number, 'group': indexes[identifier], 'quantity': quantity,
         'title': payload.title, 'edition': payload.edition_label or payload.record_details.format
         or payload.movie_details.media_format, 'issue': payload.comic_details.issue_number}
        for number, identifier, payload, quantity in rows if identifier in evidence
    ]
    digest = hashlib.sha256(json.dumps([source, parsed['sha256'], evidence],
                                       sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'digest': digest, 'rows': flagged, 'groups': groups}


def skip_duplicate_rows(mask: str) -> set[int]:
    # One bit per possible source row keeps 5,000 independent choices within URL limits.
    return {2 + byte * 8 + bit for byte, value in enumerate(bytes.fromhex(mask))
            for bit in range(8) if value & (1 << bit)}



def preview_import(source,raw,db,recipe=None):
    parsed=parse_csv(source,raw,recipe)
    existing=db.scalar(select(ImportBatch).where(ImportBatch.source==source,ImportBatch.sha256==parsed['sha256']))
    review = None if existing or parsed['errors'] else review_duplicates(db, source, parsed, recipe)
    return {'duplicate_review':review,'sha256':parsed['sha256'],'parser_version':1,'row_count':len(parsed['rows']),'copy_count':parsed['copy_count'],'errors':parsed['errors'],'warnings':parsed['warnings'],'repeated_external_ids':parsed['repeated_external_ids'],'mapping':parsed['mapping'],'preserved_columns':parsed['headers'],'existing_batch':batch_info(existing) if existing else None,'sample':[{'row':n,'quantity':q,**p.model_dump(),**({'game_release':parsed['releases'][n].model_dump(exclude_none=True)} if n in parsed['releases'] else {})} for n,_,p,q in parsed['rows'][:10]]}


def commit_import(source,raw,reviewed_sha256,db,duplicate_digest=None,skip_mask=None,recipe=None):
    parsed=parse_csv(source,raw,recipe)
    if recipe and duplicate_digest is None:
        raise HTTPException(422, 'Preview the recipe and CSV before importing')
    if reviewed_sha256!=parsed['sha256']:
        raise HTTPException(409,'The file changed. Preview it again before importing.')
    if parsed['errors']:
        raise HTTPException(422,'Correct every reported row before importing. No copies were imported.')
    if (duplicate_digest is None) != (skip_mask is None):
        raise HTTPException(422, 'Submit the reviewed duplicate choices together')
    try:
        # Serialize imports from the same source, including older clients, so a
        # changed export cannot slip between duplicate review and commit.
        db.execute(text('SELECT pg_advisory_xact_lock(737701, :source)'),
                   {'source': ('clz', 'discogs', 'bluray', 'game_recipe').index(source)})
        rows = parsed['rows']
        if duplicate_digest is not None:
            batch = db.scalar(select(ImportBatch).where(
                ImportBatch.source == source, ImportBatch.sha256 == parsed['sha256']))
            if batch is not None:
                result = {'batch': batch_info(batch), 'already_imported': True}
                db.commit()
                return result
            review = review_duplicates(db, source, parsed, recipe)
            if review['digest'] != duplicate_digest:
                detail = 'The recipe changed. Preview the file again before importing.' if recipe else 'Existing matches changed. Preview the file again before importing.'
                raise HTTPException(409, detail)
            skipped = skip_duplicate_rows(skip_mask)
            if not skipped <= {row['row'] for row in review['rows']}:
                raise HTTPException(422, 'Skip only rows with reviewed matches')
            rows = [row for row in rows if row[0] not in skipped]
            if not rows:
                raise HTTPException(422, 'Choose at least one row to import')
        # Retain the unique source/digest constraint as the exact-file retry boundary.
        ident=db.scalar(insert(ImportBatch).values(id=uuid.uuid4(),source=source,sha256=parsed['sha256'],parser_version=1,row_count=len(rows),copy_count=sum(row[3] for row in rows)).on_conflict_do_nothing(index_elements=['source','sha256']).returning(ImportBatch.id))
        if ident is None:
            batch=db.scalar(select(ImportBatch).where(ImportBatch.source==source,ImportBatch.sha256==parsed['sha256']))
            result={'batch':batch_info(batch),'already_imported':True};db.commit();return result
        for number,original,payload,quantity in rows:
            release = parsed['releases'].get(number)
            catalog_id, release_id = stage_game_release(db, payload.title, release) if release else (None, None)
            for index in range(1,quantity+1):
                copy = stage_copy(db, payload)
                if release_id:
                    copy.catalog_item_id, copy.release_id = catalog_id, release_id
                    copy.identification_status = 'identified'
                db.flush()
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


def request_recipe(request, source):
    encoded = request.headers.get('x-relicrat-import-recipe')
    if source != 'game_recipe':
        if encoded is not None:
            raise HTTPException(422, 'Choose the video game recipe import format')
        return None
    if encoded is None:
        return CLZ_GAMES
    if len(encoded) > 4 * ((MAX_RECIPE_BYTES + 2) // 3):
        raise HTTPException(413, 'Import recipe must be at most 2 KiB')
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > MAX_RECIPE_BYTES:
            raise HTTPException(413, 'Import recipe must be at most 2 KiB')
        return ImportRecipe.model_validate_json(raw)
    except (binascii.Error, ValueError):
        raise HTTPException(422, 'Use a valid version 1 video game import recipe') from None


@router.get('/recipes/clz-games')
def clz_games_recipe():
    return CLZ_GAMES.model_dump(exclude_none=True)


@router.post('/preview')
async def preview(request: Request,source: Source,db: Session=Depends(get_db)):
    raw=await csv_body(request)
    return await run_in_threadpool(preview_import,source,raw,db,request_recipe(request,source))


@router.post('/commit')
async def commit(
    request: Request, source: Source, reviewed_sha256: str = Query(pattern='^[0-9a-f]{64}$'),
    duplicate_digest: str | None = Query(default=None, pattern='^[0-9a-f]{64}$'),
    skip_mask: str | None = Query(default=None, pattern='^[0-9a-f]{1250}$'),
    db: Session = Depends(get_db),
):
    raw = await csv_body(request)
    return await run_in_threadpool(commit_import, source, raw, reviewed_sha256, db, duplicate_digest, skip_mask, request_recipe(request,source))


@router.get('')
def batches(limit: int=Query(default=20,ge=1,le=100),offset: int=Query(default=0,ge=0),db: Session=Depends(get_db)):
    return [batch_info(b) for b in db.scalars(select(ImportBatch).order_by(ImportBatch.created_at.desc(),ImportBatch.id.desc()).limit(limit).offset(offset))]


@router.get('/{batch_id}/rows')
def source_rows(batch_id: UUID,limit: int=Query(default=20,ge=1,le=100),offset: int=Query(default=0,ge=0),db: Session=Depends(get_db)):
    if db.get(ImportBatch,batch_id) is None: raise HTTPException(404,'Import batch not found')
    return [{'copy_id':str(r.owned_copy_id),'row':r.row_number,'copy_number':r.copy_number,'source':r.source_row} for r in db.scalars(select(ImportCopy).where(ImportCopy.batch_id==batch_id).order_by(ImportCopy.row_number,ImportCopy.copy_number).limit(limit).offset(offset))]

@router.get('/{batch_id}/possible-duplicates')
def possible_duplicates(
    batch_id: UUID,
    anchor: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(404, 'Import batch not found')

    column = EXTERNAL_ID_COLUMNS.get(batch.source)
    if column is None:
        if anchor is not None:
            raise HTTPException(404, 'Import comparison no longer available')
        return []
    identifier = func.btrim(ImportCopy.source_row[column].astext, ID_WHITESPACE)
    in_batch = ImportCopy.batch_id == batch_id
    eligible = (
        select(ImportCopy)
        .join(ImportBatch, ImportBatch.id == ImportCopy.batch_id)
        .join(OwnedCopy, OwnedCopy.id == ImportCopy.owned_copy_id)
        .where(ImportBatch.source == batch.source, OwnedCopy.deleted_at.is_(None),
               OwnedCopy.ownership_status == 'owned')
    )
    if anchor is None:
        selected_ids = eligible.with_only_columns(identifier).where(in_batch, identifier != '').distinct()
        # Count reviewed pairs directly so expanded quantities do not produce a cross product.
        matching = eligible.with_only_columns(
            ImportCopy.owned_copy_id.label('id'), identifier.label('identifier'),
            in_batch.label('selected'), OwnedCopy.provisional_title.label('title'),
        ).where(identifier.in_(selected_ids)).cte()
        left, right = matching.alias(), matching.alias()
        decision = ImportDuplicateDecision
        kept = (
            select(left.c.identifier, func.count().label('pairs'))
            .select_from(decision)
            .join(left, left.c.id == decision.left_id)
            .join(right, right.c.id == decision.right_id)
            .where(decision.archived_id.is_(None), decision.undone_at.is_(None),
                   left.c.selected != right.c.selected, left.c.identifier == right.c.identifier)
            .group_by(left.c.identifier).subquery()
        )
        selected_count = func.count().filter(matching.c.selected)
        other_count = func.count().filter(~matching.c.selected)
        group_query = (
            select(
                func.min(cast(matching.c.id, String)).filter(matching.c.selected).label('anchor'),
                func.min(matching.c.title).filter(matching.c.selected).label('title'),
                selected_count.label('selected_count'), other_count.label('other_count'),
            )
            .select_from(matching)
            .outerjoin(kept, kept.c.identifier == matching.c.identifier)
            .group_by(matching.c.identifier, kept.c.pairs)
            .having(selected_count * other_count > func.coalesce(kept.c.pairs, 0))
            .order_by(matching.c.identifier)
        )
        return [dict(row) for row in db.execute(group_query.limit(limit).offset(offset)).mappings()]

    shared_id = db.scalar(
        eligible.with_only_columns(identifier)
        .where(in_batch, ImportCopy.owned_copy_id == anchor)
    )
    if not shared_id:
        raise HTTPException(404, 'Import comparison no longer available')
    matches = eligible.where(identifier == shared_id)
    if not db.scalar(select(matches.where(~in_batch).exists())):
        raise HTTPException(404, 'Import comparison no longer available')
    rows = db.execute(
        matches.with_only_columns(ImportCopy, OwnedCopy, ImportBatch.created_at, StorageLocation.name)
        .outerjoin(StorageLocation, OwnedCopy.storage_location_id == StorageLocation.id)
        .order_by(in_batch.desc(), ImportBatch.created_at.desc(), ImportCopy.batch_id,
                  ImportCopy.row_number, ImportCopy.copy_number)
        .limit(limit).offset(offset)
    )
    return [
        {
            'copy_id': copy.id, 'updated_at': copy.updated_at, 'selected_import': source.batch_id == batch_id,
            'imported_at': imported_at, 'row': source.row_number, 'copy_number': source.copy_number,
            'title': copy.provisional_title, 'edition': copy.edition_label,
            'artist': copy.record_details.get('artist'), 'issue': copy.comic_details.get('issue_number'),
            'format': copy.record_details.get('format') or copy.movie_details.get('media_format'),
            'storage': storage,
        }
        for source, copy, imported_at, storage in rows
    ]

@router.get('/{batch_id}/duplicate-decisions')
def duplicate_decisions(
    batch_id: UUID, limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0), db: Session = Depends(get_db),
):
    if db.get(ImportBatch, batch_id) is None:
        raise HTTPException(404, 'Import batch not found')
    decision = ImportDuplicateDecision
    left, right = aliased(OwnedCopy), aliased(OwnedCopy)
    left_source, right_source = aliased(ImportCopy), aliased(ImportCopy)
    rows = db.execute(
        select(decision.id, decision.archived_id, decision.left_id, decision.created_at,
               left.provisional_title.label('left_title'), right.provisional_title.label('right_title'),
               left.edition_label.label('left_edition'), right.edition_label.label('right_edition'))
        .join(left, left.id == decision.left_id).join(right, right.id == decision.right_id)
        .join(left_source, left_source.owned_copy_id == decision.left_id)
        .join(right_source, right_source.owned_copy_id == decision.right_id)
        .where(or_(left_source.batch_id == batch_id, right_source.batch_id == batch_id),
               decision.undone_at.is_(None))
        .order_by(decision.created_at.desc(), decision.id).limit(limit).offset(offset)
    )
    return [dict(row) for row in rows.mappings()]


@router.post('/{batch_id}/duplicate-decisions')
def save_duplicate_decision(batch_id: UUID, request: DuplicateDecisionRequest, db: Session = Depends(get_db)):
    try:
        decision = record_decision(db, batch_id, request)
        result = {'id': decision.id, 'archived_id': decision.archived_id, 'undone_at': decision.undone_at}
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'A duplicate decision already exists. Reload before deciding') from None


@router.post('/{batch_id}/duplicate-decisions/{decision_id}/undo')
def restore_duplicate_decision(batch_id: UUID, decision_id: UUID, db: Session = Depends(get_db)):
    undo_decision(db, batch_id, decision_id)
    db.commit()
    return {'id': decision_id}
