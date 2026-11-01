"""Optional physical-copy barcode observations; retain corrections in history.

Downgrade refuses to discard any current or historical barcode observation.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0011_copy_barcodes'
down_revision = '0010_brand_default'
branch_labels = None
depends_on = None

BARCODE_CHECK = "jsonb_typeof(barcode) = 'object' AND (barcode = '{}'::jsonb OR (\n    barcode - 'value' - 'format' - 'supplement' = '{}'::jsonb\n    AND barcode ?& ARRAY['value','format']\n    AND jsonb_typeof(barcode->'value') = 'string'\n    AND jsonb_typeof(barcode->'format') = 'string'\n    AND barcode->>'value' ~ '^[0-9]+$'\n    AND CASE barcode->>'format'\n        WHEN 'UPC_A' THEN char_length(barcode->>'value') = 12\n        WHEN 'UPC_E' THEN char_length(barcode->>'value') = 8\n        WHEN 'EAN_8' THEN char_length(barcode->>'value') = 8\n        WHEN 'EAN_13' THEN char_length(barcode->>'value') = 13\n        ELSE false END\n    AND (NOT barcode ? 'supplement' OR (\n        jsonb_typeof(barcode->'supplement') = 'string'\n        AND barcode->>'supplement' ~ '^([0-9]{2}|[0-9]{5})$'))))"
OLD_CHANGED = 'before_title IS DISTINCT FROM after_title OR before_edition_label IS DISTINCT FROM after_edition_label OR before_collection_type IS DISTINCT FROM after_collection_type OR before_record_details IS DISTINCT FROM after_record_details OR before_comic_details IS DISTINCT FROM after_comic_details'
NEW_CHANGED = 'before_title IS DISTINCT FROM after_title OR before_edition_label IS DISTINCT FROM after_edition_label OR before_collection_type IS DISTINCT FROM after_collection_type OR before_record_details IS DISTINCT FROM after_record_details OR before_comic_details IS DISTINCT FROM after_comic_details OR before_barcode IS DISTINCT FROM after_barcode'


def upgrade():
    op.add_column('owned_copies', sa.Column('barcode', JSONB, nullable=False, server_default='{}'))
    op.create_check_constraint('barcode_valid', 'owned_copies', BARCODE_CHECK)
    op.add_column('copy_detail_events', sa.Column('before_barcode', JSONB, nullable=True))
    op.add_column('copy_detail_events', sa.Column('after_barcode', JSONB, nullable=True))
    op.drop_constraint('details_changed', 'copy_detail_events', type_='check')
    op.create_check_constraint('details_changed', 'copy_detail_events', NEW_CHANGED)


def downgrade():
    # Hold the writer boundary through both the loss check and schema change.
    op.get_bind().execute(sa.text('LOCK TABLE owned_copies, copy_detail_events IN ACCESS EXCLUSIVE MODE'))
    if op.get_bind().scalar(sa.text("""SELECT
        EXISTS (SELECT 1 FROM owned_copies WHERE barcode <> '{}'::jsonb) OR
        EXISTS (SELECT 1 FROM copy_detail_events WHERE
            before_barcode IS NOT NULL AND before_barcode <> '{}'::jsonb OR
            after_barcode IS NOT NULL AND after_barcode <> '{}'::jsonb OR
            NOT (""" + OLD_CHANGED + """))""")):
        raise RuntimeError('Refusing barcode downgrade: current observations or retained barcode edit history would be lost')
    op.drop_constraint('details_changed', 'copy_detail_events', type_='check')
    op.create_check_constraint('details_changed', 'copy_detail_events', OLD_CHANGED)
    op.drop_column('copy_detail_events', 'after_barcode')
    op.drop_column('copy_detail_events', 'before_barcode')
    op.drop_constraint('barcode_valid', 'owned_copies', type_='check')
    op.drop_column('owned_copies', 'barcode')
