"""ACT substrate: business_function enum + actions table (VoC OS §45, §58; plan 26)

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-28

Human override (Gate #3) giữ NGUYÊN vị trí agent (human_* columns) làm
evaluation data (§52); priority_score TÍNH LẠI từ effective values bằng công
thức deterministic — LLM không bao giờ tự tính priority (§49).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, JSONB

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE llm_call_type ADD VALUE IF NOT EXISTS 'act_generate'")
    op.execute(
        "CREATE TYPE business_function AS ENUM ("
        "'MARKETING', 'LEGAL', 'DESIGN', 'FINANCE', 'ENGINEERING', "
        "'OPERATION', 'SALES', 'SUPPORT')"
    )

    op.create_table(
        "actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("insight_id", sa.Uuid(), nullable=False),
        sa.Column(
            "function", ENUM(name="business_function", create_type=False), nullable=False
        ),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("impact", sa.Integer(), nullable=False),
        sa.Column("effort", sa.Integer(), nullable=False),
        sa.Column("urgency", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        # Gate #3 override — vị trí agent giữ nguyên làm evaluation data (§52)
        sa.Column("human_impact", sa.Integer(), nullable=True),
        sa.Column("human_effort", sa.Integer(), nullable=True),
        sa.Column("human_urgency", sa.Integer(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="proposed"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["insight_id"], ["insights.id"],
            name=op.f("fk_actions_insight_id_insights"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_actions")),
    )
    op.create_index("ix_actions_insight_id", "actions", ["insight_id"])


def downgrade() -> None:
    op.drop_index("ix_actions_insight_id", table_name="actions")
    op.drop_table("actions")
    op.execute("DROP TYPE IF EXISTS business_function")
