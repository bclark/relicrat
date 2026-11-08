"""Shared release metadata and independently observed physical game contents."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GameReleaseDetails(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    platform: str | None = Field(default=None, min_length=1, max_length=100, pattern=r'^[^\x00]*$')
    region: str | None = Field(default=None, min_length=1, max_length=100, pattern=r'^[^\x00]*$')
    edition: str | None = Field(default=None, min_length=1, max_length=500, pattern=r'^[^\x00]*$')

    @model_validator(mode='after')
    def require_observation(self):
        if not any((self.platform, self.region, self.edition)):
            raise ValueError('Enter at least one release detail')
        return self


ComponentStatus = Literal['present', 'missing', 'not_applicable']


class GameContents(BaseModel):
    model_config = ConfigDict(extra='forbid')

    media: ComponentStatus | None = None
    packaging: ComponentStatus | None = None
    manual: ComponentStatus | None = None
    inserts: ComponentStatus | None = None
