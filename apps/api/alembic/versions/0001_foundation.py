"""Create six foundational inventory tables.

Revision ID: 0001_foundation
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def id_column():
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))


def upgrade() -> None:
    op.create_table("categories", id_column(), sa.Column("slug", sa.String(120), nullable=False, unique=True), sa.Column("name", sa.String(200), nullable=False), *timestamps())
    op.create_table(
        "catalog_items", id_column(),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("canonical_name", sa.String(500), nullable=False),
        sa.Column("identity_key", sa.String(500), nullable=False),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(), sa.UniqueConstraint("category_id", "identity_key"),
    )
    op.create_index("ix_catalog_items_category_id", "catalog_items", ["category_id"])
    op.create_table(
        "releases", id_column(),
        sa.Column("catalog_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("catalog_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("release_key", sa.String(500), nullable=False),
        sa.Column("name", sa.String(500)),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(),
        sa.UniqueConstraint("catalog_item_id", "release_key"),
        sa.UniqueConstraint("id", "catalog_item_id"),
    )
    op.create_index("ix_releases_catalog_item_id", "releases", ["catalog_item_id"])
    op.create_table(
        "storage_locations", id_column(),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storage_locations.id", ondelete="RESTRICT")),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("kind", sa.String(100)),
        sa.Column("description", sa.Text()),
        *timestamps(),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="no_self_parent"),
    )
    op.create_index("ix_storage_locations_parent_id", "storage_locations", ["parent_id"])
    op.create_table(
        "owned_copies", id_column(),
        sa.Column("catalog_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("catalog_items.id", ondelete="RESTRICT")),
        sa.Column("release_id", postgresql.UUID(as_uuid=True)),
        sa.Column("provisional_title", sa.String(500)),
        sa.Column("description", sa.Text()),
        sa.Column("identification_status", sa.String(30), nullable=False, server_default="unidentified"),
        sa.Column("ownership_status", sa.String(30), nullable=False, server_default="owned"),
        sa.Column("storage_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storage_locations.id", ondelete="RESTRICT")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["release_id", "catalog_item_id"], ["releases.id", "releases.catalog_item_id"], name="fk_owned_copies_release_same_catalog", ondelete="RESTRICT"),
        sa.CheckConstraint("release_id IS NULL OR catalog_item_id IS NOT NULL", name="release_requires_catalog"),
        sa.CheckConstraint("identification_status IN ('unidentified', 'partial', 'identified', 'verified')", name="identification_status_valid"),
        sa.CheckConstraint("ownership_status IN ('owned', 'sold', 'traded', 'lost')", name="ownership_status_valid"),
        sa.UniqueConstraint("id", "catalog_item_id"),
    )
    op.create_index("ix_owned_copies_catalog_item_id", "owned_copies", ["catalog_item_id"])
    op.create_index("ix_owned_copies_storage_location_id", "owned_copies", ["storage_location_id"])
    op.create_index("ix_owned_copies_catalog_release", "owned_copies", ["catalog_item_id", "release_id"])
    op.create_table(
        "media_assets", id_column(),
        sa.Column("owned_copy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("owned_copies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64)),
        sa.Column("role", sa.String(50), nullable=False, server_default="photo"),
        *timestamps(),
        sa.CheckConstraint("byte_size >= 0", name="nonnegative_byte_size"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_media_assets_owned_copy_id", "media_assets", ["owned_copy_id"])
    # A provisional copy needs a title/description or at least one image.
    # This deferred constraint trigger also allows a copy and its image to be inserted
    # in the same transaction, regardless of statement order.
    op.execute("""
        CREATE FUNCTION validate_provisional_copy() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE copy_id uuid; valid boolean;
        BEGIN
            copy_id := CASE WHEN TG_TABLE_NAME = 'media_assets' THEN
                CASE WHEN TG_OP = 'DELETE' THEN OLD.owned_copy_id ELSE NEW.owned_copy_id END
                ELSE CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END END;
            SELECT (NULLIF(btrim(coalesce(c.provisional_title, '')), '') IS NOT NULL
                    OR NULLIF(btrim(coalesce(c.description, '')), '') IS NOT NULL
                    OR c.catalog_item_id IS NOT NULL
                    OR EXISTS (SELECT 1 FROM media_assets m WHERE m.owned_copy_id = c.id))
              INTO valid FROM owned_copies c WHERE c.id = copy_id;
            IF valid IS FALSE THEN
                RAISE EXCEPTION 'owned copy % requires a description, title, catalog match, or media asset', copy_id;
            END IF;
            RETURN NULL;
        END $$;
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER owned_copy_content_guard
        AFTER INSERT OR UPDATE ON owned_copies
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
        EXECUTE FUNCTION validate_provisional_copy();
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER media_asset_content_guard
        AFTER DELETE OR UPDATE ON media_assets
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
        EXECUTE FUNCTION validate_provisional_copy();
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION validate_provisional_copy() CASCADE")
    op.drop_table("media_assets")
    op.drop_table("owned_copies")
    op.drop_table("storage_locations")
    op.drop_table("releases")
    op.drop_table("catalog_items")
    op.drop_table("categories")
