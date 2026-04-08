"""add hwid device limit

Revision ID: a1b2c3d4e5f6
Revises: b25e7e6be241
Create Date: 2026-04-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'b25e7e6be241'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('hwid_device_limit', sa.Integer(), nullable=True))

    op.create_table(
        'user_devices',
        sa.Column('hwid', sa.String(128), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform', sa.String(64), nullable=True),
        sa.Column('os_version', sa.String(64), nullable=True),
        sa.Column('device_model', sa.String(128), nullable=True),
        sa.Column('user_agent', sa.String(256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('hwid', 'user_id'),
    )


def downgrade():
    op.drop_table('user_devices')
    op.drop_column('users', 'hwid_device_limit')
