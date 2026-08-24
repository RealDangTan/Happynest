"""clusters, insights, human_reviews, correction_examples (tạo bây giờ — unused)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, JSONB

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # review_status tái dùng type đã tạo ở 0002; chỉ review_action là mới.
    op.execute("CREATE TYPE review_action AS ENUM ('approve', 'edit', 'reject')")

    op.create_table(
        "clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("feedback_count", sa.Integer(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_count", sa.Integer(), nullable=False),
        sa.Column("previous_count", sa.Integer(), nullable=False),
        sa.Column("growth_ratio", sa.Float(), nullable=False),
        sa.Column("is_emerging", sa.Boolean(), nullable=False),
        sa.Column("is_spike", sa.Boolean(), nullable=False),
        # scale ưu tiên chốt ở giai đoạn clustering — nullable từ đầu
        sa.Column("suggested_priority", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clusters")),
    )

    op.create_table(
        "insights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("evidence_ids", JSONB(), nullable=False),
        sa.Column(
            "review_status",
            ENUM(name="review_status", create_type=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cluster_id"], ["clusters.id"], name=op.f("fk_insights_cluster_id_clusters")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insights")),
    )

    op.create_table(
        "human_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feedback_id", sa.Uuid(), nullable=False),
        sa.Column("original_value", JSONB(), nullable=False),
        sa.Column("edited_value", JSONB(), nullable=True),
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
            ["feedback_id"],
            ["feedbacks.id"],
            name=op.f("fk_human_reviews_feedback_id_feedbacks"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name=op.f("fk_human_reviews_reviewer_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_human_reviews")),
    )

    op.create_table(
        "correction_examples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feedback_id", sa.Uuid(), nullable=False),
        sa.Column("original_prediction", JSONB(), nullable=False),
        sa.Column("corrected_value", JSONB(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["feedback_id"],
            ["feedbacks.id"],
            name=op.f("fk_correction_examples_feedback_id_feedbacks"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_correction_examples")),
    )


def downgrade() -> None:
    op.drop_table("correction_examples")
    op.drop_table("human_reviews")
    op.drop_table("insights")
    op.drop_table("clusters")
    op.execute("DROP TYPE IF EXISTS review_action")
