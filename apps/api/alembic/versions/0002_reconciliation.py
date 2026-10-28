"""Add manual reconciliation snapshots and revision control.

Downgrade discards history and revisions. Export/verify a quiescent database and
media backup before downgrade; restore that backup with this revision to recover.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0002_reconciliation"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("owned_copies", sa.Column("identification_revision", sa.Integer(), nullable=False, server_default="0"))
    op.create_check_constraint("identification_revision_nonnegative", "owned_copies", "identification_revision >= 0")
    op.create_table(
        "reconciliation_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("owned_copy_id", UUID(as_uuid=True), sa.ForeignKey("owned_copies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("before_catalog_item_id", UUID(as_uuid=True), sa.ForeignKey("catalog_items.id", ondelete="RESTRICT")),
        sa.Column("before_release_id", UUID(as_uuid=True)),
        sa.Column("after_catalog_item_id", UUID(as_uuid=True), sa.ForeignKey("catalog_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("after_release_id", UUID(as_uuid=True)),
        sa.Column("before_status", sa.String(30), nullable=False),
        sa.Column("after_status", sa.String(30), nullable=False),
        sa.Column("before_revision", sa.Integer(), nullable=False),
        sa.Column("after_revision", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("owned_copy_id", "after_revision"),
        sa.CheckConstraint("before_revision >= 0 AND after_revision = before_revision + 1", name="reconciliation_revision_step"),
        sa.CheckConstraint("operation = 'manual'", name="reconciliation_manual"),
        sa.CheckConstraint("before_status IN ('unidentified', 'partial', 'identified', 'verified') AND after_status = 'identified'", name="reconciliation_status"),
        sa.CheckConstraint("before_release_id IS NULL OR before_catalog_item_id IS NOT NULL", name="reconciliation_before_catalog"),
        sa.ForeignKeyConstraint(["before_release_id", "before_catalog_item_id"], ["releases.id", "releases.catalog_item_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["after_release_id", "after_catalog_item_id"], ["releases.id", "releases.catalog_item_id"], ondelete="RESTRICT"),
    )


def downgrade():
    op.drop_table("reconciliation_events")
    op.drop_constraint("identification_revision_nonnegative", "owned_copies", type_="check")
    op.drop_column("owned_copies", "identification_revision")
