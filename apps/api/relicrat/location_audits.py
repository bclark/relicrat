"""Record storage observations and explicitly confirmed resolutions."""
import hashlib
import json
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.intake import CreateProvisionalCopy, stage_copy
from relicrat.storage import stage_location_assignment
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
    return {'id': str(audit.id), 'created_at': audit.created_at, 'resolutions': {}, **audit.result} if audit else None


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


# Every stored resolution belongs to a single original finding.
AUDIT_COUNTS = """
    SELECT id, location_id, created_at,
           jsonb_array_length(result->'copies') - missing AS found,
           missing, jsonb_array_length(result->'extras') AS extra,
           missing + jsonb_array_length(result->'extras') -
               (SELECT count(*) FROM jsonb_object_keys(coalesce(result->'resolutions', '{}'))) AS unresolved
    FROM location_audits
    CROSS JOIN LATERAL (
        SELECT jsonb_array_length(jsonb_path_query_array(
            result->'copies', '$[*] ? (@.found == false)')) AS missing
    ) AS counts
"""


@router.get('/audits/open')
def open_audit_locations(
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return query_open_audit_locations(db, limit, offset)


def query_open_audit_locations(db: Session, limit: int, offset: int):
    rows = db.execute(text(f"""
        SELECT l.id, l.name, CAST(sum(a.unresolved) AS bigint) AS unresolved
        FROM ({AUDIT_COUNTS}) AS a
        JOIN storage_locations AS l ON l.id = a.location_id
        WHERE a.unresolved > 0
        GROUP BY l.id, l.name
        ORDER BY l.name, l.id
        LIMIT :limit OFFSET :offset
    """), {'limit': limit, 'offset': offset}).mappings()
    return [dict(row) for row in rows]


@router.get('/{location_id}/audits/history')
def audit_history(
    location_id: UUID, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    require_location(db, location_id)
    rows = db.execute(text(f"""
        {AUDIT_COUNTS}
        WHERE location_id = :location_id
        ORDER BY created_at DESC, id DESC
        LIMIT :limit OFFSET :offset
    """), {'location_id': location_id, 'limit': limit, 'offset': offset}).mappings()
    return [dict(row) for row in rows]


@router.get('/{location_id}/audits/{audit_id}')
def read_audit(location_id: UUID, audit_id: UUID, db: Session = Depends(get_db)):
    audit = db.scalar(select(LocationAudit).where(
        LocationAudit.id == audit_id, LocationAudit.location_id == location_id))
    if audit is None:
        raise HTTPException(404, 'Audit not found')
    return audit_result(audit)


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

class ResolutionAction(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Found(ResolutionAction):
    action: Literal['found']
    copy_id: UUID


class MoveMissing(ResolutionAction):
    action: Literal['move_missing']
    copy_id: UUID
    destination_id: UUID
    expected_storage_revision: int = Field(ge=0)


class MatchExtra(ResolutionAction):
    action: Literal['match_extra']
    extra_index: int = Field(ge=0)
    copy_id: UUID
    expected_storage_revision: int = Field(ge=0)


class CreateExtra(ResolutionAction):
    action: Literal['create_extra']
    extra_index: int = Field(ge=0)
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500, pattern=r'^[^\x00]*$')]
    collection_type: Literal['other', 'record', 'comic', 'movie'] = 'other'


Resolution = Annotated[Found | MoveMissing | MatchExtra | CreateExtra, Field(discriminator='action')]


@router.post('/{location_id}/audits/{audit_id}/resolutions')
def resolve_audit(location_id: UUID, audit_id: UUID, payload: Resolution, db: Session = Depends(get_db)):
    audit = db.scalar(select(LocationAudit).where(
        LocationAudit.id == audit_id, LocationAudit.location_id == location_id).with_for_update())
    if audit is None:
        raise HTTPException(404, 'Audit not found')

    expected = {row['id']: row for row in audit.result['copies']}
    if isinstance(payload, (Found, MoveMissing)):
        observed = expected.get(str(payload.copy_id))
        if observed is None or observed['found']:
            raise HTTPException(422, 'Only a copy recorded as missing can be resolved here.')
        key = f'missing:{payload.copy_id}'
    else:
        if payload.extra_index >= len(audit.result['extras']):
            raise HTTPException(422, 'Extra item not found in this audit.')
        key = f'extra:{payload.extra_index}'

    resolutions = audit.result.get('resolutions', {})
    request_digest = digest(payload.model_dump(mode='json'))
    if prior := resolutions.get(key):
        if prior['request_digest'] != request_digest:
            raise HTTPException(409, 'This discrepancy is already resolved. Reopen the audit to review it.')
        return audit_result(audit)

    destination = location_id
    if isinstance(payload, CreateExtra):
        copy = stage_copy(db, CreateProvisionalCopy(title=payload.title, collection_type=payload.collection_type))
        db.flush()
    else:
        copy = db.scalar(select(OwnedCopy).where(OwnedCopy.id == payload.copy_id).with_for_update())
        if copy is None or copy.deleted_at is not None or copy.ownership_status != 'owned':
            raise HTTPException(404, 'Active owned copy not found.')
        if isinstance(payload, Found):
            if copy.storage_location_id != location_id:
                raise HTTPException(409, 'This copy is assigned elsewhere. Choose where you found it.')
        else:
            if copy.storage_revision != payload.expected_storage_revision:
                raise HTTPException(409, 'The copy location changed. Select it again before confirming.')
            if isinstance(payload, MoveMissing):
                destination = payload.destination_id
                if destination == location_id:
                    raise HTTPException(422, 'Choose another location or mark the copy found here.')
                require_location(db, destination)
            elif str(copy.id) in expected or any(
                name.startswith('extra:') and value['copy_id'] == str(copy.id)
                for name, value in resolutions.items()
            ):
                raise HTTPException(422, 'This copy already accounts for an item in this audit.')

    stage_location_assignment(db, copy, destination)
    resolution = {
        'action': payload.action, 'copy_id': str(copy.id), 'title': copy.provisional_title or 'Untitled copy',
        'location_id': str(destination), 'location_name': db.get(StorageLocation, destination).name,
        'resolved_at': datetime.now(timezone.utc).isoformat(), 'request_digest': request_digest,
    }
    audit.result = {**audit.result, 'resolutions': {**resolutions, key: resolution}}
    response = audit_result(audit)
    db.commit()
    return response
