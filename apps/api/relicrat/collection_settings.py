"""One owner's durable form preferences, separate from catalog and ownership."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from relicrat.database import get_db
from relicrat.models import CollectionSettings, OwnedCopy
from relicrat.collection_types import COLLECTION_TYPES, CollectionType

router = APIRouter(prefix='/api/v1/collection-settings', tags=['collection settings'])
RecordField = Literal['artist', 'format', 'edition', 'notes']
MovieField = Literal['media_format','studio','edition','notes']
ComicField = Literal['issue_number', 'publisher', 'edition', 'notes']


class SettingsValues(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['not_started', 'skipped', 'configured']
    records_enabled: bool = Field(strict=True)
    default_type: Literal['other', 'record', 'comic', 'movie']
    record_fields: list[RecordField] = Field(max_length=4)
    comics_enabled: bool = Field(default=False, strict=True)
    comic_fields: list[ComicField] = Field(default_factory=lambda: ['issue_number','publisher','edition','notes'], max_length=4)

    movies_enabled: bool = Field(default=False, strict=True)
    movie_fields: list[MovieField] = Field(default_factory=lambda: ['media_format','studio','edition','notes'], max_length=4)

    @field_validator('record_fields', 'comic_fields', 'movie_fields')
    @classmethod
    def unique_fields(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('Choose each field once')
        return value

    @model_validator(mode='after')
    def valid_default(self):
        if self.default_type == 'record' and not self.records_enabled:
            raise ValueError(f"Enable {COLLECTION_TYPES['record'].plural_label} before making it the default")
        if self.default_type == 'comic' and 'comics_enabled' in self.model_fields_set and not self.comics_enabled:
            raise ValueError('Enable Comics before making it the default')
        if self.default_type == 'movie' and 'movies_enabled' in self.model_fields_set and not self.movies_enabled:
            raise ValueError('Enable Movies before making it the default')
        return self


class SettingsInfo(SettingsValues):
    model_config = ConfigDict(from_attributes=True)
    revision: int


class SaveSettings(SettingsValues):
    expected_revision: int = Field(ge=0, le=2147483646, strict=True)


@router.get('/artist-suggestions', response_model=list[str])
def artist_suggestions(q: str = Query(default='', max_length=500, pattern=r'^[^\x00]*$'),
                       db: Session = Depends(get_db)):
    return saved_suggestions(db, OwnedCopy.record_details['artist'].astext, 'record', q)


@router.get('/studio-suggestions', response_model=list[str])
def studio_suggestions(q: str = Query(default='',max_length=250,pattern=r'^[^\x00]*$'),db: Session=Depends(get_db)):
    return saved_suggestions(db,OwnedCopy.movie_details['studio'].astext,'movie',q)


@router.get('/publisher-suggestions', response_model=list[str])
def publisher_suggestions(q: str = Query(default='', max_length=250, pattern=r'^[^\x00]*$'),
                          db: Session = Depends(get_db)):
    return saved_suggestions(db, OwnedCopy.comic_details['publisher'].astext, 'comic', q)


def saved_suggestions(db, column, collection_type, q):
    # The routes supply fixed columns/type IDs; clients never choose expressions.
    value = func.btrim(column)
    query = select(func.min(value.collate('C'))).where(OwnedCopy.deleted_at.is_(None),
        OwnedCopy.collection_type == collection_type, value.is_not(None), value != '')
    if term := q.strip():
        query = query.where(value.istartswith(term, autoescape=True))
    return list(db.scalars(query.group_by(func.lower(value)).order_by(func.lower(value).collate('C')).limit(20)))


@router.get('/types', response_model=dict[str, CollectionType])
def read_types():
    return COLLECTION_TYPES


@router.get('', response_model=SettingsInfo)
def read_settings(db: Session = Depends(get_db)):
    settings = db.get(CollectionSettings, 1)
    if settings is None:
        raise HTTPException(503, 'Collection settings are unavailable')
    return settings


@router.post('', response_model=SettingsInfo)
def save_settings(payload: SaveSettings, db: Session = Depends(get_db)):
    try:
        settings = db.scalar(select(CollectionSettings).where(CollectionSettings.id == 1)
                             .with_for_update().execution_options(populate_existing=True))
        if settings is None:
            raise HTTPException(503, 'Collection settings are unavailable')
        if settings.revision != payload.expected_revision:
            raise HTTPException(409, 'Collection settings changed elsewhere. Reload settings and review your choices.')
        values = payload.model_dump(exclude={'expected_revision'}, exclude_unset=True)
        effective_default = values.get('default_type', settings.default_type)
        if effective_default == 'comic' and not values.get('comics_enabled', settings.comics_enabled):
            raise HTTPException(422, 'Enable Comics before making it the default')
        if effective_default == 'movie' and not values.get('movies_enabled', settings.movies_enabled):
            raise HTTPException(422, 'Enable Movies before making it the default')
        if any(getattr(settings, key) != value for key, value in values.items()):
            for key, value in values.items():
                setattr(settings, key, value)
            settings.revision += 1
        db.commit()
        return settings
    except Exception:
        db.rollback()
        raise
