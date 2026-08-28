"""voc-os core reshape: products + imports + feedback JSONB zones (DESTRUCTIVE)

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-28

Plan 21 Task 1 — re-plan VoC OS 2026-08-28 (decisions.md cùng ngày).

⚠️ DESTRUCTIVE: DROP feedbacks (bảng phẳng cũ) + human_reviews,
correction_examples, action_drafts, insight_reviews, impact_checks, sources,
insights. Demo data bỏ đi — KHÔNG migrate row (quyết định owner "fresh
reshape"). llm_call_logs sống sót: FK feedback_id bị gỡ, cột giữ lại nullable.

New `feedback` (đơn số, mới hoàn toàn):
    id, product_id, import_id, source, source_record_id, occurred_at,
    imported_at, raw_content (PII boundary), feedback_text (sanitized),
    data JSONB, source_meta JSONB, ai_analysis JSONB, pii_detected,
    pii_entities, embedding + sidecars, cluster_id, created_at.

Downgrade tái tạo schema CŨ nguyên vẹn (không data) theo định nghĩa
0002/0003/0005/0006/0007 — cần quay lui thì phải import lại data từ ngoài.
Bảng checkpoint LangGraph vẫn ngoài Alembic nhờ filter env.py.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ENUM, JSONB

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE import_status_enum AS ENUM "
        "('pending', 'mapping_review', 'imported', 'failed')"
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )

    op.create_table(
        "imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("mapping_version", sa.String(length=50), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            ENUM(name="import_status_enum", create_type=False),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_imports_product_id_products"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imports")),
    )
    op.create_index("ix_imports_product_id", "imports", ["product_id"])

    # llm_call_logs sống sót — gỡ FK feedback_id trước khi drop feedbacks.
    op.execute(
        "ALTER TABLE llm_call_logs DROP CONSTRAINT IF EXISTS "
        "fk_llm_call_logs_feedback_id_feedbacks"
    )

    # --- Drop các bảng thuộc thiết kế cũ (thứ tự an toàn, CASCADE chốt) ---
    op.drop_table("human_reviews")
    op.drop_table("correction_examples")
    op.drop_table("impact_checks")
    op.drop_table("action_drafts")
    op.drop_table("insight_reviews")
    op.drop_table("insights")
    op.drop_table("sources")
    op.drop_table("feedbacks")

    # Enum types không còn cột nào dùng → dọn.
    for type_name in (
        "review_status",
        "review_action",
        "ai_issue_enum",
        "sentiment_enum",
        "severity_enum",
        "draft_status_enum",
        "draft_kind_enum",
    ):
        op.execute(f"DROP TYPE IF EXISTS {type_name}")

    # --- Bảng feedback mới (VoC OS plan §15/§55 + quyết định products-only) ---
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("import_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        # event time = thời điểm phản hồi diễn ra (nguồn cung cấp) — §15
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # PII boundary: raw KHÔNG BAO GIỜ ra khỏi biên; feedback_text = sanitized
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        # JSONB zones (§17): data = chiều phân tích product, source_meta =
        # metadata nguồn, ai_analysis = diễn giải ngữ nghĩa pipeline ghi.
        sa.Column("data", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "source_meta", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "ai_analysis", JSONB(), nullable=True
        ),
        sa.Column("pii_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("pii_entities", JSONB(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=True),
        sa.Column("cluster_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_feedback_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["import_id"], ["imports.id"], name=op.f("fk_feedback_import_id_imports")
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_feedback_analysis_run_id_analysis_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["cluster_id"], ["clusters.id"], name=op.f("fk_feedback_cluster_id_clusters")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedback")),
    )
    op.create_index("ix_feedback_product_id", "feedback", ["product_id"])
    op.create_index("ix_feedback_cluster_id", "feedback", ["cluster_id"])
    op.create_index("ix_feedback_import_id", "feedback", ["import_id"])

    # Seed mặc định: product dùng chung cho ingest legacy (phase 22 LISTEN
    # sẽ cho tạo product từ UI/API).
    op.execute(
        "INSERT INTO products (id, name, description) VALUES ("
        "gen_random_uuid(), 'Happynest', "
        "'Sản phẩm mặc định tạo bởi migration 0008 — đổi tên qua API.')"
    )


def downgrade() -> None:
    # --- Xóa schema mới ---
    op.drop_index("ix_feedback_import_id", table_name="feedback")
    op.drop_index("ix_feedback_cluster_id", table_name="feedback")
    op.drop_index("ix_feedback_product_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_imports_product_id", table_name="imports")
    op.drop_table("imports")
    op.drop_table("products")
    op.execute("DROP TYPE IF EXISTS import_status_enum")

    # --- Tái tạo schema cũ theo đúng định nghĩa 0002/0003/0005/0006/0007
    #     (KHÔNG data — data cũ đã bị bỏ theo quyết định fresh reshape) ---
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
    op.execute("CREATE TYPE review_action AS ENUM ('approve', 'edit', 'reject')")
    op.execute(
        "CREATE TYPE draft_kind_enum AS ENUM ('draft_ticket', 'slack_message', 'report')"
    )
    op.execute("CREATE TYPE draft_status_enum AS ENUM ('draft', 'exported')")

    op.create_table("sources", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True), sa.Column("description", sa.Text(), nullable=True), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    op.create_table(
        "feedbacks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_ref", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("sanitized_content", sa.Text(), nullable=True),
        sa.Column("pii_detected", sa.Boolean(), nullable=False),
        sa.Column("pii_entities", JSONB(), nullable=True),
        sa.Column("categories", JSONB(), nullable=True),
        sa.Column("ai_issue", ENUM(name="ai_issue_enum", create_type=False), nullable=True),
        sa.Column("sentiment", ENUM(name="sentiment_enum", create_type=False), nullable=True),
        sa.Column("severity", ENUM(name="severity_enum", create_type=False), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("review_status", ENUM(name="review_status", create_type=False), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], name=op.f("fk_feedbacks_analysis_run_id_analysis_runs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedbacks")),
    )

    op.create_table(
        "insights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("evidence_ids", JSONB(), nullable=False),
        sa.Column("review_status", ENUM(name="review_status", create_type=False), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["cluster_id"], ["clusters.id"], name=op.f("fk_insights_cluster_id_clusters")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insights")),
    )

    op.create_table(
        "human_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feedback_id", sa.Uuid(), nullable=False),
        sa.Column("original_value", JSONB(), nullable=False),
        sa.Column("edited_value", JSONB(), nullable=True),
        sa.Column("action", ENUM(name="review_action", create_type=False), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["feedback_id"], ["feedbacks.id"], name=op.f("fk_human_reviews_feedback_id_feedbacks")),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], name=op.f("fk_human_reviews_reviewer_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_human_reviews")),
    )

    op.create_table(
        "correction_examples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feedback_id", sa.Uuid(), nullable=False),
        sa.Column("original_prediction", JSONB(), nullable=False),
        sa.Column("corrected_value", JSONB(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["feedback_id"], ["feedbacks.id"], name=op.f("fk_correction_examples_feedback_id_feedbacks")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_correction_examples")),
    )

    op.create_table(
        "action_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("insight_id", sa.Uuid(), nullable=False),
        sa.Column("kind", ENUM(name="draft_kind_enum", create_type=False), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", ENUM(name="draft_status_enum", create_type=False), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["insight_id"], ["insights.id"], name=op.f("fk_action_drafts_insight_id_insights"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_action_drafts")),
    )

    op.create_table(
        "insight_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("insight_id", sa.Uuid(), nullable=False),
        sa.Column("original_value", JSONB(), nullable=False),
        sa.Column("edited_value", JSONB(), nullable=True),
        sa.Column("action", ENUM(name="review_action", create_type=False), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["insight_id"], ["insights.id"], name=op.f("fk_insight_reviews_insight_id_insights"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], name=op.f("fk_insight_reviews_reviewer_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insight_reviews")),
    )

    op.create_table(
        "impact_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("insight_id", sa.Uuid(), nullable=True),
        sa.Column("cluster_id", sa.Uuid(), nullable=True),
        sa.Column("cluster_name", sa.String(length=255), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("before_count", sa.Integer(), nullable=False),
        sa.Column("after_count", sa.Integer(), nullable=False),
        sa.Column("delta_ratio", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["insight_id"], ["insights.id"], name=op.f("fk_impact_checks_insight_id_insights"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_impact_checks")),
    )
    op.create_index("ix_impact_checks_insight_id", "impact_checks", ["insight_id"])

    # khôi phục FK llm_call_logs.feedback_id + FK feedbacks.cluster_id (0006)
    op.execute(
        "ALTER TABLE llm_call_logs ADD CONSTRAINT "
        "fk_llm_call_logs_feedback_id_feedbacks "
        "FOREIGN KEY (feedback_id) REFERENCES feedbacks (id)"
    )
    op.create_foreign_key(
        "fk_feedbacks_cluster_id_clusters", "feedbacks", "clusters",
        ["cluster_id"], ["id"],
    )
    op.create_index("ix_feedbacks_cluster_id", "feedbacks", ["cluster_id"])
