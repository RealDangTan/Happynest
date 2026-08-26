"""Bảng action_drafts — artifact draft agent sinh ra để người copy-paste.

Quyết 25/08: KHÔNG tích hợp Jira/Slack thật — draft là đích cuối.
Insight bị xoá → draft theo CASCADE (không mồ côi).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DRAFT_KIND_ENUM, DRAFT_STATUS_ENUM, DraftKind, DraftStatus


class ActionDraft(Base):
    __tablename__ = "action_drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("insights.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[DraftKind] = mapped_column(DRAFT_KIND_ENUM, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DraftStatus] = mapped_column(
        DRAFT_STATUS_ENUM, nullable=False, default=DraftStatus.draft
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
