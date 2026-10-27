"""Foundational SQLAlchemy models. PostgreSQL is the authoritative database."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Category(Timestamps, Base):
    __tablename__ = "categories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class CatalogItem(Timestamps, Base):
    __tablename__ = "catalog_items"
    __table_args__ = (UniqueConstraint("category_id", "identity_key"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    identity_key: Mapped[str] = mapped_column(String(500), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Release(Timestamps, Base):
    __tablename__ = "releases"
    __table_args__ = (UniqueConstraint("catalog_item_id", "release_key"), UniqueConstraint("id", "catalog_item_id"))
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    release_key: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str | None] = mapped_column(String(500))
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class StorageLocation(Timestamps, Base):
    __tablename__ = "storage_locations"
    __table_args__ = (CheckConstraint("parent_id IS NULL OR parent_id <> id", name="no_self_parent"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("storage_locations.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    kind: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)


class OwnedCopy(Timestamps, Base):
    __tablename__ = "owned_copies"
    __table_args__ = (
        CheckConstraint("release_id IS NULL OR catalog_item_id IS NOT NULL", name="release_requires_catalog"),
        CheckConstraint("identification_status IN ('unidentified', 'partial', 'identified', 'verified')", name="identification_status_valid"),
        CheckConstraint("ownership_status IN ('owned', 'sold', 'traded', 'lost')", name="ownership_status_valid"),
        UniqueConstraint("id", "catalog_item_id"),
        Index("ix_owned_copies_catalog_release", "catalog_item_id", "release_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalog_items.id", ondelete="RESTRICT"), index=True)
    release_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    provisional_title: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    identification_status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="unidentified")
    ownership_status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="owned")
    storage_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("storage_locations.id", ondelete="RESTRICT"), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __mapper_args__ = {}


class MediaAsset(Timestamps, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("byte_size >= 0", name="nonnegative_byte_size"),
        UniqueConstraint("storage_key"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owned_copy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("owned_copies.id", ondelete="RESTRICT"), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(50), nullable=False, server_default="photo")
