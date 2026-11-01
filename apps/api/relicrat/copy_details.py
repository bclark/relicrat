"""Atomic, revision-checked edits to the physical copy's own labels."""
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from relicrat.catalog_cover import stage_cover
from relicrat.models import CopyDetailEvent, MediaAsset, OwnedCopy


class DetailError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def save_details(db: Session, copy_id: UUID, title: str | None, edition_label: str | None,
                 expected_details_revision: int, expected_identification_revision: int, *,
                 collection_type: str | None = None, record_details: dict | None = None, comic_details: dict | None = None,
                 barcode: dict | None = None, catalog_cover=None) -> OwnedCopy:
    try:
        copy = db.scalar(select(OwnedCopy).where(OwnedCopy.id == copy_id)
                         .with_for_update().execution_options(populate_existing=True))
        if copy is None or copy.deleted_at is not None:
            raise DetailError(404, 'Copy not found')
        if (copy.details_revision, copy.identification_revision) != (expected_details_revision, expected_identification_revision):
            raise DetailError(409, 'This copy changed elsewhere. Reload the copy before editing its details.')
        if not title and not (copy.description or '').strip() and db.scalar(select(MediaAsset.id).where(MediaAsset.owned_copy_id == copy_id).limit(1)) is None:
            raise DetailError(422, 'Keep a title, notes or a photo so this copy can be recognized.')
        next_type = copy.collection_type if collection_type is None else collection_type
        next_record = copy.record_details if record_details is None else record_details
        next_comic = copy.comic_details if comic_details is None else comic_details
        next_barcode = copy.barcode if barcode is None else barcode
        if (copy.provisional_title, copy.edition_label, copy.collection_type, copy.record_details, copy.comic_details, copy.barcode) == (title, edition_label, next_type, next_record, next_comic, next_barcode):
            with stage_cover(db,copy,next_type,catalog_cover):
                db.commit()
            return copy
        db.add(CopyDetailEvent(owned_copy_id=copy.id,
            before_barcode=copy.barcode, after_barcode=next_barcode,
            before_title=copy.provisional_title, after_title=title,
            before_collection_type=copy.collection_type, after_collection_type=next_type,
            before_record_details=copy.record_details, after_record_details=next_record,
            before_comic_details=copy.comic_details, after_comic_details=next_comic,
            before_edition_label=copy.edition_label, after_edition_label=edition_label,
            identification_revision=copy.identification_revision,
            before_revision=copy.details_revision, after_revision=copy.details_revision + 1))
        copy.barcode = next_barcode
        copy.collection_type = next_type
        copy.record_details = next_record
        copy.comic_details = next_comic
        copy.provisional_title = title
        copy.edition_label = edition_label
        copy.details_revision += 1
        with stage_cover(db,copy,next_type,catalog_cover):
            db.commit()
        return copy
    except Exception:
        db.rollback()
        raise
