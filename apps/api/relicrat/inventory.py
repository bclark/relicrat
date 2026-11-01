"""Provisional inventory API.

Manual identification preserves the physical copy and its provisional information.
"""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from relicrat.inventory_queries import copies_query,copy_order
from relicrat.database import get_db
from relicrat.models import CatalogItem, CopyDetailEvent, OwnedCopy, ReconciliationEvent, Release
from relicrat.intake import CreateProvisionalCopy, stage_copy
from relicrat.catalog_cover import CoverSelection,stage_cover
from relicrat.barcodes import BarcodeReading
from relicrat.record_details import RecordDetails
from relicrat.comic_details import ComicDetails
from relicrat.movie_details import MovieDetails
from relicrat.collection_types import COLLECTION_TYPES
from relicrat.reconciliation import ReconciliationError, reconcile

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])




class InventoryCopy(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = Field(validation_alias="provisional_title")
    description: str | None
    collection_type: Literal['other', 'record', 'comic', 'movie']
    barcode: dict[str, str]
    record_details: dict[str, str]
    movie_details: dict[str, str]
    comic_details: dict[str, str]
    edition_label: str | None
    details_revision: int
    catalog_item_id: UUID | None
    release_id: UUID | None
    storage_location_id: UUID | None
    identification_status: str
    storage_revision: int
    identification_revision: int
    ownership_status: str
    created_at: datetime
    updated_at: datetime


class CreateCopyRequest(CreateProvisionalCopy):
    catalog_cover: CoverSelection | None = None


@router.post("", response_model=InventoryCopy, status_code=201)
def create_copy(payload: CreateCopyRequest, db: Session = Depends(get_db)) -> OwnedCopy:
    try:
        copy = stage_copy(db, payload)
        with stage_cover(db,copy,payload.collection_type,payload.catalog_cover):
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
    q: str | None = Query(default=None, max_length=200, pattern=r"^[^\x00]*$"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    collection_type: Literal['other', 'record', 'comic', 'movie'] | None = Query(default=None),
    storage_location_id: UUID | None = None,
    unassigned: bool = False,
    group: Annotated[str | None, Query(max_length=500,pattern=r'^[^\x00]*$')] = None,
    db: Session = Depends(get_db),
) -> list[OwnedCopy]:
    stmt=copies_query(q,collection_type,storage_location_id,unassigned,group)
    stmt=stmt.order_by(*copy_order(collection_type,group)).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


class EditCopyDetails(BaseModel):
    catalog_cover: CoverSelection | None = None
    barcode: BarcodeReading | None = None
    collection_type: Literal['other', 'record', 'comic', 'movie'] = 'other'
    record_details: RecordDetails = Field(default_factory=RecordDetails)
    comic_details: ComicDetails = Field(default_factory=ComicDetails)
    movie_details: MovieDetails = Field(default_factory=MovieDetails)
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str | None = Field(max_length=500, pattern=r'^[^\x00]*$')
    edition_label: str | None = Field(max_length=500, pattern=r'^[^\x00]*$')
    expected_details_revision: int = Field(ge=0, le=2147483646, strict=True)
    expected_identification_revision: int = Field(ge=0, le=2147483646, strict=True)


class DetailEventInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owned_copy_id: UUID
    before_collection_type: str | None
    after_collection_type: str | None
    before_barcode: dict | None
    after_barcode: dict | None
    before_movie_details: dict | None
    after_movie_details: dict | None
    before_comic_details: dict | None
    after_comic_details: dict | None
    before_record_details: dict | None
    after_record_details: dict | None
    before_title: str | None
    after_title: str | None
    before_edition_label: str | None
    after_edition_label: str | None
    identification_revision: int
    before_revision: int
    after_revision: int
    created_at: datetime


@router.post('/{copy_id}/details', response_model=InventoryCopy)
def edit_copy_details(copy_id: UUID, payload: EditCopyDetails, db: Session = Depends(get_db)) -> OwnedCopy:
    from relicrat.copy_details import DetailError, save_details
    try:
        return save_details(db, copy_id, payload.title or None, payload.edition_label,
                            payload.expected_details_revision, payload.expected_identification_revision,
                            collection_type=payload.collection_type if 'collection_type' in payload.model_fields_set else None,
                            record_details=payload.record_details.model_dump(exclude_none=True) if 'record_details' in payload.model_fields_set else None,
                            comic_details=payload.comic_details.model_dump(exclude_none=True) if 'comic_details' in payload.model_fields_set else None,
                            movie_details=payload.movie_details.model_dump(exclude_none=True) if 'movie_details' in payload.model_fields_set else None,
                            barcode=(payload.barcode.model_dump(exclude_none=True) if payload.barcode else {}) if 'barcode' in payload.model_fields_set else None,
                            catalog_cover=payload.catalog_cover)
    except DetailError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from None


@router.get('/{copy_id}/detail-history', response_model=list[DetailEventInfo])
def detail_history(copy_id: UUID, limit: int = Query(default=50, ge=1, le=100),
                   offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)) -> list[CopyDetailEvent]:
    get_copy(copy_id, db)
    return list(db.scalars(select(CopyDetailEvent).where(CopyDetailEvent.owned_copy_id == copy_id)
                          .order_by(CopyDetailEvent.after_revision).limit(limit).offset(offset)))


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
