"""sources: registry nguồn phản hồi (FE-03b — decisions 2026-08-25)

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-25

Ingest permissive giữ nguyên — bảng này chỉ làm danh mục cho UI (combobox +
wizard đăng ký nguồn). Không DELETE: feedbacks trỏ source bằng string, xoá tên
tạo orphan ý nghĩa; UI dùng is_active để ẩn.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("sources")
