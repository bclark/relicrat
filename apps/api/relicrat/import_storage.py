"""Reviewed CLZ label mapping; preserve existing placements and source evidence."""
import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.models import ImportBatch, ImportCopy, OwnedCopy, StorageLocation
from relicrat.storage import stage_location_assignment

router = APIRouter(prefix='/api/v1/imports', tags=['imports'])
LABEL = func.nullif(func.btrim(ImportCopy.source_row['Storage Box'].astext, ' \t\r\n'), '')
ACTIVE = OwnedCopy.deleted_at.is_(None) & (OwnedCopy.ownership_status == 'owned')
ELIGIBLE = ACTIVE & OwnedCopy.storage_location_id.is_(None) & (OwnedCopy.storage_revision == 0)


class MappingChoice(BaseModel):
    model_config = ConfigDict(extra='forbid')
    label: str = Field(min_length=1, max_length=500, pattern=r'^[^\x00]*$', strict=True)
    destination_id: UUID

    @field_validator('label')
    @classmethod
    def normalized_label(cls, value):
        value = value.strip(' \t\r\n')
        if not value:
            raise ValueError('Choose a nonempty source label')
        return value


class MappingCommit(MappingChoice):
    reviewed_token: str = Field(pattern=r'^[0-9a-f]{64}$', strict=True)


def clz_batch(db, batch_id):
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(404, 'Import batch not found')
    if batch.source != 'clz':
        raise HTTPException(422, 'Only CLZ storage boxes can be mapped here; Discogs folders need a separate review')
    return batch


@router.get('/{batch_id}/storage-labels')
def labels(batch_id: UUID, limit: int = Query(default=20, ge=1, le=100),
           offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    clz_batch(db, batch_id)
    statement = (select(LABEL, func.count(), func.sum(case((ELIGIBLE, 1), else_=0)))
                 .select_from(ImportCopy).join(OwnedCopy, OwnedCopy.id == ImportCopy.owned_copy_id)
                 .where(ImportCopy.batch_id == batch_id, LABEL.is_not(None))
                 .group_by(LABEL).order_by(func.lower(LABEL), LABEL).limit(limit).offset(offset))
    result = [{'label': value[:500], 'supported': len(value) <= 500,
               'copy_count': total, 'eligible_count': eligible, 'preserved_count': total - eligible}
              for value, total, eligible in db.execute(statement)]
    missing = db.scalar(select(func.count()).select_from(ImportCopy)
                        .where(ImportCopy.batch_id == batch_id, LABEL.is_(None)))
    return {'labels': result, 'unlabeled_copy_count': missing}


def mapping_plan(db, batch_id, choice, lock=False):
    clz_batch(db, batch_id)
    destination_query = select(StorageLocation).where(StorageLocation.id == choice.destination_id)
    if lock:
        # Prevent deletion without conflicting with the FK key-share lock used
        # by a simultaneous single-copy assignment (which locks its copy first).
        destination_query = destination_query.with_for_update(read=True, key_share=True)
    destination = db.scalar(destination_query.execution_options(populate_existing=True))
    if destination is None:
        raise HTTPException(404, 'Destination location not found')
    query = (select(OwnedCopy).join(ImportCopy, ImportCopy.owned_copy_id == OwnedCopy.id)
             .where(ImportCopy.batch_id == batch_id, LABEL == choice.label).order_by(OwnedCopy.id))
    if lock:
        query = query.with_for_update(of=OwnedCopy)
    copies = list(db.scalars(query.execution_options(populate_existing=True)))
    if not copies:
        raise HTTPException(404, 'Storage label not found in this import')
    eligible = []
    assigned = previously_moved = inactive = 0
    for copy in copies:
        if copy.deleted_at is not None or copy.ownership_status != 'owned':
            inactive += 1
        elif copy.storage_location_id is not None:
            assigned += 1
        elif copy.storage_revision != 0:
            previously_moved += 1
        else:
            eligible.append(copy)
    # Bind the complete cohort (including preserved copies) and destination to
    # the review. Any intervening edit requires a fresh preview, never a subset.
    state = {'version': 1, 'batch': str(batch_id), 'label': choice.label,
             'destination': [str(destination.id), destination.name, str(destination.parent_id)],
             'copies': [[str(c.id), c.storage_revision, str(c.storage_location_id),
                         c.deleted_at is not None, c.ownership_status,
                         c.details_revision, c.identification_revision] for c in copies]}
    token = hashlib.sha256(json.dumps(state, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    plan = {'label': choice.label, 'destination': {'id': str(destination.id), 'name': destination.name},
            'reviewed_token': token, 'copy_count': len(copies), 'eligible_count': len(eligible),
            'assigned_count': assigned, 'previously_moved_count': previously_moved, 'inactive_count': inactive}
    return plan, eligible


@router.post('/{batch_id}/storage-preview')
def preview(batch_id: UUID, choice: MappingChoice, limit: int = Query(default=20, ge=1, le=100),
            offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    plan, copies = mapping_plan(db, batch_id, choice)
    return {**plan, 'more': len(copies) > offset + limit,
            'copies': [{'id': str(c.id), 'title': c.provisional_title or (c.description or '')[:500] or 'Untitled copy',
                        'issue_number': c.comic_details.get('issue_number'), 'edition_label': c.edition_label}
                       for c in copies[offset:offset + limit]]}


@router.post('/{batch_id}/storage-apply')
def apply(batch_id: UUID, choice: MappingCommit, db: Session = Depends(get_db)):
    try:
        plan, copies = mapping_plan(db, batch_id, choice, lock=True)
        if choice.reviewed_token != plan['reviewed_token']:
            raise HTTPException(409, 'Copies or the destination changed. Preview again before mapping storage.')
        for copy in copies:
            stage_location_assignment(db, copy, choice.destination_id)
        db.commit()
        return {'moved_count': len(copies), 'preserved_count': plan['copy_count'] - len(copies),
                'destination': plan['destination']}
    except Exception:
        db.rollback()
        raise
