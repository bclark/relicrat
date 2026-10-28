"""Schema-level tests; use PostgreSQL integration tests for DB-specific constraints."""
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from relicrat.models import Base


def test_foundation_and_reconciliation_tables():
    assert set(Base.metadata.tables) == {
        "categories", "catalog_items", "releases", "owned_copies",
        "storage_locations", "media_assets", "reconciliation_events",
        "copy_location_events", "storage_hierarchy_guard",
    }


def test_owned_copy_identification_optional():
    table = Base.metadata.tables["owned_copies"]
    assert table.c.catalog_item_id.nullable
    assert table.c.release_id.nullable
    assert table.c.storage_location_id.nullable


def test_release_catalog_consistency_is_declared():
    table = Base.metadata.tables["owned_copies"]
    assert any(
        isinstance(c, ForeignKeyConstraint)
        and set(c.column_keys) == {"release_id", "catalog_item_id"}
        for c in table.constraints
    )
