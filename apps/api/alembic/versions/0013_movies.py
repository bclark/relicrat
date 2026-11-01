"""Add Movies observations/preferences/history without rewriting existing copies.

Downgrade refuses populated Movie observations, history or customized preferences.
Use verified recovery and an explicit release plan; never downgrade the live trial.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0013_movies'
down_revision='0012_catalog_covers'
branch_labels=None
depends_on=None
MOVIE_CHECK="jsonb_typeof(movie_details) = 'object' AND movie_details - 'media_format' - 'studio' = '{}'::jsonb AND (NOT movie_details ? 'media_format' OR (jsonb_typeof(movie_details->'media_format') = 'string' AND char_length(movie_details->>'media_format') BETWEEN 1 AND 100)) AND (NOT movie_details ? 'studio' OR (jsonb_typeof(movie_details->'studio') = 'string' AND char_length(movie_details->>'studio') BETWEEN 1 AND 250))"
MOVIE_FIELDS='jsonb_typeof(movie_fields) = \'array\' AND jsonb_array_length(movie_fields) <= 4 AND movie_fields <@ \'["media_format","studio","edition","notes"]\'::jsonb'
OLD_CHANGE='before_title IS DISTINCT FROM after_title OR before_edition_label IS DISTINCT FROM after_edition_label OR before_collection_type IS DISTINCT FROM after_collection_type OR before_record_details IS DISTINCT FROM after_record_details OR before_comic_details IS DISTINCT FROM after_comic_details OR before_barcode IS DISTINCT FROM after_barcode'
NEW_CHANGE=OLD_CHANGE+' OR before_movie_details IS DISTINCT FROM after_movie_details'


def upgrade():
    op.drop_constraint('import_source','import_batches',type_='check')
    op.create_check_constraint('import_source','import_batches',"source IN ('clz', 'discogs', 'bluray')")
    op.add_column('owned_copies',sa.Column('movie_details',JSONB(),nullable=False,server_default='{}'))
    op.create_check_constraint('movie_details_valid','owned_copies',MOVIE_CHECK)
    op.drop_constraint('collection_type_valid','owned_copies',type_='check')
    op.create_check_constraint('collection_type_valid','owned_copies',"collection_type::text IN ('other'::text, 'record'::text, 'comic'::text, 'movie'::text)")
    for key in ('before_movie_details','after_movie_details'):
        op.add_column('copy_detail_events',sa.Column(key,JSONB()))
    op.drop_constraint('details_changed','copy_detail_events',type_='check')
    op.create_check_constraint('details_changed','copy_detail_events',NEW_CHANGE)
    op.add_column('collection_settings',sa.Column('movies_enabled',sa.Boolean(),nullable=False,server_default='false'))
    op.add_column('collection_settings',sa.Column('movie_fields',JSONB(),nullable=False,server_default='["media_format","studio","edition","notes"]'))
    op.create_check_constraint('collection_settings_movie_fields','collection_settings',MOVIE_FIELDS)
    op.drop_constraint('collection_settings_default','collection_settings',type_='check')
    op.create_check_constraint('collection_settings_default','collection_settings',"default_type::text IN ('other'::text, 'record'::text, 'comic'::text, 'movie'::text) AND (default_type <> 'record' OR records_enabled) AND (default_type <> 'comic' OR comics_enabled) AND (default_type <> 'movie' OR movies_enabled)")


def downgrade():
    connection=op.get_bind()
    connection.execute(sa.text("LOCK TABLE owned_copies, copy_detail_events, collection_settings, import_batches IN ACCESS EXCLUSIVE MODE"))
    populated=connection.execute(sa.text("SELECT EXISTS(SELECT 1 FROM import_batches WHERE source='bluray') OR EXISTS(SELECT 1 FROM owned_copies WHERE collection_type='movie' OR movie_details <> '{}'::jsonb) OR EXISTS(SELECT 1 FROM copy_detail_events WHERE before_collection_type='movie' OR after_collection_type='movie' OR coalesce(before_movie_details,'{}'::jsonb) <> '{}'::jsonb OR coalesce(after_movie_details,'{}'::jsonb) <> '{}'::jsonb) OR EXISTS(SELECT 1 FROM collection_settings WHERE movies_enabled OR default_type='movie' OR movie_fields <> '[\"media_format\",\"studio\",\"edition\",\"notes\"]'::jsonb)")).scalar()
    if populated:
        raise RuntimeError('Refusing Movies downgrade: retain data/history/preferences and use a verified recovery plan')
    op.drop_constraint('collection_settings_default','collection_settings',type_='check')
    op.create_check_constraint('collection_settings_default','collection_settings',"default_type::text IN ('other'::text, 'record'::text, 'comic'::text) AND (default_type <> 'record' OR records_enabled) AND (default_type <> 'comic' OR comics_enabled)")
    op.drop_constraint('collection_settings_movie_fields','collection_settings',type_='check')
    op.drop_column('collection_settings','movie_fields');op.drop_column('collection_settings','movies_enabled')
    op.drop_constraint('details_changed','copy_detail_events',type_='check')
    op.create_check_constraint('details_changed','copy_detail_events',OLD_CHANGE)
    op.drop_column('copy_detail_events','before_movie_details');op.drop_column('copy_detail_events','after_movie_details')
    op.drop_constraint('movie_details_valid','owned_copies',type_='check')
    op.drop_column('owned_copies','movie_details')
    op.drop_constraint('collection_type_valid','owned_copies',type_='check')
    op.create_check_constraint('collection_type_valid','owned_copies',"collection_type::text IN ('other'::text, 'record'::text, 'comic'::text)")

    op.drop_constraint('import_source','import_batches',type_='check')
    op.create_check_constraint('import_source','import_batches',"source IN ('clz', 'discogs')")
