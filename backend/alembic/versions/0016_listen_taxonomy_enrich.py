"""Listen taxonomy/enrich substrate (plans 31–32).

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-07

- llm_call_type ADD 'enrich' / 'taxonomy_generate' / 'topic_recommend'
  (precedent 0007/0011: ADD VALUE không đảo được trong downgrade).
- products.taxonomy_version INT NOT NULL DEFAULT 1 — snapshot vào
  feedback.ai_analysis mỗi lần enrich (định danh dataset theo version taxonomy).
- taxonomies.slug VARCHAR(200) NULL + UNIQUE (product_id, slug) WHERE slug IS
  NOT NULL — id ổn định cho topic label (bất biến khi rename name).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for value in ("enrich", "taxonomy_generate", "topic_recommend"):
        op.execute(f"ALTER TYPE llm_call_type ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column(
        "products",
        sa.Column(
            "taxonomy_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column("taxonomies", sa.Column("slug", sa.String(length=200), nullable=True))
    op.create_index(
        "ux_taxonomies_product_slug",
        "taxonomies",
        ["product_id", "slug"],
        unique=True,
        postgresql_where=sa.text("slug IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_taxonomies_product_slug", table_name="taxonomies")
    op.drop_column("taxonomies", "slug")
    op.drop_column("products", "taxonomy_version")
