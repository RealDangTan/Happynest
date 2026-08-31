"""Bảng imports — 1 lần nạp dữ liệu vào product (VoC OS §6, §18).

Phase 21: ingest legacy (POST đơn lẻ + import-csv) tạo row `status='imported'`
ngay để feedback gắn import_id — nguồn gốc lô dữ liệu luôn truy được.
Phase 22 (LISTEN): CSV đi qua pipeline profiler → LLM mapper → Gate #1,
status chuyển `mapping_review` trước khi `imported`; raw file lưu Supabase
Storage (`storage_path`).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ImportStatus, IMPORT_STATUS_ENUM


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    # 'csv_legacy' (ingest trực tiếp phase 21) | 'csv' (LISTEN pipeline) | 'manual' | 'api'
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mapping_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    schema_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[ImportStatus] = mapped_column(
        IMPORT_STATUS_ENUM, nullable=False, default=ImportStatus.pending
    )
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    column_profiles: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    mapping_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Proposal của LLM mapper giữ lại giữa POST /imports và Gate #1 decision
    # (plan 22) — import lifecycle ngắn nên không cần bảng riêng.
    mapping_proposal: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Báo cáo kết quả nạp (imported/failed/errors) — background import ghi để
    # FE poll đọc (migration 0014).
    report: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
