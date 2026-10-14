"""Per-account data isolation: products.owner_id (multi-tenant scope).

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-11

Fix "đăng ký acc mới mà thấy data của acc khác" (user report 2026-10-11):
mọi account dùng chung 1 dataset vì products không có owner. Migration này:
1. Thêm products.owner_id (FK users.id, nullable tạm thời).
2. Gỡ unique constraint toàn cục trên products.name (uniqueness giờ là
   per-owner, enforce ở tầng app).
3. Backfill toàn bộ product hiện có về user pm seed (pm@thesis.local) —
   quyết định owner 2026-10-11 (acc mới đăng ký sẽ có workspace trống).
"""

from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_products_owner_id_users", "products", "users", ["owner_id"], ["id"]
    )
    op.create_index("ix_products_owner_id", "products", ["owner_id"])

    # Uniqueness của name giờ là per-owner (app layer) — gỡ unique toàn cục.
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS uq_products_name")

    op.execute(
        "UPDATE products SET owner_id = (SELECT id FROM users "
        "WHERE email = 'pm@thesis.local') WHERE owner_id IS NULL"
    )

    # analysis_runs chưa link product (agent runs tạo với product_id nhưng
    # không persist) — thêm cột để route run/trace/decision scope theo owner.
    op.add_column(
        "analysis_runs", sa.Column("product_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_analysis_runs_product_id_products",
        "analysis_runs",
        "products",
        ["product_id"],
        ["id"],
    )
    op.create_index(
        "ix_analysis_runs_product_id", "analysis_runs", ["product_id"]
    )
    # Backfill legacy: qua imports trước, rồi qua insights (run không import).
    op.execute(
        "UPDATE analysis_runs ar SET product_id = i.product_id "
        "FROM imports i WHERE ar.import_id = i.id AND ar.product_id IS NULL"
    )
    op.execute(
        "UPDATE analysis_runs ar SET product_id = ins.product_id "
        "FROM insights ins WHERE ins.run_id = ar.id AND ar.product_id IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_runs_product_id", table_name="analysis_runs")
    op.drop_constraint(
        "fk_analysis_runs_product_id_products", "analysis_runs", type_="foreignkey"
    )
    op.drop_column("analysis_runs", "product_id")
    op.execute("UPDATE products SET owner_id = NULL")
    op.drop_index("ix_products_owner_id", table_name="products")
    op.drop_constraint("fk_products_owner_id_users", "products", type_="foreignkey")
    op.drop_column("products", "owner_id")
    op.create_unique_constraint("uq_products_name", "products", ["name"])
