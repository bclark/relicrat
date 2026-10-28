"""Nested locations and transactional manual copy movements."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.models import CopyLocationEvent, OwnedCopy, StorageLocation

router = APIRouter(prefix="/api/v1/storage-locations", tags=["storage"])


class CreateLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=250)
    parent_id: UUID | None = None
    kind: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=10000)


class LocationInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    parent_id: UUID | None
    name: str
    kind: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=LocationInfo, status_code=201)
def create_location(payload: CreateLocation, db: Session = Depends(get_db)):
    try:
        if payload.parent_id is not None and db.get(StorageLocation, payload.parent_id) is None:
            raise HTTPException(status_code=404, detail="Parent location not found")
        location = StorageLocation(**payload.model_dump())
        db.add(location)
        db.commit()
        return location
    except Exception:
        db.rollback()
        raise


@router.get("", response_model=list[LocationInfo])
def list_locations(limit: int = Query(default=50, ge=1, le=100),
                   offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    return list(db.scalars(select(StorageLocation).order_by(StorageLocation.created_at, StorageLocation.id)
                           .limit(limit).offset(offset)).all())


@router.get("/{location_id}", response_model=LocationInfo)
def get_location(location_id: UUID, db: Session = Depends(get_db)):
    location = db.get(StorageLocation, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


class AssignmentError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def assign_location(db: Session, copy_id: UUID, location_id: UUID | None,
                    expected_revision: int) -> OwnedCopy:
    try:
        copy = db.scalar(select(OwnedCopy).where(OwnedCopy.id == copy_id)
                         .with_for_update().execution_options(populate_existing=True))
        if copy is None or copy.deleted_at is not None:
            raise AssignmentError(404, "Collectible not found")
        if copy.storage_revision != expected_revision:
            raise AssignmentError(409, "Stale storage revision; reload the collectible")
        if location_id is not None and db.get(StorageLocation, location_id) is None:
            raise AssignmentError(404, "Location not found")
        if copy.storage_location_id == location_id:
            db.commit()
            return copy
        db.add(CopyLocationEvent(owned_copy_id=copy.id,
                                before_location_id=copy.storage_location_id, after_location_id=location_id,
                                before_revision=copy.storage_revision, after_revision=copy.storage_revision + 1))
        copy.storage_location_id = location_id
        copy.storage_revision += 1
        db.commit()
        return copy
    except Exception:
        db.rollback()
        raise
