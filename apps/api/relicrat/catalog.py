"""Manual catalog identities, independent of physical ownership.

Names are descriptive, not globally unique identities. Manual keys are generated
here; no automatic matching, merging, ownership creation or editing is implied.
"""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.models import CatalogItem, Category, Release

router = APIRouter(prefix='/api/v1/catalog', tags=['catalog'])


class CreateCategory(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200, pattern=r'^[^\x00]*$')


class CreateItem(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    category_id: UUID
    canonical_name: str = Field(min_length=1, max_length=500, pattern=r'^[^\x00]*$')


class CreateRelease(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=500, pattern=r'^[^\x00]*$')


class CategoryInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str


class ItemInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    category_id: UUID
    canonical_name: str


class ReleaseInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    catalog_item_id: UUID
    name: str | None


def save(db, record):
    try:
        db.add(record)
        db.commit()
        return record
    except Exception:
        db.rollback()
        raise


@router.post('/categories', response_model=CategoryInfo, status_code=201)
def create_category(payload: CreateCategory, db: Session = Depends(get_db)):
    return save(db, Category(name=payload.name, slug='manual-' + uuid4().hex))


@router.get('/categories', response_model=list[CategoryInfo])
def list_categories(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
                    db: Session = Depends(get_db)):
    return list(db.scalars(select(Category).order_by(Category.name, Category.id).limit(limit).offset(offset)))


@router.post('/items', response_model=ItemInfo, status_code=201)
def create_item(payload: CreateItem, db: Session = Depends(get_db)):
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=404, detail='Category not found')
    return save(db, CatalogItem(**payload.model_dump(), identity_key='manual-' + uuid4().hex))


@router.get('/items', response_model=list[ItemInfo])
def list_items(q: str = Query(default='', max_length=200, pattern=r'^[^\x00]*$'),
               limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
               db: Session = Depends(get_db)):
    stmt = select(CatalogItem).order_by(CatalogItem.canonical_name, CatalogItem.id).limit(limit).offset(offset)
    if term := q.strip():
        stmt = stmt.where(CatalogItem.canonical_name.icontains(term, autoescape=True))
    return list(db.scalars(stmt))


@router.get('/items/{item_id}', response_model=ItemInfo)
def get_item(item_id: UUID, db: Session = Depends(get_db)):
    record = db.get(CatalogItem, item_id)
    if record is None:
        raise HTTPException(status_code=404, detail='Catalog item not found')
    return record


@router.post('/items/{item_id}/releases', response_model=ReleaseInfo, status_code=201)
def create_release(item_id: UUID, payload: CreateRelease, db: Session = Depends(get_db)):
    get_item(item_id, db)
    return save(db, Release(catalog_item_id=item_id, name=payload.name, release_key='manual-' + uuid4().hex))


@router.get('/items/{item_id}/releases', response_model=list[ReleaseInfo])
def list_releases(item_id: UUID, limit: int = Query(default=50, ge=1, le=100),
                  offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    get_item(item_id, db)
    return list(db.scalars(select(Release).where(Release.catalog_item_id == item_id)
                           .order_by(Release.created_at, Release.id).limit(limit).offset(offset)))


@router.get('/items/{item_id}/releases/{release_id}', response_model=ReleaseInfo)
def get_release(item_id: UUID, release_id: UUID, db: Session = Depends(get_db)):
    record = db.get(Release, release_id)
    if record is None or record.catalog_item_id != item_id:
        raise HTTPException(status_code=404, detail='Release not found for this catalog item')
    return record
