"""UNDERSTAND substrate: evidence store + insights (new model) + insight_reviews

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-28

Plan 25 Task 1 — VoC OS §38 (evidence), §42/§57 (insight model finding vs
hypothesis), §43 (Gate #2). llm_call_type ADD 'plan'/'evaluate'/'synthesize'
(precedent 0007: ADD VALUE không đảo được trong downgrade).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ENUM, JSONB

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for value in ("plan", "evaluate", "synthesize"):
        op.execute(f"ALTER TYPE llm_call_type ADD VALUE IF NOT EXISTS '{value}'")

    op.execute(
        "CREATE TYPE insight_review_action AS ENUM "
        "('approve', 'edit', 'investigate_more', 'reject')"
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("coverage", sa.Float(), nullable=True),
        sa.Column("source_tool", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["analysis_runs.id"], name=op.f("fk_evidence_run_id_analysis_runs")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_evidence_product_id_products")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence")),
    )
    op.create_index("ix_evidence_run_id", "evidence", ["run_id"])
    op.create_index("ix_evidence_product_id", "evidence", ["product_id"])

    op.create_table(
        "insights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("finding", sa.Text(), nullable=False),
        sa.Column("finding_confidence", sa.Float(), nullable=False),
        sa.Column("hypothesis", JSONB(), nullable=True),
        sa.Column("affected_context", JSONB(), nullable=False),
        sa.Column("impact", JSONB(), nullable=False),
        sa.Column("limitations", JSONB(), nullable=False),
        sa.Column("evidence", JSONB(), nullable=False),
        # pending → (Gate #2) approved | edited | rejected | investigating
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_insights_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["analysis_runs.id"], name=op.f("fk_insights_run_id_analysis_runs")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insights")),
    )
    op.create_index("ix_insights_product_id", "insights", ["product_id"])

    op.create_table(
        "insight_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("insight_id", sa.Uuid(), nullable=False),
        sa.Column("original_value", JSONB(), nullable=False),
        sa.Column("edited_value", JSONB(), nullable=True),
        sa.Column(
            "action",
            ENUM(name="insight_review_action", create_type=False),
            nullable=False,
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
            ["insight_id"], ["insights.id"],
            name=op.f("fk_insight_reviews_insight_id_insights"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name=op.f("fk_insight_reviews_reviewer_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insight_reviews")),
    )
    op.create_index("ix_insight_reviews_insight_id", "insight_reviews", ["insight_id"])


def downgrade() -> None:
    op.drop_index("ix_insight_reviews_insight_id", table_name="insight_reviews")
    op.drop_table("insight_reviews")
    op.drop_index("ix_insights_product_id", table_name="insights")
    op.drop_table("insights")
    op.drop_index("ix_evidence_product_id", table_name="evidence")
    op.drop_index("ix_evidence_run_id", table_name="evidence")
    op.drop_table("evidence")
    op.execute("DROP TYPE IF EXISTS insight_review_action")
