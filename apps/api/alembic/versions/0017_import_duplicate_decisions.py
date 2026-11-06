"""Persist reviewed import duplicate decisions and reversible archives."""
import sqlalchemy as sa
from alembic import op

revision = '0017_import_duplicate_decisions'
down_revision = '0016_checklist_progress'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'import_duplicate_decisions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('batch_id', sa.Uuid(), sa.ForeignKey('import_batches.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('left_id', sa.Uuid(), sa.ForeignKey('import_copies.owned_copy_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('right_id', sa.Uuid(), sa.ForeignKey('import_copies.owned_copy_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('archived_id', sa.Uuid()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('undone_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint('left_id < right_id', name='import_duplicate_ordered_pair'),
        sa.CheckConstraint('archived_id IN (left_id, right_id)', name='import_duplicate_archive_member'),
    )
    op.create_index('ix_import_duplicate_decisions_batch_id', 'import_duplicate_decisions', ['batch_id'])
    op.create_index('import_duplicate_active_pair', 'import_duplicate_decisions', ['left_id', 'right_id'],
                    unique=True, postgresql_where=sa.text('undone_at IS NULL'))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text('LOCK TABLE import_duplicate_decisions IN ACCESS EXCLUSIVE MODE'))
    if conn.execute(sa.text('SELECT EXISTS (SELECT 1 FROM import_duplicate_decisions)')).scalar():
        raise RuntimeError('Duplicate decisions exist. Restore a verified backup to roll back this migration.')
    op.drop_table('import_duplicate_decisions')
