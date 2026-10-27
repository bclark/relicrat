"""Provisional inventory API.

Catalog reconciliation, media upload, and location assignment are separate work.
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.models import OwnedCopy

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


class CreateProvisionalCopy(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None

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
