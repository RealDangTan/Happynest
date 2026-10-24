"""Đảo quyết định 2026-10-22: `name` canonical về tiếng Anh, thêm `name_vi` hiển thị.

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-23

`name` trở lại tiếng Anh (nhãn codebook nhất quán cho classifier), tên hiển thị
tiếng Việt chuyển sang cột mới `name_vi` (FE hiển thị `name_vi ?? name`).
Migration: (1) thêm cột; (2) mọi row cũ `name_vi = name` — hiển thị không đổi;
(3) 5 nhánh gốc seed (name đang tiếng Việt từ 0021/seed sau 0021) đổi `name` về
bộ tiếng Anh gốc của migration 0010, giữ `name_vi` tiếng Việt. Idempotent; slug
KHÔNG đụng tới (contract plan 31 — `ai_analysis.topics` không vỡ). Node thường
do human/GPT tạo trước 2026-10-23 giữ name cũ (vi/EN lẫn lộn là trạng thái quá
khứ được chấp nhận — human có thể sửa tiếp qua PATCH /api/taxonomies/nodes/{slug}).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (tên tiếng Việt hiện tại của root gốc, tên tiếng Anh canonical)
_RENAMES = [
    ("Chất lượng AI", "AI Quality"),
    ("Tìm kiếm", "Search"),
    ("Tài khoản", "Account"),
    ("Hiệu năng", "Performance"),
    ("Khác", "Other"),
]


def upgrade() -> None:
    op.add_column(
        "taxonomies", sa.Column("name_vi", sa.String(100), nullable=True)
    )
    # Hiển thị cũ phải giữ nguyên: name hiện tại (bất kể ngôn ngữ) thành label VI.
    op.execute("UPDATE taxonomies SET name_vi = name WHERE name_vi IS NULL")
    for vi_name, en_name in _RENAMES:
        op.execute(
            sa.text(
                "UPDATE taxonomies SET name = :en "
                "WHERE name = :vi AND name_vi = :vi"
            ).bindparams(en=en_name, vi=vi_name)
        )


def downgrade() -> None:
    for vi_name, en_name in _RENAMES:
        op.execute(
            sa.text(
                "UPDATE taxonomies SET name = :vi "
                "WHERE name = :en AND name_vi = :vi"
            ).bindparams(en=en_name, vi=vi_name)
        )
    op.drop_column("taxonomies", "name_vi")
