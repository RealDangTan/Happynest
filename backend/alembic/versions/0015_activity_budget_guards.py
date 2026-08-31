"""controlled import lifecycle and scoped analysis metadata

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for value in ("profile_ready", "mapping_generating", "cancelled"):
        op.execute(
            f"ALTER TYPE import_status_enum ADD VALUE IF NOT EXISTS '{value}'"
        )
    op.execute("ALTER TYPE run_status ADD VALUE IF NOT EXISTS 'cancelled'")

    op.add_column("imports", sa.Column("original_filename", sa.String(255)))
    op.add_column("imports", sa.Column("source_row_count", sa.Integer()))
    op.add_column("imports", sa.Column("column_profiles", JSONB()))
    op.add_column("imports", sa.Column("mapping_started_at", sa.DateTime(timezone=True)))

    op.add_column("analysis_runs", sa.Column("import_id", sa.Uuid()))
    op.add_column("analysis_runs", sa.Column("mode", sa.String(20)))
    op.add_column(
        "analysis_runs",
        sa.Column("chunk_size", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "analysis_runs", sa.Column("cancel_requested_at", sa.DateTime(timezone=True))
    )
    op.create_foreign_key(
        op.f("fk_analysis_runs_import_id_imports"),
        "analysis_runs",
        "imports",
        ["import_id"],
        ["id"],
    )
    op.create_index("ix_analysis_runs_import_id", "analysis_runs", ["import_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_runs_import_id", table_name="analysis_runs")
    op.drop_constraint(
        op.f("fk_analysis_runs_import_id_imports"),
        "analysis_runs",
        type_="foreignkey",
    )
    for column in (
        "cancel_requested_at",
        "failed_count",
        "chunk_size",
        "mode",
        "import_id",
    ):
        op.drop_column("analysis_runs", column)
    for column in (
        "mapping_started_at",
        "column_profiles",
        "source_row_count",
        "original_filename",
    ):
        op.drop_column("imports", column)
    # Native PG enum values cannot be removed safely; they intentionally remain.
