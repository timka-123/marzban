"""create settings table

Revision ID: f1a2b3c4d5e6
Revises: 5e176f8cb9bd
Create Date: 2026-05-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '5e176f8cb9bd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'settings',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('settings')
