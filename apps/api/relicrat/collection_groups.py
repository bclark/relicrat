"""Whole-result group counts with bounded, alphabetically paginated summaries."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query
from sqlalchemy import case,func
from sqlalchemy.orm import Session
from relicrat.database import get_db
from relicrat.inventory_queries import copies_query,group_value
from relicrat.models import OwnedCopy,CustomCollection
from relicrat.collection_types import COLLECTION_TYPES

router=APIRouter(prefix='/api/v1/collection-groups',tags=['inventory'])


@router.get('')
def groups(q: str|None=Query(default=None,max_length=200,pattern=r'^[^\x00]*$'),
           collection_type: Literal['record','comic','movie']|None=Query(default=None),
           storage_location_id: UUID|None=Query(default=None),unassigned: bool=Query(default=False),
           limit: int=Query(default=20,ge=1,le=100),offset: int=Query(default=0,ge=0),
           split_custom: bool=Query(default=False),db: Session=Depends(get_db)):
    stmt=copies_query(q,collection_type,storage_location_id,unassigned)
    if collection_type or not split_custom:
        value=group_value(collection_type) if collection_type else OwnedCopy.collection_type
        label=value if collection_type else case({k:v.plural_label for k,v in COLLECTION_TYPES.items()},value=OwnedCopy.collection_type)
        stmt=stmt.with_only_columns(value.label('value'),func.count(OwnedCopy.id).label('count')).group_by(value)
        stmt=stmt.order_by(func.lower(label).asc().nulls_last(),value.asc().nulls_last()).limit(limit).offset(offset)
        return [{'collection_type':collection_type or v,'value':v if collection_type else None,
                 'label':(v if v is not None else COLLECTION_TYPES[collection_type].grouping.unknown_label) if collection_type else COLLECTION_TYPES[v].plural_label,
                 'copy_count':count} for v,count in db.execute(stmt)]
    # A goal collection is keyed by UUID, even when names coincide. It is not a new built-in type.
    label=case((OwnedCopy.custom_collection_id.is_not(None),CustomCollection.proposal['collection']['name'].astext),
               else_=case({k:v.plural_label for k,v in COLLECTION_TYPES.items()},value=OwnedCopy.collection_type))
    stmt=stmt.outerjoin(CustomCollection,OwnedCopy.custom_collection_id==CustomCollection.id).with_only_columns(
        OwnedCopy.collection_type,OwnedCopy.custom_collection_id,label.label('label'),func.count(OwnedCopy.id))
    stmt=stmt.group_by(OwnedCopy.collection_type,OwnedCopy.custom_collection_id,label).order_by(
        func.lower(label),label,OwnedCopy.custom_collection_id.asc().nulls_first(),OwnedCopy.collection_type).limit(limit).offset(offset)
    return [dict({'collection_type':kind,'value':None,'label':name,'copy_count':count},
                 **({'custom_collection_id':str(cid)} if cid else {})) for kind,cid,name,count in db.execute(stmt)]
