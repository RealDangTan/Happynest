"""feedbacks, analysis_runs, llm_call_logs + các enum pipeline

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ENUM, JSONB

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE run_status AS ENUM ('running', 'completed', 'failed')"
    )
    op.execute(
        "CREATE TYPE ai_issue_enum AS ENUM "
        "('hallucination', 'inaccuracy', 'bias', 'safety', 'privacy', "
        "'performance', 'other')"
    )
    op.execute(
        "CREATE TYPE sentiment_enum AS ENUM ('positive', 'negative', 'neutral', 'mixed')"
    )
    op.execute(
        "CREATE TYPE severity_enum AS ENUM ('low', 'medium', 'high', 'critical')"
    )
    op.execute(
        "CREATE TYPE review_status AS ENUM "
        "('unreviewed', 'pending', 'approved', 'edited', 'rejected')"
    )
    op.execute(
        "CREATE TYPE llm_call_type AS ENUM "
        "('classify', 'embed', 'name_cluster', 'generate_insight')"
    )

    # analysis_runs TRƯỚC feedbacks (feedbacks.analysis_run_id FK tới đây)
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=50), nullable=False),
        sa.Column("llm_model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status", ENUM(name="run_status", create_type=False), nullable=False
        ),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_runs")),
    )

    op.create_table(
        "feedbacks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_ref", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        # event time = thời điểm phản hồi diễn ra (nguồn cung cấp)
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("sanitized_content", sa.Text(), nullable=True),
        sa.Column("pii_detected", sa.Boolean(), nullable=False),
        sa.Column("pii_entities", JSONB(), nullable=True),
        sa.Column("categories", JSONB(), nullable=True),
        sa.Column(
            "ai_issue", ENUM(name="ai_issue_enum", create_type=False), nullable=True
        ),
        sa.Column(
            "sentiment", ENUM(name="sentiment_enum", create_type=False), nullable=True
        ),
        sa.Column(
            "severity", ENUM(name="severity_enum", create_type=False), nullable=True
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column(
            "review_status",
            ENUM(name="review_status", create_type=False),
            nullable=False,
        ),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_feedbacks_analysis_run_id_analysis_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedbacks")),
    )

    op.create_table(
        "llm_call_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=True),
        sa.Column("feedback_id", sa.Uuid(), nullable=True),
        sa.Column(
            "call_type", ENUM(name="llm_call_type", create_type=False), nullable=False
        ),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_llm_call_logs_analysis_run_id_analysis_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["feedback_id"],
            ["feedbacks.id"],
            name=op.f("fk_llm_call_logs_feedback_id_feedbacks"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_call_logs")),
    )


def downgrade() -> None:
    op.drop_table("llm_call_logs")
    op.drop_table("feedbacks")
    op.drop_table("analysis_runs")
    op.execute("DROP TYPE IF EXISTS llm_call_type")
    op.execute("DROP TYPE IF EXISTS review_status")
    op.execute("DROP TYPE IF EXISTS severity_enum")
    op.execute("DROP TYPE IF EXISTS sentiment_enum")
    op.execute("DROP TYPE IF EXISTS ai_issue_enum")
    op.execute("DROP TYPE IF EXISTS run_status")
