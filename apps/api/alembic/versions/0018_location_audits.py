"""Retain completed physical storage audits."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = '0018_location_audits'
down_revision = '0017_import_duplicate_decisions'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'location_audits',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('location_id', sa.Uuid(), sa.ForeignKey('storage_locations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('request_digest', sa.String(64), nullable=False),
        sa.Column('result', JSONB(), nullable=False),
    )
    op.create_index('ix_location_audits_location_time', 'location_audits', ['location_id', 'created_at', 'id'])


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text('LOCK TABLE location_audits IN ACCESS EXCLUSIVE MODE'))
    if conn.execute(sa.text('SELECT EXISTS (SELECT 1 FROM location_audits)')).scalar():
        raise RuntimeError('Location audits exist. Restore a verified backup to roll back this migration.')
    op.drop_table('location_audits')
