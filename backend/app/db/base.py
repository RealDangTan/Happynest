"""DeclarativeBase dùng chung + import toàn bộ models.

Alembic env.py chỉ cần `from app.db.base import Base` là có metadata đầy đủ.
Naming convention ổn định cho constraint → migration autogenerate/downgrade sạch.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Import models CUỐI file (tránh circular) để đăng ký đủ bảng vào metadata.
# noqa: E402,F401 — import có chủ đích, không dùng trực tiếp tại đây.
from app.models import (  # noqa: E402,F401
    analysis_run,
    cluster,
    feedback,
    import_,
    llm_call_log,
    product,
    user,
)
