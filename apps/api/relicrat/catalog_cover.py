"""Explicit optional artwork import, joined to the ordinary final save."""
from contextlib import contextmanager
from urllib.parse import urlsplit
from pydantic import BaseModel,ConfigDict,Field
from fastapi import HTTPException
from sqlalchemy import select
from relicrat.collection_types import COLLECTION_TYPES
from relicrat.barcode_providers import PROVIDERS
from relicrat.musicbrainz import LookupUnavailable
from relicrat.media import staged_image
from relicrat.models import MediaAsset

class CoverSelection(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    provider:str=Field(pattern=r'^[a-z][a-z0-9_-]{0,39}$')
    candidate_id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')

@contextmanager
def stage_cover(db,copy,collection_type,selection):
    if selection is None:
        yield
        return
    config=COLLECTION_TYPES[collection_type].lookup
    if not config or not config.cover_art or config.provider!=selection.provider:
        raise HTTPException(422,'This cover is not supported by the selected collection type. Review the match again.')
    provider=PROVIDERS[config.provider]
    if not provider.get('cover') or not provider.get('source_url'):
        raise HTTPException(422,'This provider does not support saving cover artwork.')
    try:
        ident=provider.get('canonical_id',str)(selection.candidate_id)
        ident=CoverSelection(provider=selection.provider,candidate_id=ident).candidate_id
        source=provider['source_url'](ident);url=urlsplit(source)
        if len(source)>1000 or url.scheme!='https' or url.username or url.password or url.port not in (None,443) or 'https://'+str(url.hostname)!=provider['source_origin']:raise ValueError()
    except (ValueError,TypeError):raise HTTPException(422,'Invalid catalog cover reference.') from None
    db.flush()
    existing=db.scalar(select(MediaAsset.id).where(MediaAsset.owned_copy_id==copy.id,MediaAsset.source_provider==selection.provider,MediaAsset.source_id==ident))
    if existing:
        yield
        return
    try:data=provider['cover'](ident)
    except LookupUnavailable:raise HTTPException(422,'The selected cover is unavailable. Nothing was saved. Remove the cover selection or try again.') from None
    with staged_image(db,copy.id,data,source_provider=selection.provider,source_id=ident,source_url=source):
        yield
