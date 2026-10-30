"""Personal Records details and durable single-owner form preferences.

Downgrade loses preferences, record fields, and record-only edit events. Never
use it as an automatic live rollback; retain a verified recovery capture first.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0006_records_setup'
down_revision = '0005_copy_details'
branch_labels = None
depends_on = None
OLD_CHANGE = 'before_title IS DISTINCT FROM after_title OR before_edition_label IS DISTINCT FROM after_edition_label'
NEW_CHANGE = OLD_CHANGE + ' OR before_collection_type IS DISTINCT FROM after_collection_type OR before_record_details IS DISTINCT FROM after_record_details'
RECORD_CHECK = "jsonb_typeof(record_details) = 'object' AND record_details - 'artist' - 'format' = '{}'::jsonb AND (NOT record_details ? 'artist' OR (jsonb_typeof(record_details->'artist') = 'string' AND char_length(record_details->>'artist') BETWEEN 1 AND 500)) AND (NOT record_details ? 'format' OR (jsonb_typeof(record_details->'format') = 'string' AND char_length(record_details->>'format') BETWEEN 1 AND 100))"
FIELDS_CHECK = "jsonb_typeof(record_fields) = 'array' AND jsonb_array_length(record_fields) <= 4 AND record_fields <@ '[\"artist\",\"format\",\"edition\",\"notes\"]'::jsonb"


def upgrade():
    op.add_column('owned_copies', sa.Column('collection_type', sa.String(20), nullable=False, server_default='other'))
    op.add_column('owned_copies', sa.Column('record_details', JSONB(), nullable=False, server_default='{}'))
    op.create_check_constraint('collection_type_valid', 'owned_copies', "collection_type::text IN ('other'::text, 'record'::text)")
    op.create_check_constraint('record_details_valid', 'owned_copies', RECORD_CHECK)
    for name, kind in [('before_collection_type', sa.String(20)), ('after_collection_type', sa.String(20)),
                       ('before_record_details', JSONB()), ('after_record_details', JSONB())]:
        op.add_column('copy_detail_events', sa.Column(name, kind))
    op.drop_constraint('details_changed', 'copy_detail_events', type_='check')
    op.create_check_constraint('details_changed', 'copy_detail_events', NEW_CHANGE)
    op.create_table('collection_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='not_started'),
        sa.Column('records_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_type', sa.String(20), nullable=False, server_default='other'),
        sa.Column('record_fields', JSONB(), nullable=False, server_default='["artist","format","edition","notes"]'),
        sa.Column('revision', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('id = 1', name='collection_settings_singleton'),
        sa.CheckConstraint('revision >= 0', name='collection_settings_revision'),
        sa.CheckConstraint("status::text IN ('not_started'::text, 'skipped'::text, 'configured'::text)", name='collection_settings_status'),
        sa.CheckConstraint("default_type::text IN ('other'::text, 'record'::text) AND (default_type <> 'record' OR records_enabled)", name='collection_settings_default'),
        sa.CheckConstraint(FIELDS_CHECK, name='collection_settings_fields'))
    op.execute('INSERT INTO collection_settings (id) VALUES (1)')


def downgrade():
    op.drop_table('collection_settings')
    # New-only events cannot satisfy the earlier, title/edition-only constraint.
    op.execute('DELETE FROM copy_detail_events WHERE NOT (' + OLD_CHANGE + ')')
    op.drop_constraint('details_changed', 'copy_detail_events', type_='check')
    op.create_check_constraint('details_changed', 'copy_detail_events', OLD_CHANGE)
    for name in ('before_collection_type', 'after_collection_type', 'before_record_details', 'after_record_details'):
        op.drop_column('copy_detail_events', name)
    op.drop_constraint('record_details_valid', 'owned_copies', type_='check')
    op.drop_constraint('collection_type_valid', 'owned_copies', type_='check')
    op.drop_column('owned_copies', 'record_details')
    op.drop_column('owned_copies', 'collection_type')
