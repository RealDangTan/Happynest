"""agent substrate: insights.embedding + action_drafts/insight_reviews/impact_checks

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-26

Plan 17 Task 1. Lệch có chủ đích so với chữ plan: thêm `insights.created_at`
(server_default now) vì plan 20 tính time_to_insight từ cột này nhưng bảng
gốc 0003 không có — thêm tại đây rẻ hơn migration riêng về sau.

ALTER TYPE llm_call_type ADD VALUE: PG17 cho phép trong transaction miễn
KHÔNG dùng giá trị mới trong cùng transaction — migration này chỉ ADD.
Downgrade KHÔNG gỡ 2 value 'route'/'critic' (ADD VALUE không đảo được; gỡ
đòi hỏi rebuild type và sẽ fail nếu data đã dùng) — chỉ ghi nhận additive.
Bảng checkpoint LangGraph vẫn ngoài Alembic nhờ filter env.py giữ nguyên.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ENUM, JSONB

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE draft_kind_enum AS ENUM ('draft_ticket', 'slack_message', 'report')"
    )
    op.execute("CREATE TYPE draft_status_enum AS ENUM ('draft', 'exported')")

    # --- insights: embedding precedent retrieval + created_at cho KPI P20 ---
    op.add_column("insights", sa.Column("embedding", Vector(1536), nullable=True))
    op.add_column(
        "insights", sa.Column("embedding_model", sa.String(length=100), nullable=True)
    )
    op.add_column("insights", sa.Column("embedding_dim", sa.Integer(), nullable=True))
    op.add_column(
        "insights",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "action_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("insight_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind", ENUM(name="draft_kind_enum", create_type=False), nullable=False
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            ENUM(name="draft_status_enum", create_type=False),
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["insight_id"],
            ["insights.id"],
            name=op.f("fk_action_drafts_insight_id_insights"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_action_drafts")),
    )

    op.create_table(
        "insight_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("insight_id", sa.Uuid(), nullable=False),
        sa.Column("original_value", JSONB(), nullable=False),
        sa.Column("edited_value", JSONB(), nullable=True),
        # review_action tái dùng type tạo ở 0003 — không enum mới
        sa.Column(
            "action", ENUM(name="review_action", create_type=False), nullable=False
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["insight_id"],
            ["insights.id"],
            name=op.f("fk_insight_reviews_insight_id_insights"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name=op.f("fk_insight_reviews_reviewer_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insight_reviews")),
    )

    op.create_table(
        "impact_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("insight_id", sa.Uuid(), nullable=True),
        # snapshot cụm — KHÔNG FK (clusters bị DELETE-all mỗi lần rerun)
        sa.Column("cluster_id", sa.Uuid(), nullable=True),
        sa.Column("cluster_name", sa.String(length=255), nullable=False),
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
            ["insight_id"],
            ["insights.id"],
            name=op.f("fk_impact_checks_insight_id_insights"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_impact_checks")),
    )
    op.create_index(
        "ix_impact_checks_insight_id", "impact_checks", ["insight_id"]
    )

    op.execute(
        "ALTER TYPE llm_call_type ADD VALUE IF NOT EXISTS 'route'"
    )
    op.execute(
        "ALTER TYPE llm_call_type ADD VALUE IF NOT EXISTS 'critic'"
    )


def downgrade() -> None:
    op.drop_index("ix_impact_checks_insight_id", table_name="impact_checks")
    op.drop_table("impact_checks")
    op.drop_table("insight_reviews")
    op.drop_table("action_drafts")
    op.drop_column("insights", "created_at")
    op.drop_column("insights", "embedding_dim")
    op.drop_column("insights", "embedding_model")
    op.drop_column("insights", "embedding")
    op.execute("DROP TYPE IF EXISTS draft_status_enum")
    op.execute("DROP TYPE IF EXISTS draft_kind_enum")
