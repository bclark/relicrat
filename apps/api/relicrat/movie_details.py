"""Bounded personal Movie observations, separate from shared catalog identity."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from relicrat.collection_types import COLLECTION_TYPES

LIMITS = {field.key:field.max_length for field in COLLECTION_TYPES['movie'].fields}

class MovieDetails(BaseModel):
    model_config = ConfigDict(extra='forbid',str_strip_whitespace=True)
    media_format: str | None = Field(default=None,max_length=LIMITS['media_format'],pattern=r'^[^\x00]*$')
    studio: str | None = Field(default=None,max_length=LIMITS['studio'],pattern=r'^[^\x00]*$')

    @field_validator('media_format','studio')
    @classmethod
    def blank_is_unknown(cls,value):
        return value or None
