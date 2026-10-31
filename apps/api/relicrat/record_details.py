"""Bounded personal observations; these never establish catalog identity."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from relicrat.collection_types import COLLECTION_TYPES

LIMITS = {field.key: field.max_length for field in COLLECTION_TYPES['record'].fields}


class RecordDetails(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    artist: str | None = Field(default=None, max_length=LIMITS['artist'], pattern=r'^[^\x00]*$')
    format: str | None = Field(default=None, max_length=LIMITS['format'], pattern=r'^[^\x00]*$')

    @field_validator('artist', 'format')
    @classmethod
    def blank_is_unknown(cls, value):
        return value or None
