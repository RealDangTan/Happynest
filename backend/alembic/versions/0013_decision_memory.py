"""Decision memory + closed-loop: decision_logs + impact_checks (VoC OS §52–53)

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-28

Plan 27 Task 1–2. decision_logs = unified evaluation data của 3 HITL gate
(schema_mapping | taxonomy | insight | action) — dùng làm precedent retrieval /
evaluation metrics, KHÔNG fine-tune sớm (§53). impact_checks tái tạo (shape cũ
commit 95c59dd làm tham khảo) đo volume feedback trước/sau action accepted —
trigger là CLI script (điền gap "no trigger" của phase 20).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, JSONB

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE decision_subject AS ENUM "
        "('schema_mapping', 'taxonomy', 'insight', 'action')"
    )

    op.create_table(
        "decision_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column(
            "subject_type",
            ENUM(name="decision_subject", create_type=False),
            nullable=False,
        ),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("agent_value", JSONB(), nullable=True),
        sa.Column("human_value", JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_decision_logs_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name=op.f("fk_decision_logs_reviewer_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_decision_logs")),
    )
    op.create_index("ix_decision_logs_product_id", "decision_logs", ["product_id"])
    op.create_index(
        "ix_decision_logs_subject", "decision_logs", ["subject_type", "subject_id"]
    )

    op.create_table(
        "impact_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action_id", sa.Uuid(), nullable=False),
        sa.Column("insight_id", sa.Uuid(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("before_count", sa.Integer(), nullable=False),
        sa.Column("after_count", sa.Integer(), nullable=False),
        sa.Column("delta_ratio", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["action_id"], ["actions.id"],
            name=op.f("fk_impact_checks_action_id_actions"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["insight_id"], ["insights.id"],
            name=op.f("fk_impact_checks_insight_id_insights"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_impact_checks")),
    )
    op.create_index("ix_impact_checks_action_id", "impact_checks", ["action_id"])


def downgrade() -> None:
    op.drop_index("ix_impact_checks_action_id", table_name="impact_checks")
    op.drop_table("impact_checks")
    op.drop_index("ix_decision_logs_subject", table_name="decision_logs")
    op.drop_index("ix_decision_logs_product_id", table_name="decision_logs")
    op.drop_table("decision_logs")
    op.execute("DROP TYPE IF EXISTS decision_subject")
