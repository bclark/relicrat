"""Owner-reviewed checklist matching, independent of catalog identification."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from relicrat.collection_proposals import Identifier
from relicrat.custom_collections import get_collection
from relicrat.database import get_db
from relicrat.models import ChecklistMatch, ChecklistMatchEvent, OwnedCopy

router = APIRouter(prefix='/api/v1/custom-collections', tags=['checklist progress'])


def member_copy(db, collection_id, copy_id, *, lock=False):
    query = select(OwnedCopy).where(OwnedCopy.id == copy_id, OwnedCopy.custom_collection_id == collection_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    copy = db.scalar(query)
    if copy is None:
        raise HTTPException(404, 'Figure not found in this collection')
    return copy


def match_info(value):
    return {'entry_id': value.entry_id if value else None, 'confirmed': value.confirmed if value else False,
            'revision': value.revision if value else 0, 'updated_at': value.updated_at if value else None}


@router.get('/{collection_id}/progress')
def progress(collection_id: UUID, db: Session = Depends(get_db)):
    collection = get_collection(db, collection_id)
    # One aggregate snapshot across all owned copies; independent of browse pagination.
    rows = db.execute(select(ChecklistMatch.entry_id, ChecklistMatch.confirmed, func.count(OwnedCopy.id))
        .select_from(OwnedCopy).outerjoin(ChecklistMatch, ChecklistMatch.owned_copy_id == OwnedCopy.id)
        .where(OwnedCopy.custom_collection_id == collection_id, OwnedCopy.deleted_at.is_(None), OwnedCopy.ownership_status == 'owned')
        .group_by(ChecklistMatch.entry_id, ChecklistMatch.confirmed)).all()
    counts = {(entry, confirmed): count for entry, confirmed, count in rows}
    entries = [dict(entry, confirmed_copies=counts.get((entry['id'], True), 0), pending_copies=counts.get((entry['id'], False), 0))
               for entry in collection.proposal['collection']['checklist']]
    return {'completed': sum(entry['confirmed_copies'] > 0 for entry in entries), 'total': len(entries),
            'unassigned_copies': sum(count for entry, _, count in rows if entry is None), 'entries': entries}


@router.get('/{collection_id}/copies/{copy_id}/checklist-match')
def read_match(collection_id: UUID, copy_id: UUID, db: Session = Depends(get_db)):
    member_copy(db, collection_id, copy_id)
    return match_info(db.get(ChecklistMatch, copy_id))


class ReviewMatch(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_revision: int = Field(ge=0, le=2147483646)
    entry_id: Identifier | None
    confirmed: StrictBool


def save_match(db, collection_id, copy_id, payload):
    try:
        copy = member_copy(db, collection_id, copy_id, lock=True)
        current = db.get(ChecklistMatch, copy_id, populate_existing=True)
        revision = current.revision if current else 0
        if revision != payload.expected_revision:
            raise HTTPException(409, 'This checklist match changed elsewhere. Reload the saved match before reviewing again.')
        if payload.entry_id is None and payload.confirmed:
            raise HTTPException(422, 'Choose a checklist entry before confirming eligibility')
        if payload.entry_id is not None:
            if copy.deleted_at is not None or copy.ownership_status != 'owned':
                raise HTTPException(422, 'Only active owned figures can receive a checklist match')
            collection = get_collection(db, collection_id)
            if payload.entry_id not in {entry['id'] for entry in collection.proposal['collection']['checklist']}:
                raise HTTPException(422, 'Choose an entry from this collection checklist')
        if (current.entry_id if current else None, current.confirmed if current else False) == (payload.entry_id, payload.confirmed):
            db.commit()
            return match_info(current)
        if current is None:
            current = ChecklistMatch(owned_copy_id=copy_id, collection_id=collection_id, revision=1,
                                     entry_id=payload.entry_id, confirmed=payload.confirmed)
            db.add(current)
        else:
            current.entry_id = payload.entry_id
            current.confirmed = payload.confirmed
            current.revision += 1
        # Database trigger validates membership and appends history atomically.
        db.commit()
        db.refresh(current)
        return match_info(current)
    except Exception:
        db.rollback()
        raise


@router.post('/{collection_id}/copies/{copy_id}/checklist-match')
def review_match(collection_id: UUID, copy_id: UUID, payload: ReviewMatch, db: Session = Depends(get_db)):
    return save_match(db, collection_id, copy_id, payload)


@router.get('/{collection_id}/copies/{copy_id}/checklist-history')
def match_history(collection_id: UUID, copy_id: UUID, limit: int = Query(default=20, ge=1, le=100),
                  offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    member_copy(db, collection_id, copy_id)
    events = db.scalars(select(ChecklistMatchEvent).where(ChecklistMatchEvent.owned_copy_id == copy_id)
        .order_by(ChecklistMatchEvent.revision.desc()).limit(limit).offset(offset))
    return [{'before_entry_id': e.before_entry_id, 'after_entry_id': e.after_entry_id, 'before_confirmed': e.before_confirmed,
             'after_confirmed': e.after_confirmed, 'revision': e.revision, 'created_at': e.created_at} for e in events]
