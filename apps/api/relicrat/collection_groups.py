"""Whole-result group counts with bounded, alphabetically paginated summaries."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query
from sqlalchemy import case,func
from sqlalchemy.orm import Session
from relicrat.database import get_db
from relicrat.inventory_queries import copies_query,group_value
from relicrat.models import OwnedCopy
from relicrat.collection_types import COLLECTION_TYPES

router=APIRouter(prefix='/api/v1/collection-groups',tags=['inventory'])


@router.get('')
def groups(q: str|None=Query(default=None,max_length=200,pattern=r'^[^\x00]*$'),
           collection_type: Literal['record','comic']|None=Query(default=None),
           storage_location_id: UUID|None=Query(default=None),unassigned: bool=Query(default=False),
           limit: int=Query(default=20,ge=1,le=100),offset: int=Query(default=0,ge=0),
           db: Session=Depends(get_db)):
    stmt=copies_query(q,collection_type,storage_location_id,unassigned)
    value=group_value(collection_type) if collection_type else OwnedCopy.collection_type
    stmt=stmt.with_only_columns(value.label('value'),func.count(OwnedCopy.id).label('count')).group_by(value)
    label=value if collection_type else case({k:v.plural_label for k,v in COLLECTION_TYPES.items()},value=OwnedCopy.collection_type)
    stmt=stmt.order_by(func.lower(label).asc().nulls_last(),value.asc().nulls_last()).limit(limit).offset(offset)
    return [{'collection_type':collection_type or v,'value':v if collection_type else None,
             'label':(v if v is not None else COLLECTION_TYPES[collection_type].grouping.unknown_label) if collection_type else COLLECTION_TYPES[v].plural_label,
             'copy_count':count} for v,count in db.execute(stmt)]
