"""Transactional manual identification; callers supply the revision they read."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from relicrat.models import CatalogItem, OwnedCopy, ReconciliationEvent, Release


class ReconciliationError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def reconcile(db: Session, copy_id: UUID, catalog_item_id: UUID,
              release_id: UUID | None, expected_revision: int) -> OwnedCopy:
    try:
        copy = db.scalar(select(OwnedCopy).where(OwnedCopy.id == copy_id)
                         .with_for_update().execution_options(populate_existing=True))
        if copy is None or copy.deleted_at is not None:
            raise ReconciliationError(404, "Collectible not found")
        if copy.identification_revision != expected_revision:
            raise ReconciliationError(409, "Stale identification revision; reload the collectible")
        if db.get(CatalogItem, catalog_item_id) is None:
            raise ReconciliationError(404, "Catalog item not found")
        if release_id is not None:
            release = db.get(Release, release_id)
            if release is None:
                raise ReconciliationError(404, "Release not found")
            if release.catalog_item_id != catalog_item_id:
                raise ReconciliationError(422, "Release belongs to another catalog item")
        if (copy.catalog_item_id, copy.release_id, copy.identification_status) == (catalog_item_id, release_id, "identified"):
            db.commit()  # Release the lock; no UPDATE or duplicate event.
            return copy
        db.add(ReconciliationEvent(
            owned_copy_id=copy.id,
            before_catalog_item_id=copy.catalog_item_id, before_release_id=copy.release_id,
            after_catalog_item_id=catalog_item_id, after_release_id=release_id,
            before_status=copy.identification_status, after_status="identified",
            before_revision=copy.identification_revision,
            after_revision=copy.identification_revision + 1,
        ))
        copy.catalog_item_id = catalog_item_id
        copy.release_id = release_id
        copy.identification_status = "identified"
        copy.identification_revision += 1
        db.commit()
        return copy
    except Exception:
        db.rollback()
        raise
