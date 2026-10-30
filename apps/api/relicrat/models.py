"""Foundational SQLAlchemy models. PostgreSQL is the authoritative database."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, func
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
        CheckConstraint("storage_revision >= 0", name="storage_revision_nonnegative"),
        CheckConstraint("collection_type::text IN ('other'::text, 'record'::text)", name="collection_type_valid"),
        CheckConstraint("jsonb_typeof(record_details) = 'object' AND record_details - 'artist' - 'format' = '{}'::jsonb AND (NOT record_details ? 'artist' OR (jsonb_typeof(record_details->'artist') = 'string' AND char_length(record_details->>'artist') BETWEEN 1 AND 500)) AND (NOT record_details ? 'format' OR (jsonb_typeof(record_details->'format') = 'string' AND char_length(record_details->>'format') BETWEEN 1 AND 100))", name="record_details_valid"),
        CheckConstraint("details_revision >= 0", name="details_revision_nonnegative"),
        CheckConstraint("identification_revision >= 0", name="identification_revision_nonnegative"),
        CheckConstraint("identification_status IN ('unidentified', 'partial', 'identified', 'verified')", name="identification_status_valid"),
        CheckConstraint("ownership_status IN ('owned', 'sold', 'traded', 'lost')", name="ownership_status_valid"),
        ForeignKeyConstraint(["release_id", "catalog_item_id"], ["releases.id", "releases.catalog_item_id"], name="fk_owned_copies_release_same_catalog", ondelete="RESTRICT"),
        Index("ix_owned_copies_catalog_release", "catalog_item_id", "release_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalog_items.id", ondelete="RESTRICT"), index=True)
    release_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    provisional_title: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    # NULL follows a linked release; empty text explicitly leaves the edition unknown.
    collection_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="other")
    record_details: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    edition_label: Mapped[str | None] = mapped_column(String(500))
    details_revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    identification_status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="unidentified")
    identification_revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    storage_revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    ownership_status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="owned")
    storage_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("storage_locations.id", ondelete="RESTRICT"), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CopyDetailEvent(Base):
    """Manual physical-copy labels; catalog identities are never edited here."""
    __tablename__ = 'copy_detail_events'
    __table_args__ = (
        UniqueConstraint('owned_copy_id', 'after_revision'),
        CheckConstraint('before_revision >= 0 AND after_revision = before_revision + 1', name='detail_revision_step'),
        CheckConstraint('identification_revision >= 0', name='detail_identification_revision'),
        CheckConstraint('before_title IS DISTINCT FROM after_title OR before_edition_label IS DISTINCT FROM after_edition_label OR before_collection_type IS DISTINCT FROM after_collection_type OR before_record_details IS DISTINCT FROM after_record_details', name='details_changed'),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owned_copy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('owned_copies.id', ondelete='RESTRICT'), nullable=False)
    before_title: Mapped[str | None] = mapped_column(String(500))
    after_title: Mapped[str | None] = mapped_column(String(500))
    before_edition_label: Mapped[str | None] = mapped_column(String(500))
    after_edition_label: Mapped[str | None] = mapped_column(String(500))
    before_collection_type: Mapped[str | None] = mapped_column(String(20))
    after_collection_type: Mapped[str | None] = mapped_column(String(20))
    before_record_details: Mapped[dict | None] = mapped_column(JSONB)
    after_record_details: Mapped[dict | None] = mapped_column(JSONB)
    identification_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    before_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    after_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


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


class ReconciliationEvent(Base):
    """Manual identification snapshots; no authenticated actor is available."""
    __tablename__ = "reconciliation_events"
    __table_args__ = (
        UniqueConstraint("owned_copy_id", "after_revision"),
        CheckConstraint("before_revision >= 0 AND after_revision = before_revision + 1", name="reconciliation_revision_step"),
        CheckConstraint("operation = 'manual'", name="reconciliation_manual"),
        CheckConstraint("before_status IN ('unidentified', 'partial', 'identified', 'verified') AND after_status = 'identified'", name="reconciliation_status"),
        CheckConstraint("before_release_id IS NULL OR before_catalog_item_id IS NOT NULL", name="reconciliation_before_catalog"),
        ForeignKeyConstraint(["before_release_id", "before_catalog_item_id"], ["releases.id", "releases.catalog_item_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["after_release_id", "after_catalog_item_id"], ["releases.id", "releases.catalog_item_id"], ondelete="RESTRICT"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owned_copy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("owned_copies.id", ondelete="RESTRICT"), nullable=False)
    before_catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalog_items.id", ondelete="RESTRICT"))
    before_release_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    after_catalog_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_items.id", ondelete="RESTRICT"), nullable=False)
    after_release_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    before_status: Mapped[str] = mapped_column(String(30), nullable=False)
    after_status: Mapped[str] = mapped_column(String(30), nullable=False)
    before_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    after_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    operation: Mapped[str] = mapped_column(String(30), nullable=False, server_default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StorageHierarchyGuard(Base):
    """Singleton written by PostgreSQL hierarchy statement triggers."""
    __tablename__ = "storage_hierarchy_guard"
    __table_args__ = (CheckConstraint("id = 1", name="storage_guard_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class CopyLocationEvent(Base):
    __tablename__ = "copy_location_events"
    __table_args__ = (
        UniqueConstraint("owned_copy_id", "after_revision"),
        CheckConstraint("before_revision >= 0 AND after_revision = before_revision + 1", name="location_revision_step"),
        CheckConstraint("operation = 'manual'", name="location_manual"),
        CheckConstraint("before_location_id IS DISTINCT FROM after_location_id", name="location_changed"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owned_copy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("owned_copies.id", ondelete="RESTRICT"), nullable=False)
    before_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("storage_locations.id", ondelete="RESTRICT"))
    after_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("storage_locations.id", ondelete="RESTRICT"))
    before_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    after_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    operation: Mapped[str] = mapped_column(String(30), nullable=False, server_default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class OwnerSession(Base):
    """Revocable, time-bounded owner access; never store raw bearer tokens."""
    __tablename__ = 'owner_sessions'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    credential_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OwnerLoginGuard(Base):
    __tablename__ = 'owner_login_guard'
    __table_args__ = (CheckConstraint('id = 1', name='owner_guard_singleton'),
                      CheckConstraint('failures >= 0 AND failures <= 5', name='owner_guard_failures'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollectionSettings(Timestamps, Base):
    __tablename__ = 'collection_settings'
    __table_args__ = (
        CheckConstraint('id = 1', name='collection_settings_singleton'),
        CheckConstraint('revision >= 0', name='collection_settings_revision'),
        CheckConstraint("status::text IN ('not_started'::text, 'skipped'::text, 'configured'::text)", name='collection_settings_status'),
        CheckConstraint("default_type::text IN ('other'::text, 'record'::text) AND (default_type <> 'record' OR records_enabled)", name='collection_settings_default'),
        CheckConstraint("jsonb_typeof(record_fields) = 'array' AND jsonb_array_length(record_fields) <= 4 AND record_fields <@ '[\"artist\",\"format\",\"edition\",\"notes\"]'::jsonb", name='collection_settings_fields'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default='not_started')
    records_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='false')
    default_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default='other')
    record_fields: Mapped[list] = mapped_column(JSONB, nullable=False, server_default='["artist","format","edition","notes"]')
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
