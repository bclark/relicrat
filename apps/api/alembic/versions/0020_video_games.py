"""Store physical game contents and preserve their edit history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = '0020_video_games'
down_revision = '0019_agent_credential'
branch_labels = None
depends_on = None

OLD_TYPES = "collection_type::text IN ('other'::text, 'record'::text, 'comic'::text, 'movie'::text)"
GAME_TYPES = "collection_type::text IN ('other'::text, 'record'::text, 'comic'::text, 'movie'::text, 'game'::text)"
CONTENTS = "(jsonb_typeof(game_contents) = 'object' AND game_contents - ARRAY['media','packaging','manual','inserts'] = '{}'::jsonb AND (collection_type = 'game' OR game_contents = '{}'::jsonb) AND (collection_type <> 'game' OR COALESCE(btrim(provisional_title), '') <> '') AND (NOT game_contents ? 'media' OR (game_contents->>'media') IN ('present','missing','not_applicable')) AND (NOT game_contents ? 'packaging' OR (game_contents->>'packaging') IN ('present','missing','not_applicable')) AND (NOT game_contents ? 'manual' OR (game_contents->>'manual') IN ('present','missing','not_applicable')) AND (NOT game_contents ? 'inserts' OR (game_contents->>'inserts') IN ('present','missing','not_applicable'))) IS TRUE"
OLD_CHANGE = 'before_title IS DISTINCT FROM after_title OR before_edition_label IS DISTINCT FROM after_edition_label OR before_collection_type IS DISTINCT FROM after_collection_type OR before_record_details IS DISTINCT FROM after_record_details OR before_comic_details IS DISTINCT FROM after_comic_details OR before_barcode IS DISTINCT FROM after_barcode OR before_movie_details IS DISTINCT FROM after_movie_details OR before_custom_details IS DISTINCT FROM after_custom_details'
GAME_CHANGE = 'before_title IS DISTINCT FROM after_title OR before_edition_label IS DISTINCT FROM after_edition_label OR before_collection_type IS DISTINCT FROM after_collection_type OR before_record_details IS DISTINCT FROM after_record_details OR before_comic_details IS DISTINCT FROM after_comic_details OR before_barcode IS DISTINCT FROM after_barcode OR before_movie_details IS DISTINCT FROM after_movie_details OR before_custom_details IS DISTINCT FROM after_custom_details OR before_game_contents IS DISTINCT FROM after_game_contents'


def upgrade():
    op.add_column('owned_copies', sa.Column('game_contents', JSONB(), nullable=False, server_default='{}'))
    op.drop_constraint('collection_type_valid', 'owned_copies', type_='check')
    op.create_check_constraint('collection_type_valid', 'owned_copies', GAME_TYPES)
    op.create_check_constraint('game_contents_valid', 'owned_copies', CONTENTS)
    op.add_column('copy_detail_events', sa.Column('before_game_contents', JSONB()))
    op.add_column('copy_detail_events', sa.Column('after_game_contents', JSONB()))
    op.drop_constraint('details_changed', 'copy_detail_events', type_='check')
    op.create_check_constraint('details_changed', 'copy_detail_events', GAME_CHANGE)


def downgrade():
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE owned_copies, copy_detail_events IN ACCESS EXCLUSIVE MODE'))
    populated = connection.execute(sa.text("""
        SELECT EXISTS (SELECT 1 FROM owned_copies WHERE collection_type = 'game')
            OR EXISTS (SELECT 1 FROM copy_detail_events
                       WHERE before_collection_type = 'game' OR after_collection_type = 'game')
    """)).scalar_one()
    if populated:
        raise RuntimeError('Refusing downgrade with saved game copies or history')
    op.drop_constraint('details_changed', 'copy_detail_events', type_='check')
    op.create_check_constraint('details_changed', 'copy_detail_events', OLD_CHANGE)
    op.drop_column('copy_detail_events', 'after_game_contents')
    op.drop_column('copy_detail_events', 'before_game_contents')
    op.drop_constraint('game_contents_valid', 'owned_copies', type_='check')
    op.drop_column('owned_copies', 'game_contents')
    op.drop_constraint('collection_type_valid', 'owned_copies', type_='check')
    op.create_check_constraint('collection_type_valid', 'owned_copies', OLD_TYPES)
