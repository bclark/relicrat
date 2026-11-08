"""Manual catalog identities, independent of physical ownership.

Names are descriptive, not globally unique identities. Manual keys are generated
here; no automatic matching, merging, ownership creation or editing is implied.
"""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from relicrat.game_details import GameReleaseDetails
from relicrat.database import get_db
from relicrat.models import CatalogItem, Category, Release

GAME_CATEGORY_SLUG = 'video-games'

router = APIRouter(prefix='/api/v1/catalog', tags=['catalog'])


class CreateCategory(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200, pattern=r'^[^\x00]*$')


class CreateItem(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    category_id: UUID | None = None
    video_game: bool = False
    canonical_name: str = Field(min_length=1, max_length=500, pattern=r'^[^\x00]*$')

    @model_validator(mode='after')
    def choose_category(self):
        if (self.category_id is not None) == self.video_game:
            raise ValueError('Choose a category or create a video game title')
        return self


class CreateRelease(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=500, pattern=r'^[^\x00]*$')
    game_details: GameReleaseDetails | None = None

    @model_validator(mode='after')
    def require_details(self):
        if self.name is None and self.game_details is None:
            raise ValueError('Enter a release name or game release details')
        return self


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
    game_details: GameReleaseDetails | None


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
    category_id = payload.category_id
    if payload.video_game:
        db.execute(insert(Category).values(id=uuid4(), name='Video games', slug=GAME_CATEGORY_SLUG)
                   .on_conflict_do_nothing(index_elements=[Category.slug]))
        category_id = db.scalar(select(Category.id).where(Category.slug == GAME_CATEGORY_SLUG))
    elif db.get(Category, category_id) is None:
        raise HTTPException(status_code=404, detail='Category not found')
    return save(db, CatalogItem(category_id=category_id, canonical_name=payload.canonical_name,
                                identity_key='manual-' + uuid4().hex))


@router.get('/items', response_model=list[ItemInfo])
def list_items(q: str = Query(default='', max_length=200, pattern=r'^[^\x00]*$'),
               video_game: bool = Query(default=False),
               limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
               db: Session = Depends(get_db)):
    stmt = select(CatalogItem).order_by(CatalogItem.canonical_name, CatalogItem.id).limit(limit).offset(offset)
    if video_game:
        stmt = stmt.join(Category).where(Category.slug == GAME_CATEGORY_SLUG)
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
    attributes = {'game': payload.game_details.model_dump(exclude_none=True)} if payload.game_details else {}
    return save(db, Release(catalog_item_id=item_id, name=payload.name,
                            attributes=attributes, release_key='manual-' + uuid4().hex))


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
