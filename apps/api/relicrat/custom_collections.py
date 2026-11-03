"""Explicit custom collection activation and physical-copy intake, without catalog inference."""
import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictStr, StrictBool
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from relicrat.collection_proposals import read_proposal, read_document_bytes, parse_document, TypeDefinition
from relicrat.database import get_db
from relicrat.intake import CreateProvisionalCopy, stage_copy
from relicrat.models import CustomCollection, CustomCollectionType, CustomTypeRevision, OwnedCopy

router = APIRouter(prefix='/api/v1/custom-collections', tags=['custom collections'])


def collection_info(db,value):
    definition,revision=current_definition(db,value.type_id)
    return {'id':str(value.id), 'name':value.proposal['collection']['name'], 'proposal':dict(value.proposal,type_definition=definition),'type_revision':revision}


def get_collection(db, collection_id):
    value=db.get(CustomCollection, collection_id)
    if value is None:raise HTTPException(404,'Collection not found')
    return value


def current_definition(db,type_id,lock=False):
    if lock:
        db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended('relicrat-custom-type:'+type_id,0))))
    revision=db.scalar(select(CustomTypeRevision).where(CustomTypeRevision.type_id==type_id).order_by(CustomTypeRevision.revision.desc()).limit(1))
    if revision is not None:return revision.definition,revision.revision
    return db.get(CustomCollectionType,type_id).definition,0


def compatible_values(definition,title,details):
    if not title or not title.strip() or len(title)>definition['title']['max_length']:return False
    fields={f['id']:f for f in definition['optional_fields']}
    if not isinstance(details,dict) or not set(details)<=set(fields):return False
    for key,value in details.items():
        field=fields[key];control=field['input'];choices=field.get('options',[])
        if control=='checkbox':
            if type(value) is not bool:return False
        elif control=='checkboxes':
            if not isinstance(value,list) or len(value)>20 or any(type(v) is not str for v in value) or len(set(value))!=len(value) or not set(value)<=set(choices):return False
        elif type(value) is not str or not value.strip() or '\x00' in value or len(value)>field['max_length'] or (control in ('select','radio') and value not in choices):return False
    return True


def validate_observations(db, collection_id, title, details, expected_revision=None):
    if collection_id is None:
        if details:raise HTTPException(422,'Choose a saved custom collection before adding its fields')
        return
    collection=get_collection(db,collection_id)
    definition,revision=current_definition(db,collection.type_id,lock=True)
    if expected_revision is not None and expected_revision!=revision:
        raise HTTPException(412,'The field definition changed. Reload and review your draft before saving.')
    if not compatible_values(definition,title,details):
        raise HTTPException(422,'Observations must match the saved field controls, choices and length limits')



@router.get('')
def list_collections(limit:int=Query(default=50,ge=1,le=100),offset:int=Query(default=0,ge=0),db:Session=Depends(get_db)):
    return [{'id':str(value.id),'name':value.proposal['collection']['name']} for value in db.scalars(select(CustomCollection).order_by(CustomCollection.created_at,CustomCollection.id).limit(limit).offset(offset))]


@router.get('/{collection_id}')
def read_collection(collection_id:UUID,db:Session=Depends(get_db)):
    return collection_info(db,get_collection(db,collection_id))


@router.post('')
async def activate_collection(request:Request,db:Session=Depends(get_db)):
    proposal=(await read_proposal(request)).model_dump(exclude_defaults=True)
    definition=proposal['type_definition'];slug=proposal['collection']['id']
    try:
        saved=db.scalar(select(CustomCollection).where(CustomCollection.slug==slug))
        if saved is not None and saved.proposal==proposal:return collection_info(db,saved)
        db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended('relicrat-custom-type:'+definition['id'],0))))
        db.execute(insert(CustomCollectionType).values(id=definition['id'],definition=definition).on_conflict_do_nothing())
        existing,_=current_definition(db,definition['id'])
        if existing!=definition:
            raise HTTPException(409,'This type ID already has a different definition. Keep the saved definition or use a new ID; existing figures will not be changed.')
        db.execute(insert(CustomCollection).values(slug=slug,type_id=definition['id'],proposal=proposal).on_conflict_do_nothing(index_elements=['slug']))
        collection=db.scalar(select(CustomCollection).where(CustomCollection.slug==slug))
        if collection.proposal!=proposal:
            raise HTTPException(409,'This collection ID already has a different checklist. Use a new ID; the saved collection will not be replaced.')
        db.commit()
        return collection_info(db,collection)
    except Exception:
        db.rollback();raise


class AddCustomCopy(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    request_id: UUID
    title: str=Field(min_length=1,max_length=500,pattern=r'^[^\x00]*$')
    description: str | None=Field(default=None,max_length=10000,pattern=r'^[^\x00]*$')
    expected_type_revision: int | None=Field(default=None,ge=0,le=2147483646,strict=True)
    custom_details: dict[str,StrictStr | StrictBool | list[StrictStr]]=Field(default_factory=dict,max_length=12)


@router.post('/{collection_id}/copies')
def add_custom_copy(collection_id:UUID,payload:AddCustomCopy,db:Session=Depends(get_db)):
    from relicrat.inventory import InventoryCopy
    try:
        get_collection(db,collection_id)
        digest=hashlib.sha256(json.dumps({'collection':str(collection_id),'title':payload.title,'description':payload.description,'details':payload.custom_details},sort_keys=True).encode()).hexdigest()
        # Serialize exact retry UUIDs across concurrent tabs; no persistent lock table.
        db.execute(select(func.pg_advisory_xact_lock(int.from_bytes(payload.request_id.bytes[:8],signed=True))))
        existing=db.get(OwnedCopy,payload.request_id)
        if existing is not None:
            if existing.custom_collection_id!=collection_id or existing.custom_intake_hash!=digest:
                raise HTTPException(409,'This save identifier was used for different details. Reload before adding another figure.')
            if existing.deleted_at is not None:raise HTTPException(409,'This earlier save is no longer active; review inventory before retrying')
            db.commit();return InventoryCopy.model_validate(existing)
        validate_observations(db,collection_id,payload.title,payload.custom_details,payload.expected_type_revision)
        copy=stage_copy(db,CreateProvisionalCopy(title=payload.title,description=payload.description))
        copy.id=payload.request_id;copy.custom_collection_id=collection_id;copy.custom_details=payload.custom_details;copy.custom_intake_hash=digest
        db.commit();db.refresh(copy)
        return InventoryCopy.model_validate(copy)
    except Exception:
        db.rollback();raise


class ReviseDefinition(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    expected_revision: int=Field(ge=0,le=2147483646)
    definition: TypeDefinition


def check_revision(db,collection_id,payload):
    collection=get_collection(db,collection_id)
    current,revision=current_definition(db,collection.type_id,lock=True)
    definition=payload.definition.model_dump(exclude_defaults=True)
    if revision!=payload.expected_revision:raise HTTPException(409,'The definition changed elsewhere. Reload it before reviewing another update.')
    if definition['id']!=collection.type_id:raise HTTPException(422,'Keep the saved type ID when changing field controls')
    affected=db.scalar(select(func.count()).select_from(CustomCollection).where(CustomCollection.type_id==collection.type_id))
    copies=db.execute(select(OwnedCopy.provisional_title,OwnedCopy.custom_details).join(CustomCollection,OwnedCopy.custom_collection_id==CustomCollection.id).where(CustomCollection.type_id==collection.type_id))
    incompatible=sum(not compatible_values(definition,title,details) for title,details in copies)
    if incompatible:raise HTTPException(422,f'{incompatible} saved figure(s) have values outside the proposed controls or limits. Keep those choices/fields or review the figures first; no values were changed.')
    return collection,definition,revision,affected,current==definition


@router.post('/{collection_id}/definition-preview')
async def preview_definition(collection_id:UUID,request:Request,db:Session=Depends(get_db)):
    payload=parse_document(await read_document_bytes(request),ReviseDefinition)
    try:
        _,definition,revision,affected,unchanged=check_revision(db,collection_id,payload)
        return {'definition':definition,'revision':revision,'affected_collections':affected,'unchanged':unchanged,'notice':'All saved values remain compatible. No figure or checklist will change.'}
    finally:db.rollback() # Release the type lock after read-only review.


@router.post('/{collection_id}/definition')
async def revise_definition(collection_id:UUID,request:Request,db:Session=Depends(get_db)):
    payload=parse_document(await read_document_bytes(request),ReviseDefinition)
    try:
        collection,definition,revision,_,unchanged=check_revision(db,collection_id,payload)
        if not unchanged:db.add(CustomTypeRevision(type_id=collection.type_id,revision=revision+1,definition=definition))
        db.commit();return collection_info(db,collection)
    except Exception:db.rollback();raise


@router.get('/{collection_id}/definition-history')
def definition_history(collection_id:UUID,limit:int=Query(default=20,ge=1,le=100),offset:int=Query(default=0,ge=0),db:Session=Depends(get_db)):
    collection=get_collection(db,collection_id);base=db.get(CustomCollectionType,collection.type_id)
    total=db.scalar(select(func.count()).select_from(CustomTypeRevision).where(CustomTypeRevision.type_id==collection.type_id))
    revisions=list(db.scalars(select(CustomTypeRevision).where(CustomTypeRevision.type_id==collection.type_id).order_by(CustomTypeRevision.revision.desc()).limit(limit).offset(offset)))
    result=[{'revision':v.revision,'definition':v.definition,'created_at':v.created_at} for v in revisions]
    if offset<=total and len(result)<limit:result.append({'revision':0,'definition':base.definition,'created_at':base.created_at})
    return result
