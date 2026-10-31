"""One owner's durable form preferences, separate from catalog and ownership."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from relicrat.database import get_db
from relicrat.models import CollectionSettings
from relicrat.collection_types import COLLECTION_TYPES, CollectionType

router = APIRouter(prefix='/api/v1/collection-settings', tags=['collection settings'])
RecordField = Literal['artist', 'format', 'edition', 'notes']


class SettingsValues(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['not_started', 'skipped', 'configured']
    records_enabled: bool = Field(strict=True)
    default_type: Literal['other', 'record']
    record_fields: list[RecordField] = Field(max_length=4)

    @field_validator('record_fields')
    @classmethod
    def unique_fields(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('Choose each field once')
        return value

    @model_validator(mode='after')
    def valid_default(self):
        if self.default_type == 'record' and not self.records_enabled:
            raise ValueError('Enable Records before making it the default')
        return self


class SettingsInfo(SettingsValues):
    model_config = ConfigDict(from_attributes=True)
    revision: int


class SaveSettings(SettingsValues):
    expected_revision: int = Field(ge=0, le=2147483646, strict=True)


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
        values = payload.model_dump(exclude={'expected_revision'})
        if any(getattr(settings, key) != value for key, value in values.items()):
            for key, value in values.items():
                setattr(settings, key, value)
            settings.revision += 1
        db.commit()
        return settings
    except Exception:
        db.rollback()
        raise
