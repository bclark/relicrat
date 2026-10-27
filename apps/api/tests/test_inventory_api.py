"""Integration tests. Requires a migrated disposable PostgreSQL database.

TEST_DATABASE_URL must point to the dedicated test database, not production.
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.main import app

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
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        outer.rollback()
        connection.close()
        engine.dispose()


def test_create_and_retrieve_title_only(client):
    response = client.post("/api/v1/inventory", json={"title": "  Mystery comic  "})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Mystery comic"
    assert body["description"] is None
    assert body["identification_status"] == "unidentified"
    assert client.get(f"/api/v1/inventory/{body['id']}").json()["id"] == body["id"]


def test_description_only(client):
    response = client.post("/api/v1/inventory", json={"description": "  Unknown record  "})
    assert response.status_code == 201, response.text
    assert response.json()["description"] == "Unknown record"


@pytest.mark.parametrize("payload", [{}, {"title": "  "}, {"description": ""}, {"title": None, "description": None}])
def test_reject_empty_copy(client, payload):
    assert client.post("/api/v1/inventory", json=payload).status_code == 422


def test_missing_copy(client):
    assert client.get(f"/api/v1/inventory/{uuid.uuid4()}").status_code == 404


def test_list_newest_first(client):
    a = client.post("/api/v1/inventory", json={"title": "First"}).json()
    b = client.post("/api/v1/inventory", json={"title": "Second"}).json()
    result = client.get("/api/v1/inventory?limit=2").json()
    ids = [item["id"] for item in result]
    assert a["id"] in ids and b["id"] in ids
    assert ids.index(b["id"]) < ids.index(a["id"])


def test_invalid_pagination(client):
    assert client.get("/api/v1/inventory?limit=101").status_code == 422
    assert client.get("/api/v1/inventory?offset=-1").status_code == 422
