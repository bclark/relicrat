"""Integration tests. Requires a migrated disposable PostgreSQL database.

TEST_DATABASE_URL must point to the dedicated test database, not production.
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.main import app
from relicrat.models import CatalogItem, Category, OwnedCopy, Release

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not configured")


@pytest.fixture
def client():
    engine = create_engine(URL)
    connection = engine.connect()
    outer = connection.begin()

    def override_db():
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as test_client:
            yield test_client, connection
    finally:
        app.dependency_overrides.pop(get_db, None)
        outer.rollback()
        connection.close()
        engine.dispose()


def test_create_and_retrieve_title_only(client):
    client, _ = client
    response = client.post("/api/v1/inventory", json={"title": "  Mystery comic  "})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Mystery comic"
    assert body["description"] is None
    assert body["identification_status"] == "unidentified"
    assert client.get(f"/api/v1/inventory/{body['id']}").json()["id"] == body["id"]


def test_description_only(client):
    client, _ = client
    response = client.post("/api/v1/inventory", json={"description": "  Unknown record  "})
    assert response.status_code == 201, response.text
    assert response.json()["description"] == "Unknown record"


@pytest.mark.parametrize("payload", [{}, {"title": "  "}, {"description": ""}, {"title": None, "description": None}])
def test_reject_empty_copy(client, payload):
    client, _ = client
    assert client.post("/api/v1/inventory", json=payload).status_code == 422


def test_missing_copy(client):
    client, _ = client
    assert client.get(f"/api/v1/inventory/{uuid.uuid4()}").status_code == 404


def test_list_newest_first(client):
    client, connection = client
    a = client.post("/api/v1/inventory", json={"title": "First"}).json()
    b = client.post("/api/v1/inventory", json={"title": "Second"}).json()
    # The fixture uses one outer transaction, so PostgreSQL now() gives both
    # inserts the same timestamp. Set distinct values to test the API ordering.
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        session.execute(update(OwnedCopy).where(OwnedCopy.id == uuid.UUID(a["id"])).values(created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
        session.execute(update(OwnedCopy).where(OwnedCopy.id == uuid.UUID(b["id"])).values(created_at=datetime(2026, 1, 2, tzinfo=timezone.utc)))
        session.commit()
    result = client.get("/api/v1/inventory?limit=2").json()
    ids = [item["id"] for item in result]
    assert a["id"] in ids and b["id"] in ids
    assert ids.index(b["id"]) < ids.index(a["id"])


def test_invalid_pagination(client):
    client, _ = client
    assert client.get("/api/v1/inventory?limit=101").status_code == 422
    assert client.get("/api/v1/inventory?offset=-1").status_code == 422


def test_reject_oversized_description(client):
    client, _ = client
    assert client.post("/api/v1/inventory", json={"description": "x" * 10001}).status_code == 422


@pytest.fixture
def search_inventory(client):
    api, connection = client
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        category = Category(slug=str(uuid.uuid4()), name="Synthetic search")
        db.add(category)
        db.flush()
        item = CatalogItem(category_id=category.id, identity_key="knight", canonical_name="Copper Knight")
        unowned = CatalogItem(category_id=category.id, identity_key="unowned", canonical_name="Unowned phantom")
        db.add_all([item, unowned])
        db.flush()
        release = Release(catalog_item_id=item.id, release_key="first", name="First printing")
        db.add(release)
        db.flush()
        copy = OwnedCopy(provisional_title="Mystery comic", description="Blue cover", catalog_item_id=item.id, release_id=release.id)
        other = OwnedCopy(provisional_title="Other record")
        db.add_all([copy, other])
        db.commit()
        ids = copy.id, other.id, item.id, release.id
    yield api, connection, *ids


def search(api, q, **pagination):
    response = api.get("/api/v1/inventory", params={"q": q, **pagination})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("q", ["mYsTeRy", "blue cover", "cOpPeR", "PRINTING", "  blue cover  "])
def test_search_each_field_and_trim(search_inventory, q):
    api, _, cid, *_ = search_inventory
    assert [row["id"] for row in search(api, q)] == [str(cid)]


@pytest.mark.parametrize("q", ["", "   ", "\t\n"])
def test_blank_search_preserves_listing(search_inventory, q):
    api, *_ = search_inventory
    assert search(api, q) == api.get("/api/v1/inventory").json()


@pytest.mark.parametrize("needle", ["%", "_", "\\", "/", "' OR 1=1 --", "café"])
def test_search_literal_input(search_inventory, needle):
    api, connection, *_ = search_inventory
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        copy = OwnedCopy(provisional_title=f"Literal {needle} collectible")
        db.add(copy)
        db.commit()
        cid = str(copy.id)
    assert [row["id"] for row in search(api, needle)] == [cid]


def test_search_only_inventory_and_exclude_deleted(search_inventory):
    api, connection, cid, other_id, item_id, *_ = search_inventory
    assert search(api, "Unowned phantom") == []
    assert search(api, "not present") == []
    # NULL identity/description/release fields must not exclude title matches.
    assert [row["id"] for row in search(api, "Other")] == [str(other_id)]
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        db.add(OwnedCopy(catalog_item_id=item_id, provisional_title="Deleted", deleted_at=datetime.now(timezone.utc)))
        db.commit()
    assert [row["id"] for row in search(api, "Copper")] == [str(cid)]


def test_search_null_release_name_and_disposed_copy(search_inventory):
    api, connection, _, _, item_id, *_ = search_inventory
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        release = Release(catalog_item_id=item_id, release_key="unnamed")
        db.add(release)
        db.flush()
        copy = OwnedCopy(catalog_item_id=item_id, release_id=release.id, ownership_status="sold")
        db.add(copy)
        db.commit()
        cid = str(copy.id)
    assert cid in [row["id"] for row in search(api, "Knight")]


def test_search_paginates_copies_without_duplicates(search_inventory):
    api, connection, *_ = search_inventory
    marker = str(uuid.uuid4())
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        item = CatalogItem(category_id=db.get(CatalogItem, search_inventory[4]).category_id,
                           identity_key=marker, canonical_name=marker)
        db.add(item)
        db.flush()
        # Match two fields, with two distinct physical copies of one identity.
        copies = [OwnedCopy(id=uuid.UUID(int=n), catalog_item_id=item.id, provisional_title=marker,
                            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)) for n in (1, 2, 3)]
        db.add_all(copies)
        db.commit()
    expected = [str(uuid.UUID(int=n)) for n in (3, 2, 1)]
    assert [row["id"] for row in search(api, marker)] == expected
    pages = [search(api, marker, limit=1, offset=n) for n in range(4)]
    assert [page[0]["id"] for page in pages[:3]] == expected
    assert pages[3] == []


def test_search_validation(search_inventory):
    api, *_ = search_inventory
    assert search(api, "x" * 200) == []
    for params in ({"q": "x" * 201}, {"q": "\x00"}, {"q": "Copper", "limit": 0},
                   {"q": "Copper", "limit": 101}, {"q": "Copper", "offset": -1}):
        assert api.get("/api/v1/inventory", params=params).status_code == 422


def test_search_preserves_copy_history_and_photo(search_inventory, tmp_path, monkeypatch):
    import io
    from PIL import Image

    api, _, cid, _, item_id, release_id = search_inventory
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    base = f"/api/v1/inventory/{cid}"
    image = io.BytesIO()
    Image.new("RGB", (2, 2), (15, 25, 35)).save(image, format="PNG")
    data = image.getvalue()
    uploaded = api.post(f"{base}/photos", files={"file": ("synthetic.png", data, "image/png")})
    assert uploaded.status_code == 201, uploaded.text
    photo = uploaded.json()
    response = api.post(f"{base}/reconcile", json={"catalog_item_id": str(item_id), "release_id": str(release_id), "expected_revision": 0})
    assert response.status_code == 200, response.text
    before = api.get(base).json()
    history = api.get(f"{base}/reconciliations").json()
    assert len(history) == 1
    assert search(api, "Copper") == [before]
    assert search(api, "no match") == []
    assert api.get(base).json() == before
    assert api.get(f"{base}/reconciliations").json() == history
    assert api.get(f"{base}/photos").json() == [photo]
    assert api.get(f"{base}/photos/{photo['id']}").content == data
