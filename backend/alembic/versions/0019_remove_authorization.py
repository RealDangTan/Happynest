"""Remove account roles and product ownership; keep identity authentication.

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_products_owner_id", table_name="products")
    op.drop_constraint("fk_products_owner_id_users", "products", type_="foreignkey")
    op.drop_column("products", "owner_id")
    op.drop_column("users", "role")
    op.execute("DROP TYPE user_role")


def downgrade() -> None:
    # Restore the former schema, not the discarded role/ownership assignments.
    op.execute("CREATE TYPE user_role AS ENUM ('pm', 'operations')")
    role_type = postgresql.ENUM("pm", "operations", name="user_role", create_type=False)
    op.add_column("users", sa.Column("role", role_type, nullable=False,
                                   server_default="operations"))
    op.alter_column("users", "role", server_default=None)
    op.add_column("products", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_products_owner_id_users", "products", "users",
                          ["owner_id"], ["id"])
    op.create_index("ix_products_owner_id", "products", ["owner_id"])
