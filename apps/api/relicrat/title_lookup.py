"""Owner-only external title search. It does not read or write inventory."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from relicrat.barcode_providers import TITLE_PROVIDERS
from relicrat.barcode_errors import LookupBusy, LookupUnavailable
from relicrat.collection_types import COLLECTION_TYPES

router = APIRouter(prefix='/api/v1/title-lookups', tags=['title lookup'])


class TitleQuery(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=2, max_length=500, pattern=r'^[^\x00-\x1f\x7f]+$')


@router.post('/game')
def lookup(query: TitleQuery):
    config = COLLECTION_TYPES['game'].title_lookup
    provider = TITLE_PROVIDERS[config.provider] if config else None
    if provider is None or not provider["enabled"]():
        raise HTTPException(404, 'Online game title search is not configured.')
    try:
        candidates = provider["search"](query.title, config.max_results)
    except LookupBusy as error:
        raise HTTPException(429, 'Catalog search is busy. Try again shortly.',
                            headers={'Retry-After': str(error.retry_after)}) from None
    except LookupUnavailable:
        raise HTTPException(503, 'Online game title search is unavailable.') from None
    return {'provider': config.provider, 'provider_label': provider['label'], 'candidates': candidates}
