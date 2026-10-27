"""PostgreSQL integration checks for the first migration.

Run after: alembic upgrade head
Set TEST_DATABASE_URL to a disposable migrated PostgreSQL database.
"""
import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def conn():
    engine = create_engine(URL)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def test_empty_provisional_copy_is_rejected(conn):
    with pytest.raises(DBAPIError):
        conn.execute(text("INSERT INTO owned_copies (id) VALUES (:id)"), {"id": uuid.uuid4()})
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_description_allows_provisional_copy(conn):
    copy_id = uuid.uuid4()
    conn.execute(text("INSERT INTO owned_copies (id, description) VALUES (:id, :description)"),
                 {"id": copy_id, "description": "Unidentified comic"})
    conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_image_allows_provisional_copy_in_same_transaction(conn):
    copy_id = uuid.uuid4()
    conn.execute(text("INSERT INTO owned_copies (id) VALUES (:id)"), {"id": copy_id})
    conn.execute(text("""INSERT INTO media_assets
        (id, owned_copy_id, storage_key, content_type, byte_size)
        VALUES (:id, :copy_id, :key, 'image/jpeg', 100)"""),
        {"id": uuid.uuid4(), "copy_id": copy_id, "key": f"test/{uuid.uuid4()}"})
    conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_release_cannot_belong_to_different_catalog_item(conn):
    category = uuid.uuid4()
    first, second, release = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    conn.execute(text("INSERT INTO categories (id, slug, name) VALUES (:id, :slug, 'Test')"),
                 {"id": category, "slug": f"test-{category}"})
    for item in (first, second):
        conn.execute(text("""INSERT INTO catalog_items
            (id, category_id, canonical_name, identity_key)
            VALUES (:id, :category, 'Test', :key)"""),
            {"id": item, "category": category, "key": str(item)})
    conn.execute(text("""INSERT INTO releases (id, catalog_item_id, release_key)
        VALUES (:id, :catalog, 'standard')"""), {"id": release, "catalog": first})
    with pytest.raises(DBAPIError):
        conn.execute(text("""INSERT INTO owned_copies
            (id, catalog_item_id, release_id) VALUES (:id, :catalog, :release)"""),
            {"id": uuid.uuid4(), "catalog": second, "release": release})


def test_reassigning_only_photo_cannot_leave_empty_copy(conn):
    first, second, media = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    conn.execute(text("INSERT INTO owned_copies (id) VALUES (:id)"), {"id": first})
    conn.execute(text("INSERT INTO owned_copies (id, description) VALUES (:id, 'Other')"), {"id": second})
    conn.execute(text("""INSERT INTO media_assets
        (id, owned_copy_id, storage_key, content_type, byte_size)
        VALUES (:id, :owner, :key, 'image/jpeg', 100)"""),
        {"id": media, "owner": first, "key": f"test/{media}"})
    conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    with pytest.raises(DBAPIError):
        conn.execute(text("UPDATE media_assets SET owned_copy_id = :new WHERE id = :id"),
                     {"new": second, "id": media})
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
