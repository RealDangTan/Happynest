"""Vi hóa nhánh canonical gốc (quyết định 2026-10-22 — thị trường VN).

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-22

FE hiển thị topic theo taxonomy `name` (slug là id bất biến — plan 31), nên
5 nhánh gốc tiếng Anh seed từ migration 0010 hiển thị sai thị trường. Migration
đổi NAME sang tiếng Việt, KHÔNG đụng slug → feedback.ai_analysis.topics và
enqueue matching không vỡ. Rename chỉ khi (slug, name) khớp CẶP tiếng Anh gốc
— tên đã bị human sửa qua governance thì giữ nguyên. Idempotent.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (slug gốc từ migration 0010, tên tiếng Anh gốc) → tên tiếng Việt
_RENAMES = {
    ("ai_quality", "AI Quality"): "Chất lượng AI",
    ("search", "Search"): "Tìm kiếm",
    ("account", "Account"): "Tài khoản",
    ("performance", "Performance"): "Hiệu năng",
    ("other", "Other"): "Khác",
}


def upgrade() -> None:
    for (slug, old_name), vi_name in _RENAMES.items():
        op.execute(
            sa.text(
                "UPDATE taxonomies SET name = :vi "
                "WHERE slug = :slug AND name = :old"
            ).bindparams(slug=slug, old=old_name, vi=vi_name)
        )


def downgrade() -> None:
    for (slug, old_name), vi_name in _RENAMES.items():
        op.execute(
            sa.text(
                "UPDATE taxonomies SET name = :old "
                "WHERE slug = :slug AND name = :vi"
            ).bindparams(slug=slug, old=old_name, vi=vi_name)
        )
