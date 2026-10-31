"""Bounded comic observations; no catalog identity or ownership is inferred."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from relicrat.collection_types import COLLECTION_TYPES

LIMITS = {field.key: field.max_length for field in COLLECTION_TYPES['comic'].fields}

class ComicDetails(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    issue_number: str | None = Field(default=None, max_length=LIMITS['issue_number'], pattern=r'^[^\x00]*$')
    publisher: str | None = Field(default=None, max_length=LIMITS['publisher'], pattern=r'^[^\x00]*$')

    @field_validator('issue_number', 'publisher')
    @classmethod
    def blank_is_unknown(cls, value):
        return value or None
