"""feedbacks.cluster_id — membership cụm HDBSCAN (plan 14, migration DUY NHẤT delivery)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-26

Lệch số so với plan viết sớm (plan ghi 0004): head thực tế đã là 0005 do
sources registry FE-03b — xem decisions.md 2026-08-26. Bảng checkpoint
LangGraph vẫn ngoài Alembic nhờ filter env.py giữ nguyên.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "feedbacks",
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_feedbacks_cluster_id_clusters",
        "feedbacks",
        "clusters",
        ["cluster_id"],
        ["id"],
    )
    op.create_index("ix_feedbacks_cluster_id", "feedbacks", ["cluster_id"])


def downgrade() -> None:
    op.drop_index("ix_feedbacks_cluster_id", table_name="feedbacks")
    op.drop_constraint(
        "fk_feedbacks_cluster_id_clusters", "feedbacks", type_="foreignkey"
    )
    op.drop_column("feedbacks", "cluster_id")
