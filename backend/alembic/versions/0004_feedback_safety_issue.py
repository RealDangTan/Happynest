"""feedbacks: thêm cột safety_issue (Phase 07 — lệch §6 có chủ đích)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-24

Xem docs/decisions.md entry "Phase 07: thêm cột safety_issue vào bảng feedbacks":
công thức HITL cần truy vấn trực tiếp flag an toàn, không giấu trong
categories/rationale. Default false — feedback chưa classify giữ nguyên ngữ nghĩa.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "feedbacks",
        sa.Column(
            "safety_issue",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("feedbacks", "safety_issue")
