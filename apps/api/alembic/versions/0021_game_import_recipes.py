"""Allow batches created by video game import recipes."""
from alembic import op

revision = '0021_game_import_recipes'
down_revision = '0020_video_games'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('import_source', 'import_batches', type_='check')
    op.create_check_constraint('import_source', 'import_batches',
                               "source IN ('clz', 'discogs', 'bluray', 'game_recipe')")


def downgrade():
    # PostgreSQL refuses this constraint if any recipe batches exist.
    op.create_check_constraint('legacy_import_source', 'import_batches',
                               "source IN ('clz', 'discogs', 'bluray')")
    op.drop_constraint('import_source', 'import_batches', type_='check')
    op.execute('ALTER TABLE import_batches RENAME CONSTRAINT legacy_import_source TO import_source')
