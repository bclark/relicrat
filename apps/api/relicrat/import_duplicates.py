"""Explicit decisions about physical copies from separate CSV imports."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from relicrat.models import ImportBatch, ImportCopy, ImportDuplicateDecision, OwnedCopy

EXTERNAL_ID_COLUMNS = {'clz': 'Core ComicID', 'discogs': 'release_id', 'bluray': 'Product ID'}
ID_WHITESPACE = ' \t\r\n\v\f'


class DuplicateDecisionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    request_id: UUID
    first_id: UUID
    second_id: UUID
    first_updated_at: AwareDatetime
    second_updated_at: AwareDatetime
    archive_id: UUID | None = None


def lock_copies(db: Session, left: UUID, right: UUID) -> dict[UUID, OwnedCopy]:
    return {
        copy.id: copy
        for copy in db.scalars(
            select(OwnedCopy).where(OwnedCopy.id.in_((left, right))).order_by(OwnedCopy.id)
            .with_for_update().execution_options(populate_existing=True)
        )
    }


def record_decision(db: Session, batch_id: UUID, request: DuplicateDecisionRequest):
    left, right = sorted((request.first_id, request.second_id))
    if left == right or request.archive_id not in (None, left, right):
        raise HTTPException(422, 'Choose two different copies and archive at most one of them')

    copies = lock_copies(db, left, right)
    prior = db.get(ImportDuplicateDecision, request.request_id)
    if prior is not None:
        if (prior.batch_id, prior.left_id, prior.right_id, prior.archived_id) != (
            batch_id, left, right, request.archive_id
        ):
            raise HTTPException(409, 'This request ID already belongs to another decision')
        return prior

    rows = db.execute(
        select(ImportCopy, ImportBatch.source)
        .join(ImportBatch, ImportBatch.id == ImportCopy.batch_id)
        .where(ImportCopy.owned_copy_id.in_((left, right)))
    ).all()
    if len(rows) != 2 or len(copies) != 2:
        raise HTTPException(404, 'Imported copies not found')
    (first, source), (second, other_source) = rows
    column = EXTERNAL_ID_COLUMNS[source]
    identifier = first.source_row.get(column, '').strip(ID_WHITESPACE)
    if (source != other_source or first.batch_id == second.batch_id
            or batch_id not in (first.batch_id, second.batch_id) or not identifier
            or identifier != second.source_row.get(column, '').strip(ID_WHITESPACE)):
        raise HTTPException(422, 'Choose copies with a shared source ID from two different imports')

    reviewed = {request.first_id: request.first_updated_at, request.second_id: request.second_updated_at}
    if any(copy.deleted_at is not None or copy.ownership_status != 'owned'
           or copy.updated_at != reviewed[copy.id] for copy in copies.values()):
        raise HTTPException(409, 'A copy changed. Reload the comparison before deciding')
    active = db.scalar(
        select(ImportDuplicateDecision.id).where(
            ImportDuplicateDecision.left_id == left, ImportDuplicateDecision.right_id == right,
            ImportDuplicateDecision.undone_at.is_(None),
        )
    )
    if active is not None:
        raise HTTPException(409, 'This pair already has a decision. Review or undo it in the decision history')

    decision = ImportDuplicateDecision(
        id=request.request_id, batch_id=batch_id, left_id=left, right_id=right,
        archived_id=request.archive_id, created_at=datetime.now(timezone.utc),
    )
    if request.archive_id is not None:
        copies[request.archive_id].deleted_at = decision.created_at
    db.add(decision)
    return decision


def undo_decision(db: Session, batch_id: UUID, decision_id: UUID):
    decision = db.get(ImportDuplicateDecision, decision_id)
    if decision is None or not db.scalar(select(
        select(ImportCopy).where(
            ImportCopy.owned_copy_id.in_((decision.left_id, decision.right_id)),
            ImportCopy.batch_id == batch_id,
        ).exists()
    )):
        raise HTTPException(404, 'Duplicate decision not found')
    copies = lock_copies(db, decision.left_id, decision.right_id)
    db.refresh(decision)
    if decision.undone_at is not None:
        return decision
    if decision.archived_id is not None:
        archived = copies[decision.archived_id]
        if archived.deleted_at != decision.created_at or archived.ownership_status != 'owned':
            raise HTTPException(409, 'This copy changed after it was archived')
        archived.deleted_at = None
    decision.undone_at = datetime.now(timezone.utc)
    return decision
