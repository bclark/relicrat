"""Shared validation and staging of provisional physical copies."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session
from relicrat.models import OwnedCopy
from relicrat.record_details import RecordDetails
from relicrat.comic_details import ComicDetails
from relicrat.collection_types import COLLECTION_TYPES

class CreateProvisionalCopy(BaseModel):
    model_config = ConfigDict(extra='forbid')
    collection_type: Literal['other', 'record', 'comic'] = 'other'
    record_details: RecordDetails = Field(default_factory=RecordDetails)
    comic_details: ComicDetails = Field(default_factory=ComicDetails)
    edition_label: str | None = Field(default=None, max_length=500, pattern=r'^[^\x00]*$')
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def require_content(self) -> "CreateProvisionalCopy":
        self.title = self.title.strip() if self.title else None
        self.description = self.description.strip() if self.description else None
        if self.collection_type != 'record' and self.record_details.model_dump(exclude_none=True):
            raise ValueError(f"Choose {COLLECTION_TYPES['record'].label} before adding artist or format")
        if self.collection_type != 'comic' and self.comic_details.model_dump(exclude_none=True):
            raise ValueError('Choose Comic before adding issue number or publisher')
        if not self.title and not self.description:
            raise ValueError("A title or description is required")
        return self


def stage_copy(db: Session, payload: CreateProvisionalCopy) -> OwnedCopy:
    copy = OwnedCopy(provisional_title=payload.title, description=payload.description, edition_label=payload.edition_label.strip() if payload.edition_label else None, collection_type=payload.collection_type, record_details=payload.record_details.model_dump(exclude_none=True), comic_details=payload.comic_details.model_dump(exclude_none=True))
    db.add(copy)
    return copy
