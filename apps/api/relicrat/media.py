"""Photo storage for collectible copies.

Files live under MEDIA_ROOT; storage keys are generated UUIDs, never user paths.
"""
from contextlib import contextmanager
import hashlib
import io
import os
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from relicrat.database import get_db
from relicrat.models import MediaAsset, OwnedCopy

router = APIRouter(prefix="/api/v1/inventory", tags=["media"])
MAX_PHOTO_BYTES = 15 * 1024 * 1024
IMAGE_FORMATS = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png"), "WEBP": ("image/webp", ".webp")}


def media_root() -> Path:
    root = os.getenv("MEDIA_ROOT")
    if not root:
        raise RuntimeError("MEDIA_ROOT is required for photo operations")
    return Path(root).resolve()


class PhotoInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owned_copy_id: UUID
    content_type: str
    byte_size: int
    sha256: str | None
    role: str
    source_provider: str | None
    source_id: str | None
    source_url: str | None


def existing_copy(db: Session, copy_id: UUID) -> OwnedCopy:
    copy = db.get(OwnedCopy, copy_id)
    if copy is None or copy.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Collectible not found")
    return copy


@router.post("/{copy_id}/photos", response_model=PhotoInfo, status_code=201)
def upload_photo(copy_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db)) -> MediaAsset:
    existing_copy(db, copy_id)
    data = file.file.read(MAX_PHOTO_BYTES + 1)
    with staged_image(db, copy_id, data) as asset:
        db.commit()
    db.refresh(asset)
    return asset


@contextmanager
def staged_image(db, copy_id, data, *, source_provider=None, source_id=None, source_url=None):
    """Join the caller's transaction; preserve files if commit outcome is unknown."""
    if not data or len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Photo must be between 1 byte and 15 MiB")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            image_format = image.format
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise HTTPException(status_code=422, detail="Invalid image") from None
    if image_format not in IMAGE_FORMATS:
        raise HTTPException(status_code=415, detail="Supported formats: JPEG, PNG, WebP")
    content_type, extension = IMAGE_FORMATS[image_format]

    asset_id = uuid.uuid4()
    key = f"{asset_id.hex[:2]}/{asset_id.hex}{extension}"
    destination = media_root() / key
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as output:
            output.write(data)
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Photo storage collision") from None
    asset = MediaAsset(id=asset_id, owned_copy_id=copy_id, storage_key=key,
        content_type=content_type, byte_size=len(data), sha256=hashlib.sha256(data).hexdigest(),
        role='catalog_cover' if source_provider else 'photo', source_provider=source_provider,
        source_id=source_id, source_url=source_url)
    try:
        db.add(asset)
        yield asset
    except Exception:
        # Pending means this asset has never been flushed to PostgreSQL. Once
        # flushed, a lost commit acknowledgement can race a confirming read;
        # retain the file rather than risk removing committed media.
        never_flushed = inspect(asset).pending
        db.rollback()
        if never_flushed:
            destination.unlink(missing_ok=True)
        raise


@router.get("/{copy_id}/photos", response_model=list[PhotoInfo])
def list_photos(copy_id: UUID, db: Session = Depends(get_db)) -> list[MediaAsset]:
    existing_copy(db, copy_id)
    from sqlalchemy import select
    return list(db.scalars(
        select(MediaAsset).where(MediaAsset.owned_copy_id == copy_id)
        .order_by(MediaAsset.created_at.desc(), MediaAsset.id.desc())
    ).all())


@router.get("/{copy_id}/photos/{photo_id}")
def download_photo(copy_id: UUID, photo_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    existing_copy(db, copy_id)
    asset = db.get(MediaAsset, photo_id)
    if asset is None or asset.owned_copy_id != copy_id:
        raise HTTPException(status_code=404, detail="Photo not found")
    root = media_root()
    path = (root / asset.storage_key).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(status_code=404, detail="Photo file not found")
    return FileResponse(path, media_type=asset.content_type)
