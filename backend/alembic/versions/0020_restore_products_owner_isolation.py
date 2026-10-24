"""Restore per-account isolation: products.owner_id (reverse 0019).

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-22

Owner report 2026-10-22: account mới đăng ký thấy toàn bộ product/workspace
của account khác — vô lý với kịch bản nhiều công ty. Migration khôi phục
đúng phần products của 0018 mà 0019 đã gỡ (giữ nguyên users.role đã bỏ):
1. Thêm products.owner_id (FK users.id, index) — NOT NULL sau backfill.
2. Gỡ unique constraint toàn cục trên products.name nếu còn (uniqueness
   per-owner, enforce ở tầng app).
3. Backfill product hiện có về pm@thesis.local (fallback: user cũ nhất) —
   account mới đăng ký sẽ có workspace trống như quyết định 2026-10-11.
"""

from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_products_owner_id_users", "products", "users", ["owner_id"], ["id"]
    )
    op.create_index("ix_products_owner_id", "products", ["owner_id"])

    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS uq_products_name")

    op.execute(
        "UPDATE products SET owner_id = COALESCE("
        "(SELECT id FROM users WHERE email = 'pm@thesis.local'),"
        "(SELECT id FROM users ORDER BY created_at LIMIT 1)"
        ") WHERE owner_id IS NULL"
    )
    op.alter_column("products", "owner_id", existing_type=sa.Uuid(), nullable=False)


def downgrade() -> None:
    # Về đúng schema 0019: owner_id nullable, không NOT NULL để không mất dữ liệu.
    op.alter_column("products", "owner_id", existing_type=sa.Uuid(), nullable=True)
    op.drop_index("ix_products_owner_id", table_name="products")
    op.drop_constraint("fk_products_owner_id_users", "products", type_="foreignkey")
    op.drop_column("products", "owner_id")
