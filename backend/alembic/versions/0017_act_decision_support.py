"""Immutable ACT grounding snapshots.

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("actions", sa.Column("decision_support", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("actions", "decision_support")
