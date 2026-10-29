"""Editable copy labels with retained history and optimistic revisions.

Upgrade preserves every existing row. Downgrade discards these new labels and
edit history only; take a verified backup before any operational downgrade.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '0005_copy_details'
down_revision = '0004_owner_access'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('owned_copies', sa.Column('edition_label', sa.String(500), nullable=True))
    op.add_column('owned_copies', sa.Column('details_revision', sa.Integer(), nullable=False, server_default='0'))
    op.create_check_constraint('details_revision_nonnegative', 'owned_copies', 'details_revision >= 0')
    op.create_table('copy_detail_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('owned_copy_id', UUID(as_uuid=True), sa.ForeignKey('owned_copies.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('before_title', sa.String(500)),
        sa.Column('after_title', sa.String(500)),
        sa.Column('before_edition_label', sa.String(500)),
        sa.Column('after_edition_label', sa.String(500)),
        sa.Column('identification_revision', sa.Integer(), nullable=False),
        sa.Column('before_revision', sa.Integer(), nullable=False),
        sa.Column('after_revision', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('owned_copy_id', 'after_revision'),
        sa.CheckConstraint('before_revision >= 0 AND after_revision = before_revision + 1', name='detail_revision_step'),
        sa.CheckConstraint('identification_revision >= 0', name='detail_identification_revision'),
        sa.CheckConstraint('before_title IS DISTINCT FROM after_title OR before_edition_label IS DISTINCT FROM after_edition_label', name='details_changed'))


def downgrade():
    op.drop_table('copy_detail_events')
    op.drop_constraint('details_revision_nonnegative', 'owned_copies', type_='check')
    op.drop_column('owned_copies', 'details_revision')
    op.drop_column('owned_copies', 'edition_label')
