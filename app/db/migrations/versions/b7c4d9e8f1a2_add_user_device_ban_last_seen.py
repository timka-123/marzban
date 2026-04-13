"""add banned and last_seen to user_devices

Revision ID: b7c4d9e8f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-04-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'b7c4d9e8f1a2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user_devices',
        sa.Column('banned', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'user_devices',
        sa.Column('last_seen', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column('user_devices', 'last_seen')
    op.drop_column('user_devices', 'banned')
