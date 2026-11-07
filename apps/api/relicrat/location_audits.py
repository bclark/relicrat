"""Record observed storage discrepancies without changing inventory."""
import hashlib
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.models import LocationAudit, OwnedCopy, StorageLocation

router = APIRouter(prefix='/api/v1/storage-locations', tags=['storage'])
MAX_COPIES = 1000
Extra = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120, pattern=r'^[^\x00]*$')]


class AuditRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    snapshot: str = Field(pattern=r'^[0-9a-f]{64}$')
    found_ids: list[UUID] = Field(max_length=MAX_COPIES)
    extras: list[Extra] = Field(max_length=25)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def expected_copies(db, location_id):
    rows = db.execute(
        select(OwnedCopy.id, OwnedCopy.provisional_title, OwnedCopy.edition_label, OwnedCopy.storage_revision)
        .where(OwnedCopy.storage_location_id == location_id, OwnedCopy.deleted_at.is_(None),
               OwnedCopy.ownership_status == 'owned')
        .order_by(OwnedCopy.provisional_title, OwnedCopy.id).limit(MAX_COPIES + 1)
    ).all()
    if len(rows) > MAX_COPIES:
        raise HTTPException(422, f'An audit can check up to {MAX_COPIES} copies in one location.')
    return [
        {'id': str(row.id), 'title': row.provisional_title or 'Untitled copy',
         'edition': row.edition_label, 'storage_revision': row.storage_revision}
        for row in rows
    ]


def audit_result(audit):
    return {'id': str(audit.id), 'created_at': audit.created_at, **audit.result} if audit else None


def require_location(db, location_id):
    if db.get(StorageLocation, location_id) is None:
        raise HTTPException(404, 'Location not found')


@router.get('/{location_id}/audits')
def prepare_audit(location_id: UUID, db: Session = Depends(get_db)):
    require_location(db, location_id)
    copies = expected_copies(db, location_id)
    latest = db.scalar(select(LocationAudit).where(LocationAudit.location_id == location_id)
                       .order_by(LocationAudit.created_at.desc(), LocationAudit.id.desc()).limit(1))
    return {'copies': copies, 'snapshot': digest(copies), 'latest': audit_result(latest)}


@router.post('/{location_id}/audits')
def save_audit(location_id: UUID, payload: AuditRequest, db: Session = Depends(get_db)):
    request_digest = digest(payload.model_dump(mode='json'))
    prior = db.get(LocationAudit, payload.request_id)
    if prior is None:
        require_location(db, location_id)
        copies = expected_copies(db, location_id)
        if digest(copies) != payload.snapshot:
            raise HTTPException(409, 'The expected contents changed. Start a fresh check.')
        found = {str(copy_id) for copy_id in payload.found_ids}
        if not found.issubset({copy['id'] for copy in copies}):
            raise HTTPException(422, 'Only expected copies can be marked found.')
        result = {'copies': [{**copy, 'found': copy['id'] in found} for copy in copies], 'extras': payload.extras}
        db.execute(insert(LocationAudit).values(id=payload.request_id, location_id=location_id,
                                               request_digest=request_digest, result=result)
                   .on_conflict_do_nothing(index_elements=['id']))
        prior = db.get(LocationAudit, payload.request_id)
    if prior.location_id != location_id or prior.request_digest != request_digest:
        raise HTTPException(409, 'This audit request ID is already in use.')
    response = audit_result(prior)
    db.commit()
    return response
