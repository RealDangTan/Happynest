"""baseline: pgvector extension + users

Migration viết tay theo nhóm logic (plan 03 §3.6). CREATE TYPE thủ công với
ENUM(create_type=False) ở mức cột để tránh double-create khi nhiều bảng
dùng chung một type.

Revision ID: 0001
Revises:
Create Date: 2026-08-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # bare — Supabase deprecated extension version pinning (2026-08-05).
    # Type `vector` phải thấy được qua search_path=extensions,public
    # (engine đã đặt options; migration chạy qua cùng engine).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("CREATE TYPE user_role AS ENUM ('pm', 'operations')")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "role", ENUM(name="user_role", create_type=False), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )


def downgrade() -> None:
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_role")
    # KHÔNG drop extension vector — dùng chung, idempotent giữa các lần upgrade lại.
