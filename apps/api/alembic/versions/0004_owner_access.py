"""Revocable owner sessions and a serialized failed-login throttle.

Downgrade discards sessions/throttle state, retaining all collection data.
Rotate the session secret before promoting any restored database.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '0004_owner_access'
down_revision = '0003_storage'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('owner_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('credential_fingerprint', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)))
    op.create_index('ix_owner_sessions_expires_at', 'owner_sessions', ['expires_at'])
    op.create_table('owner_login_guard',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('window_started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('blocked_until', sa.DateTime(timezone=True)),
        sa.CheckConstraint('id = 1', name='owner_guard_singleton'),
        sa.CheckConstraint('failures >= 0 AND failures <= 5', name='owner_guard_failures'))
    op.execute('INSERT INTO owner_login_guard (id) VALUES (1)')


def downgrade():
    op.drop_table('owner_login_guard')
    op.drop_index('ix_owner_sessions_expires_at', table_name='owner_sessions')
    op.drop_table('owner_sessions')
