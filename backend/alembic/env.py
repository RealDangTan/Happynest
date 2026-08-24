"""Alembic environment — Phase 03 (execute-plan §1 migrations decision).

- DATABASE_URL lấy từ Settings (backend/.env), ghi đè sqlalchemy.url của ini.
- target_metadata = Base.metadata (đầy đủ nhờ app.db.base import mọi models).
- include_object LOẠI 4 bảng langgraph checkpoint khỏi autogenerate NGÀY ĐẦU
  (quyết định đã khóa) — langgraph-checkpoint-postgres tự quản các bảng này.
- compare_type=True để bắt lệch kiểu cột.
"""

import os
import sys

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402

config = context.config

# KHÔNG dùng config.set_main_option() — configparser chết với '%' trong password
# percent-encoded. URL truyền thẳng từ Settings vào context.configure().
settings = get_settings()

target_metadata = Base.metadata

# Quyết định đã khóa: Alembic KHÔNG đụng 4 bảng checkpoint của langgraph.
LANGGRAPH_CHECKPOINT_TABLES = {
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
    "checkpoint_migrations",
}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name in LANGGRAPH_CHECKPOINT_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url_sqla,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Tái dùng engine ứng dụng — có sẵn connect_args search_path=extensions,public
    # (nơi Supabase cài extension vector).
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
