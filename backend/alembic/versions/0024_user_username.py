"""Add an optional profile display name.

Revision ID: 0024
Revises: 0023
"""

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(48), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "username")
