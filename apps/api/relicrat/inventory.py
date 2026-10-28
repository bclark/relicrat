"""Provisional inventory API.

Manual identification preserves the physical copy and its provisional information.
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.models import OwnedCopy, ReconciliationEvent
from relicrat.reconciliation import ReconciliationError, reconcile

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


class CreateProvisionalCopy(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def require_content(self) -> "CreateProvisionalCopy":
        self.title = self.title.strip() if self.title else None
        self.description = self.description.strip() if self.description else None
        if not self.title and not self.description:
            raise ValueError("A title or description is required")
        return self


class InventoryCopy(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = Field(validation_alias="provisional_title")
    description: str | None
    catalog_item_id: UUID | None
    release_id: UUID | None
    storage_location_id: UUID | None
    identification_status: str
    storage_revision: int
    identification_revision: int
    ownership_status: str
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=InventoryCopy, status_code=201)
def create_copy(payload: CreateProvisionalCopy, db: Session = Depends(get_db)) -> OwnedCopy:
    copy = OwnedCopy(provisional_title=payload.title, description=payload.description)
    try:
        db.add(copy)
        db.commit()
        db.refresh(copy)
    except Exception:
        db.rollback()
        raise
    return copy


@router.get("/{copy_id}", response_model=InventoryCopy)
def get_copy(copy_id: UUID, db: Session = Depends(get_db)) -> OwnedCopy:
    copy = db.get(OwnedCopy, copy_id)
    if copy is None or copy.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Collectible not found")
    return copy


@router.get("", response_model=list[InventoryCopy])
def list_copies(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[OwnedCopy]:
    stmt = (
        select(OwnedCopy)
        .where(OwnedCopy.deleted_at.is_(None))
        .order_by(OwnedCopy.created_at.desc(), OwnedCopy.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())


class ReconcileCopy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    catalog_item_id: UUID
    release_id: UUID | None = None
    expected_revision: int = Field(ge=0, le=2147483646, strict=True)


class ReconciliationInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owned_copy_id: UUID
    before_catalog_item_id: UUID | None
    before_release_id: UUID | None
    after_catalog_item_id: UUID
    after_release_id: UUID | None
    before_status: str
    after_status: str
    before_revision: int
    after_revision: int
    operation: str
    created_at: datetime


@router.post("/{copy_id}/reconcile", response_model=InventoryCopy)
def reconcile_copy(copy_id: UUID, payload: ReconcileCopy, db: Session = Depends(get_db)) -> OwnedCopy:
    try:
        return reconcile(db, copy_id, payload.catalog_item_id, payload.release_id, payload.expected_revision)
    except ReconciliationError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from None


@router.get("/{copy_id}/reconciliations", response_model=list[ReconciliationInfo])
def reconciliation_history(copy_id: UUID,
                           limit: int = Query(default=50, ge=1, le=100),
                           offset: int = Query(default=0, ge=0),
                           db: Session = Depends(get_db)) -> list[ReconciliationEvent]:
    get_copy(copy_id, db)
    return list(db.scalars(select(ReconciliationEvent)
                          .where(ReconciliationEvent.owned_copy_id == copy_id)
                          .order_by(ReconciliationEvent.after_revision.asc())
                          .limit(limit).offset(offset)).all())


class AssignLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    storage_location_id: UUID | None
    expected_storage_revision: int = Field(ge=0, le=2147483646, strict=True)


class LocationEventInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owned_copy_id: UUID
    before_location_id: UUID | None
    after_location_id: UUID | None
    before_revision: int
    after_revision: int
    operation: str
    created_at: datetime


@router.post("/{copy_id}/location", response_model=InventoryCopy)
def assign_copy_location(copy_id: UUID, payload: AssignLocation, db: Session = Depends(get_db)) -> OwnedCopy:
    from relicrat.storage import AssignmentError, assign_location
    try:
        return assign_location(db, copy_id, payload.storage_location_id, payload.expected_storage_revision)
    except AssignmentError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from None


@router.get("/{copy_id}/locations", response_model=list[LocationEventInfo])
def location_history(copy_id: UUID,
                     limit: int = Query(default=50, ge=1, le=100),
                     offset: int = Query(default=0, ge=0),
                     db: Session = Depends(get_db)):
    from relicrat.models import CopyLocationEvent
    get_copy(copy_id, db)
    return list(db.scalars(select(CopyLocationEvent)
                          .where(CopyLocationEvent.owned_copy_id == copy_id)
                          .order_by(CopyLocationEvent.after_revision.asc())
                          .limit(limit).offset(offset)).all())
