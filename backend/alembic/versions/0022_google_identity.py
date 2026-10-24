"""Google OAuth identity: password_hash nullable + users.google_sub (0022).

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-23

Đăng nhập bằng Google (decisions.md 2026-10-23):
1. `users.password_hash` nới thành nullable — account Google-only không có
   mật khẩu; route đăng nhập password chặn NULL trước khi verify.
2. `users.google_sub` (TEXT, unique, nullable) lưu `sub` từ id_token —
   liên kết account password sẵn có khi email khớp (link-on-first-login).
"""

from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=True)
    op.add_column("users", sa.Column("google_sub", sa.Text(), nullable=True))
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)


def downgrade() -> None:
    # Chặn downgrade nếu còn account Google-only (password_hash NULL) để không
    # mất bản sắc — dọn dữ liệu trước khi hạ schema.
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM users WHERE password_hash IS NULL) "
        "THEN RAISE EXCEPTION 'Con account Google-only (password_hash NULL) — khong the downgrade'; "
        "END IF; END $$;"
    )
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "google_sub")
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=False)
