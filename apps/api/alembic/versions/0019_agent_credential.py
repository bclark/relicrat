"""Store the owner-managed read-only agent credential."""
import sqlalchemy as sa
from alembic import op

revision = '0019_agent_credential'
down_revision = '0018_location_audits'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'agent_credentials',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('credential_fingerprint', sa.String(64), nullable=False),
        sa.CheckConstraint('id = 1', name='agent_credential_singleton'),
    )


def downgrade():
    op.drop_table('agent_credentials')
