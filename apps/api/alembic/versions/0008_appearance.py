"""Add owner appearance without changing collection data.

Downgrade refuses a customized theme; export and explicitly restore the default
before a reviewed rollback. This is not a live rollback procedure.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0008_appearance'
down_revision = '0007_comics'
branch_labels = None
depends_on = None

DEFAULT = '{"schema_version": 1, "name": "RelicRat", "mode": "light", "colors": {"page": "#f1f4f8", "paper": "#ffffff", "ink": "#1b2a3d", "muted": "#53647a", "rule": "#cdd6e2", "accent": "#214fbd", "accent_text": "#ffffff", "soft": "#e9effc"}, "font": "sans", "heading_font": "sans", "spacing": "balanced", "corners": "soft", "density": "comfortable"}'
THEME_CHECK = "(jsonb_typeof(theme) = 'object' AND octet_length(theme::text) <= 4096 AND theme - ARRAY['schema_version','name','mode','colors','font','heading_font','spacing','corners','density']::text[] = '{}'::jsonb AND theme->'schema_version' = '1'::jsonb AND jsonb_typeof(theme->'name') = 'string' AND char_length(btrim(theme->>'name')) BETWEEN 1 AND 60 AND (theme->>'name') !~ '[[:cntrl:]]' AND theme->>'mode' IN ('light','dark') AND theme->>'font' IN ('sans','serif','mono') AND theme->>'heading_font' IN ('sans','serif','mono') AND theme->>'spacing' IN ('close','balanced','airy') AND theme->>'corners' IN ('square','soft','round') AND theme->>'density' IN ('compact','comfortable') AND jsonb_typeof(theme->'colors') = 'object' AND (theme->'colors') - ARRAY['page','paper','ink','muted','rule','accent','accent_text','soft']::text[] = '{}'::jsonb AND jsonb_typeof(theme->'colors'->'page') = 'string' AND (theme->'colors'->>'page') ~ '^#[0-9a-fA-F]{6}$' AND jsonb_typeof(theme->'colors'->'paper') = 'string' AND (theme->'colors'->>'paper') ~ '^#[0-9a-fA-F]{6}$' AND jsonb_typeof(theme->'colors'->'ink') = 'string' AND (theme->'colors'->>'ink') ~ '^#[0-9a-fA-F]{6}$' AND jsonb_typeof(theme->'colors'->'muted') = 'string' AND (theme->'colors'->>'muted') ~ '^#[0-9a-fA-F]{6}$' AND jsonb_typeof(theme->'colors'->'rule') = 'string' AND (theme->'colors'->>'rule') ~ '^#[0-9a-fA-F]{6}$' AND jsonb_typeof(theme->'colors'->'accent') = 'string' AND (theme->'colors'->>'accent') ~ '^#[0-9a-fA-F]{6}$' AND jsonb_typeof(theme->'colors'->'accent_text') = 'string' AND (theme->'colors'->>'accent_text') ~ '^#[0-9a-fA-F]{6}$' AND jsonb_typeof(theme->'colors'->'soft') = 'string' AND (theme->'colors'->>'soft') ~ '^#[0-9a-fA-F]{6}$') IS TRUE"


def upgrade():
    op.create_table('appearance_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('theme', JSONB(), nullable=False, server_default=DEFAULT),
        sa.Column('revision', sa.Integer(), nullable=False, server_default='0'),
        sa.CheckConstraint('id = 1', name='appearance_singleton'),
        sa.CheckConstraint('revision >= 0', name='appearance_revision'),
        sa.CheckConstraint(THEME_CHECK, name='appearance_theme'))
    op.execute('INSERT INTO appearance_settings (id) VALUES (1)')


def downgrade():
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE appearance_settings IN ACCESS EXCLUSIVE MODE'))
    customized = connection.execute(sa.text('SELECT EXISTS(SELECT 1 FROM appearance_settings WHERE theme <> CAST(:theme AS jsonb))'), {'theme': DEFAULT}).scalar()
    if customized:
        raise RuntimeError('Export the customized theme and explicitly restore the default before downgrading')
    op.drop_table('appearance_settings')
