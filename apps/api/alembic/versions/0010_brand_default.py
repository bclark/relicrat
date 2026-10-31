"""Adopt the approved factory theme without replacing saved owner choices.

Only pristine legacy defaults (revision zero and exact old values) change on
upgrade. Downgrade maps the exact new factory palette back to the old default;
other themes survive. Both transitions increment revisions to reject stale saves.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0010_brand_default'
down_revision = '0009_csv_import'
branch_labels = None
depends_on = None

OLD_DEFAULT = '{"schema_version": 1, "name": "RelicRat", "mode": "light", "colors": {"page": "#f1f4f8", "paper": "#ffffff", "ink": "#1b2a3d", "muted": "#53647a", "rule": "#cdd6e2", "accent": "#214fbd", "accent_text": "#ffffff", "soft": "#e9effc"}, "font": "sans", "heading_font": "sans", "spacing": "balanced", "corners": "soft", "density": "comfortable"}'
NEW_DEFAULT = '{"schema_version": 1, "name": "RelicRat", "mode": "light", "colors": {"page": "#F7F3E9", "paper": "#FFFFFF", "ink": "#302B28", "muted": "#595650", "rule": "#C6C9C3", "accent": "#823B3D", "accent_text": "#FFFFFF", "soft": "#E8EEE9"}, "font": "sans", "heading_font": "sans", "spacing": "balanced", "corners": "soft", "density": "comfortable"}'


def upgrade():
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE appearance_settings IN ACCESS EXCLUSIVE MODE'))
    op.alter_column('appearance_settings', 'theme', existing_type=JSONB(), server_default=NEW_DEFAULT)
    connection.execute(sa.text("UPDATE appearance_settings SET theme=CAST(:new AS jsonb), revision=revision+1 WHERE revision=0 AND theme=CAST(:old AS jsonb)"), {'old': OLD_DEFAULT, 'new': NEW_DEFAULT})


def downgrade():
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE appearance_settings IN ACCESS EXCLUSIVE MODE'))
    op.alter_column('appearance_settings', 'theme', existing_type=JSONB(), server_default=OLD_DEFAULT)
    connection.execute(sa.text("UPDATE appearance_settings SET theme=CAST(:old AS jsonb), revision=revision+1 WHERE theme=CAST(:new AS jsonb)"), {'old': OLD_DEFAULT, 'new': NEW_DEFAULT})
