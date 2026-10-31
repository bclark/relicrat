"""Add Comics observations/preferences/history without rewriting existing copies.

Downgrade refuses populated Comic observations, history or customized preferences.
Use verified recovery and an explicit release plan; never downgrade the live trial.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0007_comics'
down_revision='0006_records_setup'
branch_labels=None
depends_on=None
COMIC_CHECK="jsonb_typeof(comic_details) = 'object' AND comic_details - 'issue_number' - 'publisher' = '{}'::jsonb AND (NOT comic_details ? 'issue_number' OR (jsonb_typeof(comic_details->'issue_number') = 'string' AND char_length(comic_details->>'issue_number') BETWEEN 1 AND 100)) AND (NOT comic_details ? 'publisher' OR (jsonb_typeof(comic_details->'publisher') = 'string' AND char_length(comic_details->>'publisher') BETWEEN 1 AND 250))"
COMIC_FIELDS='jsonb_typeof(comic_fields) = \'array\' AND jsonb_array_length(comic_fields) <= 4 AND comic_fields <@ \'["issue_number","publisher","edition","notes"]\'::jsonb'
OLD_CHANGE='before_title IS DISTINCT FROM after_title OR before_edition_label IS DISTINCT FROM after_edition_label OR before_collection_type IS DISTINCT FROM after_collection_type OR before_record_details IS DISTINCT FROM after_record_details'
NEW_CHANGE=OLD_CHANGE+' OR before_comic_details IS DISTINCT FROM after_comic_details'


def upgrade():
    op.add_column('owned_copies',sa.Column('comic_details',JSONB(),nullable=False,server_default='{}'))
    op.create_check_constraint('comic_details_valid','owned_copies',COMIC_CHECK)
    op.drop_constraint('collection_type_valid','owned_copies',type_='check')
    op.create_check_constraint('collection_type_valid','owned_copies',"collection_type::text IN ('other'::text, 'record'::text, 'comic'::text)")
    for key in ('before_comic_details','after_comic_details'):
        op.add_column('copy_detail_events',sa.Column(key,JSONB()))
    op.drop_constraint('details_changed','copy_detail_events',type_='check')
    op.create_check_constraint('details_changed','copy_detail_events',NEW_CHANGE)
    op.add_column('collection_settings',sa.Column('comics_enabled',sa.Boolean(),nullable=False,server_default='false'))
    op.add_column('collection_settings',sa.Column('comic_fields',JSONB(),nullable=False,server_default='["issue_number","publisher","edition","notes"]'))
    op.create_check_constraint('collection_settings_comic_fields','collection_settings',COMIC_FIELDS)
    op.drop_constraint('collection_settings_default','collection_settings',type_='check')
    op.create_check_constraint('collection_settings_default','collection_settings',"default_type::text IN ('other'::text, 'record'::text, 'comic'::text) AND (default_type <> 'record' OR records_enabled) AND (default_type <> 'comic' OR comics_enabled)")


def downgrade():
    connection=op.get_bind()
    connection.execute(sa.text("LOCK TABLE owned_copies, copy_detail_events, collection_settings IN ACCESS EXCLUSIVE MODE"))
    populated=connection.execute(sa.text("SELECT EXISTS(SELECT 1 FROM owned_copies WHERE collection_type='comic' OR comic_details <> '{}'::jsonb) OR EXISTS(SELECT 1 FROM copy_detail_events WHERE before_collection_type='comic' OR after_collection_type='comic' OR coalesce(before_comic_details,'{}'::jsonb) <> '{}'::jsonb OR coalesce(after_comic_details,'{}'::jsonb) <> '{}'::jsonb) OR EXISTS(SELECT 1 FROM collection_settings WHERE comics_enabled OR default_type='comic' OR comic_fields <> '[\"issue_number\",\"publisher\",\"edition\",\"notes\"]'::jsonb)")).scalar()
    if populated:
        raise RuntimeError('Refusing Comics downgrade: retain data/history/preferences and use a verified recovery plan')
    op.drop_constraint('collection_settings_default','collection_settings',type_='check')
    op.create_check_constraint('collection_settings_default','collection_settings',"default_type::text IN ('other'::text, 'record'::text) AND (default_type <> 'record' OR records_enabled)")
    op.drop_constraint('collection_settings_comic_fields','collection_settings',type_='check')
    op.drop_column('collection_settings','comic_fields');op.drop_column('collection_settings','comics_enabled')
    op.drop_constraint('details_changed','copy_detail_events',type_='check')
    op.create_check_constraint('details_changed','copy_detail_events',OLD_CHANGE)
    op.drop_column('copy_detail_events','before_comic_details');op.drop_column('copy_detail_events','after_comic_details')
    op.drop_constraint('comic_details_valid','owned_copies',type_='check')
    op.drop_column('owned_copies','comic_details')
    op.drop_constraint('collection_type_valid','owned_copies',type_='check')
    op.create_check_constraint('collection_type_valid','owned_copies',"collection_type::text IN ('other'::text, 'record'::text)")
