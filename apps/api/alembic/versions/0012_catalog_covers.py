"""Retain optional imported catalog artwork with its source, separate from photos."""
from alembic import op
import sqlalchemy as sa
revision='0012_catalog_covers'
down_revision='0011_copy_barcodes'
branch_labels=None
depends_on=None

def upgrade():
    for name,size in [('source_provider',40),('source_id',128),('source_url',1000)]:
        op.add_column('media_assets',sa.Column(name,sa.String(size),nullable=True))
    op.create_unique_constraint('uq_media_cover_source','media_assets',['owned_copy_id','source_provider','source_id'])
    op.create_check_constraint('cover_source_required','media_assets',"role != 'catalog_cover' OR (source_provider IS NOT NULL AND source_id IS NOT NULL AND source_url IS NOT NULL)")

def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM media_assets WHERE source_provider IS NOT NULL OR source_id IS NOT NULL OR source_url IS NOT NULL OR role='catalog_cover')")).scalar():
        raise RuntimeError('Refusing catalog cover downgrade: preserve imported artwork and source evidence first')
    op.drop_constraint('cover_source_required','media_assets',type_='check')
    op.drop_constraint('uq_media_cover_source','media_assets',type_='unique')
    for name in ['source_url','source_id','source_provider']:op.drop_column('media_assets',name)
