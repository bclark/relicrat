"""Bounded read projections for collection assistants."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from relicrat.auth import AGENT_PREFIX
from relicrat.database import get_db
from relicrat.inventory_queries import copies_query, copy_order
from relicrat.location_audits import query_open_audit_locations
from relicrat.models import OwnedCopy, StorageLocation

router = APIRouter(prefix=AGENT_PREFIX, tags=['agent reads'])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


class Location(BaseModel):
    id: UUID
    name: str


class CopyLocation(BaseModel):
    id: UUID
    title: str | None
    edition: str | None
    location: Location | None


class UnresolvedLocation(Location):
    unresolved: int


def with_locations(statement):
    return (statement.add_columns(StorageLocation.id, StorageLocation.name)
            .outerjoin(StorageLocation, StorageLocation.id == OwnedCopy.storage_location_id)
            .where(OwnedCopy.ownership_status == 'owned'))


def project(row):
    copy, location_id, name = row
    return CopyLocation(id=copy.id, title=copy.provisional_title, edition=copy.edition_label,
                        location=Location(id=location_id, name=name) if location_id else None)


@router.get('/copies', response_model=list[CopyLocation])
def search_copies(
    q: Annotated[str | None, Query(max_length=200, pattern=r'^[^\x00]*$')] = None,
    limit: Limit = 20, offset: Offset = 0, db: Session = Depends(get_db),
):
    stmt = with_locations(copies_query(q=q)).order_by(*copy_order(None, None, 'title'))
    return [project(row) for row in db.execute(stmt.limit(limit).offset(offset))]


@router.get('/copies/{copy_id}', response_model=CopyLocation)
def copy_location(copy_id: UUID, db: Session = Depends(get_db)):
    row = db.execute(with_locations(copies_query()).where(OwnedCopy.id == copy_id)).one_or_none()
    if row is None:
        raise HTTPException(404, 'Owned copy not found')
    return project(row)


@router.get('/unresolved-locations', response_model=list[UnresolvedLocation])
def unresolved_locations(limit: Limit = 20, offset: Offset = 0, db: Session = Depends(get_db)):
    return query_open_audit_locations(db, limit, offset)
