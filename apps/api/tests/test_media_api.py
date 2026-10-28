"""PostgreSQL-backed photo upload tests; never point at a production database."""
import io
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from auth_helpers import sign_in
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.main import app
from relicrat.models import MediaAsset

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not configured")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    engine = create_engine(URL)
    connection = engine.connect()
    outer = connection.begin()

    def override_db():
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as test_client:
            sign_in(test_client)
            yield test_client, connection, tmp_path / "media"
    finally:
        app.dependency_overrides.pop(get_db, None)
        outer.rollback()
        connection.close()
        engine.dispose()


def png_bytes():
    output = io.BytesIO()
    Image.new("RGB", (4, 4), (255, 0, 0)).save(output, format="PNG")
    return output.getvalue()


def create_copy(client):
    response = client.post("/api/v1/inventory", json={"title": "Unknown comic"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_upload_list_and_download(client):
    api, connection, root = client
    copy_id = create_copy(api)
    data = png_bytes()
    response = api.post(f"/api/v1/inventory/{copy_id}/photos", files={"file": ("photo.png", data, "image/png")})
    assert response.status_code == 201, response.text
    photo = response.json()
    assert photo["content_type"] == "image/png"
    assert photo["byte_size"] == len(data)
    assert photo["owned_copy_id"] == copy_id
    assert len(list(root.rglob("*.png"))) == 1
    assert api.get(f"/api/v1/inventory/{copy_id}/photos").json()[0]["id"] == photo["id"]
    downloaded = api.get(f"/api/v1/inventory/{copy_id}/photos/{photo['id']}")
    assert downloaded.status_code == 200
    assert downloaded.content == data
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        assert session.get(MediaAsset, uuid.UUID(photo["id"])) is not None


def test_reject_invalid_image_and_no_file(client):
    api, _, root = client
    copy_id = create_copy(api)
    response = api.post(f"/api/v1/inventory/{copy_id}/photos", files={"file": ("fake.png", b"not a photo", "image/png")})
    assert response.status_code == 422
    assert not root.exists() or not list(root.rglob("*.*"))


def test_reject_oversized_upload(client):
    api, _, root = client
    copy_id = create_copy(api)
    response = api.post(f"/api/v1/inventory/{copy_id}/photos", files={"file": ("huge.png", b"x" * (15 * 1024 * 1024 + 1), "image/png")})
    assert response.status_code == 413
    assert not root.exists()


def test_photo_is_scoped_to_copy(client):
    api, _, _ = client
    first = create_copy(api)
    second = create_copy(api)
    response = api.post(f"/api/v1/inventory/{first}/photos", files={"file": ("photo.png", png_bytes(), "image/png")})
    assert response.status_code == 201, response.text
    photo_id = response.json()["id"]
    assert api.get(f"/api/v1/inventory/{second}/photos/{photo_id}").status_code == 404
    assert api.get(f"/api/v1/inventory/{uuid.uuid4()}/photos").status_code == 404


def test_photo_missing_on_disk_returns_404(client):
    api, _, root = client
    copy_id = create_copy(api)
    response = api.post(f"/api/v1/inventory/{copy_id}/photos", files={"file": ("photo.png", png_bytes(), "image/png")})
    assert response.status_code == 201, response.text
    photo_id = response.json()["id"]
    for path in root.rglob("*.png"):
        path.unlink()
    assert api.get(f"/api/v1/inventory/{copy_id}/photos/{photo_id}").status_code == 404


def test_failed_photo_commit_removes_file(client, monkeypatch):
    api, connection, root = client
    copy_id = create_copy(api)
    original_commit = Session.commit

    def fail_photo_commit(session):
        if any(isinstance(obj, MediaAsset) for obj in session.new):
            raise RuntimeError("Injected photo commit failure")
        return original_commit(session)

    monkeypatch.setattr(Session, "commit", fail_photo_commit)
    with pytest.raises(RuntimeError, match="Injected photo commit failure"):
        api.post(f"/api/v1/inventory/{copy_id}/photos",
                 files={"file": ("photo.png", png_bytes(), "image/png")})
    assert not list(root.rglob("*.png"))
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        assert session.scalar(select(MediaAsset).where(
            MediaAsset.owned_copy_id == uuid.UUID(copy_id))) is None


def test_refresh_failure_preserves_committed_photo(tmp_path, monkeypatch):
    # Use real commits and independent sessions: savepoint fixtures cannot prove
    # that data survives a committed transaction followed by a read failure.
    from relicrat.models import OwnedCopy

    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    engine = create_engine(URL)
    with Session(engine) as session:
        copy = OwnedCopy(provisional_title="Disposable refresh-failure test")
        session.add(copy)
        session.commit()
        copy_id = copy.id

    def override_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    original_refresh = Session.refresh

    def fail_photo_refresh(session, instance, *args, **kwargs):
        if isinstance(instance, MediaAsset):
            raise RuntimeError("Injected post-commit refresh failure")
        return original_refresh(session, instance, *args, **kwargs)

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(Session, "refresh", fail_photo_refresh)
    try:
        data = png_bytes()
        with TestClient(app, raise_server_exceptions=False) as api:
            sign_in(api)
            response = api.post(f"/api/v1/inventory/{copy_id}/photos",
                                files={"file": ("photo.png", data, "image/png")})
            assert response.status_code == 500
            with Session(engine) as session:
                asset = session.scalar(select(MediaAsset).where(MediaAsset.owned_copy_id == copy_id))
                assert asset is not None, "A successful commit must remain visible to a new session"
                path = tmp_path / asset.storage_key
                assert path.is_file(), "Post-commit read failure must not delete the committed photo"
                assert path.read_bytes() == data
    finally:
        app.dependency_overrides.pop(get_db, None)
        with Session(engine) as session:
            # Only delete the records this test committed to its disposable DB.
            for asset in session.scalars(select(MediaAsset).where(MediaAsset.owned_copy_id == copy_id)):
                session.delete(asset)
            session.flush()
            session.delete(session.get(OwnedCopy, copy_id))
            session.commit()
        engine.dispose()
