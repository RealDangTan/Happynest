"""Taxonomy governance — canonical + emerging themes (VoC OS §20–21, plan 23)

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-28

VoC OS §21: AI KHÔNG BAO GIỜ tự mutate canonical taxonomy. Flow: feedback →
match taxonomy hiện có → classify; không match → emerging theme (accumulate
evidence) → human review → approve/merge/reject. Seed mặc định: mỗi product
hiện có nhận 5 nhánh canonical gốc (AI Quality, Search, Account, Performance,
Other — theo §20).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT_ROOTS = ("AI Quality", "Search", "Account", "Performance", "Other")


def upgrade() -> None:
    op.create_table(
        "taxonomies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # canonical (human-governed) | emerging (AI đề xuất chờ duyệt)
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="canonical"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_taxonomies_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["taxonomies.id"], name=op.f("fk_taxonomies_parent_id_taxonomies")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_taxonomies")),
    )
    op.create_index("ix_taxonomies_product_id", "taxonomies", ["product_id"])
    op.create_index(
        "uq_taxonomies_product_id_name", "taxonomies", ["product_id", "name"], unique=True
    )

    # Seed canonical roots cho mọi product hiện có (chỉ products đã tồn tại)
    for root in _DEFAULT_ROOTS:
        op.execute(
            f"""
            INSERT INTO taxonomies (id, product_id, name, kind, status)
            SELECT gen_random_uuid(), p.id, '{root}', 'canonical', 'active'
            FROM products p
            WHERE NOT EXISTS (
                SELECT 1 FROM taxonomies t
                WHERE t.product_id = p.id AND t.name = '{root}'
            )
            """
        )


def downgrade() -> None:
    op.drop_index("uq_taxonomies_product_id_name", table_name="taxonomies")
    op.drop_index("ix_taxonomies_product_id", table_name="taxonomies")
    op.drop_table("taxonomies")
