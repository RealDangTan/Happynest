"""LISTEN: product_schemas registry + imports.mapping_proposal + llm_call_type 'schema_map'

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-28

Plan 22 Task 1. product_schemas = registry versioned product-specific (VoC OS
§8/§56): definition JSONB {fields: [{key, label, description, type}]}, status
draft|active|superseded. imports.mapping_proposal = proposal của LLM mapper
giữa POST /imports và Gate #1 decision (tránh bảng riêng — import lifecycle
ngắn). ALTER TYPE llm_call_type ADD VALUE 'schema_map' (PG17 cho phép trong
transaction miễn KHÔNG dùng giá trị mới trong cùng transaction — migration
chỉ ADD, downgrade không gỡ được theo precedent 0007).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE llm_call_type ADD VALUE IF NOT EXISTS 'schema_map'")

    op.create_table(
        "product_schemas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", JSONB(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_schemas_product_id_products"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_schemas")),
        sa.UniqueConstraint(
            "product_id", "version", name=op.f("uq_product_schemas_product_id_version")
        ),
    )
    op.create_index(
        "ix_product_schemas_product_id", "product_schemas", ["product_id"]
    )

    op.add_column(
        "imports", sa.Column("mapping_proposal", JSONB(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("imports", "mapping_proposal")
    op.drop_index("ix_product_schemas_product_id", table_name="product_schemas")
    op.drop_table("product_schemas")
    # ADD VALUE không đảo được (precedent 0007) — 'schema_map' ở lại trong type.
