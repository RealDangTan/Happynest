"""Request/response schemas cho HITL review — Phase 13 (13-hitl-langgraph.md §3.2).

Contract C3 (delivery-contracts.md):
- POST /api/reviews/{feedback_id}: action approve|edit|reject; action=edit
  bắt buộc kèm `edited_content` khác rỗng → vi phạm là **422** (FastAPI tự
  chuyển ValueError của model_validator thành 422).
- POST /api/corrections/{feedback_id}: CẦN ít nhất 1 nhãn trong body
  (categories/ai_issue/severity/sentiment) — rỗng toàn bộ → 422.

⚠️ PII boundary: `edited_content` là text NGƯỜI DÙNG GÕ — chưa sanitize.
Schema chỉ vận chuyển; việc đi qua Presidio trước khi lưu là trách nhiệm của
graph (services/hitl_graph.py), KHÔNG phải của schema.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import AiIssue, Sentiment, Severity
from app.schemas.feedback import FeedbackOut

ReviewActionLiteral = Literal["approve", "edit", "reject"]


class ReviewIn(BaseModel):
    """Body POST /api/reviews/{feedback_id}."""

    action: ReviewActionLiteral
    edited_content: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _edit_requires_content(self) -> "ReviewIn":
        if self.action == "edit" and not (
            self.edited_content and self.edited_content.strip()
        ):
            raise ValueError(
                "action='edit' bắt buộc kèm edited_content khác rỗng "
                "(nội dung đã chỉnh sửa bởi người review)."
            )
        return self


class CorrectionIn(BaseModel):
    """Body POST /api/corrections/{feedback_id} — sửa nhãn trực tiếp.

    Chỉ các trường ĐƯỢC GỬI (khác None) mới được cập nhật; thiếu hoàn toàn
    → validator chặn. Enum fields khai báo bằng enum taxonomy sẵn có nên
    giá trị lạ tự động 422 — không string lạ lọt vào JSONB.
    """

    categories: list[str] | None = None
    ai_issue: AiIssue | None = None
    severity: Severity | None = None
    sentiment: Sentiment | None = None
    note: str | None = None

    @field_validator("categories")
    @classmethod
    def _categories_non_empty_items(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for item in v:
                if not item or not item.strip():
                    raise ValueError("Phần tử categories không được rỗng/toàn khoảng trắng.")
        return v

    @model_validator(mode="after")
    def _at_least_one_label(self) -> "CorrectionIn":
        if (
            self.categories is None
            and self.ai_issue is None
            and self.severity is None
            and self.sentiment is None
        ):
            raise ValueError(
                "Cần ít nhất một nhãn để sửa: categories/ai_issue/severity/sentiment."
            )
        return self

    def label_updates(self) -> dict:
        """Các nhãn thực sự được gửi (khác None) → dict gán thẳng lên Feedback."""
        return {
            f: getattr(self, f)
            for f in ("categories", "ai_issue", "severity", "sentiment")
            if getattr(self, f) is not None
        }


class CorrectionOut(FeedbackOut):
    """FeedbackOut + cờ xác nhận correction đã ghi — response phẳng đúng C3.

    Default False để model_validate trực tiếp từ row Feedback; endpoint
    corrections luôn trả True sau khi đã ghi CorrectionExample.
    """

    correction_recorded: bool = False
