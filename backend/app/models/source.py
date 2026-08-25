"""Bảng sources — registry nguồn phản hồi (FE-03b, decisions 2026-08-25).

Ingest vẫn permissive: feedback ghi source dạng string KHÔNG bị chặn khi tên
nguồn chưa đăng ký ở đây. Registry chỉ phục vụ UI (combobox/wizard) trong đợt
này — validation chặt là scope sau (decisions cùng ngày).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
