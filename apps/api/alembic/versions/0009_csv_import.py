"""Retain import batches and original row provenance without changing inventory."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
revision='0009_csv_import'
down_revision='0008_appearance'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('import_batches',
        sa.Column('id',UUID(as_uuid=True),primary_key=True),
        sa.Column('source',sa.String(20),nullable=False),
        sa.Column('sha256',sa.String(64),nullable=False),
        sa.Column('parser_version',sa.Integer(),nullable=False),
        sa.Column('row_count',sa.Integer(),nullable=False),
        sa.Column('copy_count',sa.Integer(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint('source','sha256',name='import_file_once'),
        sa.CheckConstraint("source IN ('clz', 'discogs')",name='import_source'),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'",name='import_sha256'),
        sa.CheckConstraint('row_count BETWEEN 1 AND 5000 AND copy_count BETWEEN 1 AND 10000',name='import_counts'),
        sa.CheckConstraint('parser_version = 1',name='import_parser_version'))
    op.create_table('import_copies',
        sa.Column('owned_copy_id',UUID(as_uuid=True),sa.ForeignKey('owned_copies.id',ondelete='RESTRICT'),primary_key=True),
        sa.Column('batch_id',UUID(as_uuid=True),sa.ForeignKey('import_batches.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('row_number',sa.Integer(),nullable=False),
        sa.Column('copy_number',sa.Integer(),nullable=False),
        sa.Column('source_row',JSONB(),nullable=False),
        sa.UniqueConstraint('batch_id','row_number','copy_number',name='import_row_copy_once'),
        sa.CheckConstraint('row_number BETWEEN 2 AND 5001 AND copy_number BETWEEN 1 AND 10000',name='import_row_numbers'),
        sa.CheckConstraint("jsonb_typeof(source_row) = 'object'",name='import_source_row'))
    op.create_index('ix_import_copies_batch_id','import_copies',['batch_id'])

def downgrade():
    connection=op.get_bind()
    connection.execute(sa.text('LOCK TABLE import_batches, import_copies IN ACCESS EXCLUSIVE MODE'))
    if connection.execute(sa.text('SELECT EXISTS(SELECT 1 FROM import_batches)')).scalar():
        raise RuntimeError('Import provenance exists; retain it or restore a verified pre-import backup')
    op.drop_table('import_copies')
    op.drop_table('import_batches')
