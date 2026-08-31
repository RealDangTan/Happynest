"""importing status + imports.report (background import execution)

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-29

Plan 22 fix UX: POST /mapping/decision trả lời NGAY (status → importing),
executed import chạy background (sanitize 650 row mất vài phút — sync request
làm proxy FE reset connection). Báo cáo per-row lưu `imports.report` để FE
poll đọc kết quả.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ADD VALUE trong transaction OK (PG17) miễn không dùng value mới trong
    # cùng transaction — migration này chỉ ADD.
    op.execute("ALTER TYPE import_status_enum ADD VALUE IF NOT EXISTS 'importing'")
    op.add_column("imports", sa.Column("report", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("imports", "report")
    # ADD VALUE không đảo được (precedent 0007) — 'importing' ở lại trong type.
