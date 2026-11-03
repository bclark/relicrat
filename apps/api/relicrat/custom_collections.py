"""Explicit custom collection activation and physical-copy intake, without catalog inference."""
import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from relicrat.collection_proposals import read_proposal
from relicrat.database import get_db
from relicrat.intake import CreateProvisionalCopy, stage_copy
from relicrat.models import CustomCollection, CustomCollectionType, OwnedCopy

router = APIRouter(prefix='/api/v1/custom-collections', tags=['custom collections'])


def collection_info(value):
    return {'id':str(value.id), 'name':value.proposal['collection']['name'], 'proposal':value.proposal}


def get_collection(db, collection_id):
    value=db.get(CustomCollection, collection_id)
    if value is None:raise HTTPException(404,'Collection not found')
    return value


def validate_observations(db, collection_id, title, details):
    if collection_id is None:
        if details:raise HTTPException(422,'Choose a saved custom collection before adding its fields')
        return
    collection=get_collection(db,collection_id)
    definition=db.get(CustomCollectionType,collection.type_id).definition
    if not title or not title.strip() or len(title)>definition['title']['max_length']:
        raise HTTPException(422,'Keep a title within this collection definition’s length limit')
    fields={field['id']:field for field in definition['optional_fields']}
    if not isinstance(details,dict) or not set(details)<=set(fields):
        raise HTTPException(422,'Custom observations must use this collection’s field IDs')
    for key,value in details.items():
        if not isinstance(value,str) or not value.strip() or '\x00' in value or len(value)>fields[key]['max_length']:
            raise HTTPException(422,'Custom observations must be meaningful text within their field limits')


@router.get('')
def list_collections(limit:int=Query(default=50,ge=1,le=100),offset:int=Query(default=0,ge=0),db:Session=Depends(get_db)):
    return [{'id':str(value.id),'name':value.proposal['collection']['name']} for value in db.scalars(select(CustomCollection).order_by(CustomCollection.created_at,CustomCollection.id).limit(limit).offset(offset))]


@router.get('/{collection_id}')
def read_collection(collection_id:UUID,db:Session=Depends(get_db)):
    return collection_info(get_collection(db,collection_id))


@router.post('')
async def activate_collection(request:Request,db:Session=Depends(get_db)):
    proposal=(await read_proposal(request)).model_dump()
    definition=proposal['type_definition'];slug=proposal['collection']['id']
    try:
        db.execute(insert(CustomCollectionType).values(id=definition['id'],definition=definition).on_conflict_do_nothing())
        existing=db.get(CustomCollectionType,definition['id'])
        if existing.definition!=definition:
            raise HTTPException(409,'This type ID already has a different definition. Keep the saved definition or use a new ID; existing figures will not be changed.')
        db.execute(insert(CustomCollection).values(slug=slug,type_id=definition['id'],proposal=proposal).on_conflict_do_nothing(index_elements=['slug']))
        collection=db.scalar(select(CustomCollection).where(CustomCollection.slug==slug))
        if collection.proposal!=proposal:
            raise HTTPException(409,'This collection ID already has a different checklist. Use a new ID; the saved collection will not be replaced.')
        db.commit()
        return collection_info(collection)
    except Exception:
        db.rollback();raise


class AddCustomCopy(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    request_id: UUID
    title: str=Field(min_length=1,max_length=500,pattern=r'^[^\x00]*$')
    description: str | None=Field(default=None,max_length=10000,pattern=r'^[^\x00]*$')
    custom_details: dict[str,StrictStr]=Field(default_factory=dict,max_length=12)


@router.post('/{collection_id}/copies')
def add_custom_copy(collection_id:UUID,payload:AddCustomCopy,db:Session=Depends(get_db)):
    from relicrat.inventory import InventoryCopy
    try:
        get_collection(db,collection_id)
        validate_observations(db,collection_id,payload.title,payload.custom_details)
        digest=hashlib.sha256(json.dumps({'collection':str(collection_id),'title':payload.title,'description':payload.description,'details':payload.custom_details},sort_keys=True).encode()).hexdigest()
        # Serialize exact retry UUIDs across concurrent tabs; no persistent lock table.
        db.execute(select(func.pg_advisory_xact_lock(int.from_bytes(payload.request_id.bytes[:8],signed=True))))
        existing=db.get(OwnedCopy,payload.request_id)
        if existing is not None:
            if existing.custom_collection_id!=collection_id or existing.custom_intake_hash!=digest:
                raise HTTPException(409,'This save identifier was used for different details. Reload before adding another figure.')
            if existing.deleted_at is not None:raise HTTPException(409,'This earlier save is no longer active; review inventory before retrying')
            db.commit();return InventoryCopy.model_validate(existing)
        copy=stage_copy(db,CreateProvisionalCopy(title=payload.title,description=payload.description))
        copy.id=payload.request_id;copy.custom_collection_id=collection_id;copy.custom_details=payload.custom_details;copy.custom_intake_hash=digest
        db.commit();db.refresh(copy)
        return InventoryCopy.model_validate(copy)
    except Exception:
        db.rollback();raise
