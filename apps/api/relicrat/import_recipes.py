"""Declarative recipes for reviewed video game CSV intake."""
import hashlib
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from relicrat.catalog import GAME_CATEGORY_SLUG
from relicrat.game_details import GameReleaseDetails
from relicrat.intake import CreateProvisionalCopy
from relicrat.models import CatalogItem, Category, Release

MAX_RECIPE_BYTES = 2048


class RecipeColumns(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    title: str = Field(min_length=1, max_length=120)
    platform: str | None = None
    region: str | None = None
    edition: str | None = None
    notes: str | None = None
    quantity: str | None = None
    media: str | None = None
    packaging: str | None = None
    manual: str | None = None
    inserts: str | None = None

    @model_validator(mode='after')
    def valid_headers(self):
        headers = list(self.model_dump(exclude_none=True).values())
        if any(not header.strip() or len(header) > 120 or '\x00' in header for header in headers):
            raise ValueError('Map fields to nonempty CSV headers of at most 120 characters')
        if len(set(headers)) != len(headers):
            raise ValueError('Map each CSV header at most once')
        return self


class ImportRecipe(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    schema_version: Literal[1]
    name: str = Field(min_length=1, max_length=80, pattern=r'^[^\x00-\x1f\x7f]+$')
    collection: Literal['game']
    columns: RecipeColumns

    @property
    def fingerprint(self):
        return hashlib.sha256(self.model_dump_json(exclude_none=True).encode()).hexdigest()

    def row(self, value):
        fields = {target: value(header) for target, header in self.columns.model_dump(exclude_none=True).items()}
        quantity = fields.get('quantity') or '1'
        if not quantity.isascii() or not quantity.isdecimal() or len(quantity) > 5 or not 1 <= int(quantity) <= 10000:
            raise ValueError('Quantity must be a whole number from 1 to 10,000')
        release = {key: fields[key] for key in ('platform', 'region', 'edition') if fields.get(key)}
        contents = {key: fields[key] for key in ('media', 'packaging', 'manual', 'inserts') if fields.get(key)}
        return (
            CreateProvisionalCopy(
                title=fields['title'], collection_type='game', description=fields.get('notes'),
                game_contents=contents,
            ),
            int(quantity),
            GameReleaseDetails.model_validate(release) if release else None,
        )


CLZ_GAMES = ImportRecipe.model_validate_json(Path(__file__).with_name('clz-games.recipe.json').read_bytes())


def stage_game_release(db, title, release):
    """Create a release for the reviewed row without guessing existing catalog identity."""
    db.execute(insert(Category).values(id=uuid4(), name='Video games', slug=GAME_CATEGORY_SLUG)
               .on_conflict_do_nothing(index_elements=[Category.slug]))
    category_id = db.scalar(select(Category.id).where(Category.slug == GAME_CATEGORY_SLUG))
    item = CatalogItem(category_id=category_id, canonical_name=title, identity_key='import-' + uuid4().hex)
    db.add(item)
    db.flush()
    record = Release(catalog_item_id=item.id, attributes={'game': release.model_dump(exclude_none=True)},
                     release_key='import-' + uuid4().hex)
    db.add(record)
    db.flush()
    return item.id, record.id
