"""Bounded personal observations; these never establish catalog identity."""
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecordDetails(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    artist: str | None = Field(default=None, max_length=500, pattern=r'^[^\x00]*$')
    format: str | None = Field(default=None, max_length=100, pattern=r'^[^\x00]*$')

    @field_validator('artist', 'format')
    @classmethod
    def blank_is_unknown(cls, value):
        return value or None
