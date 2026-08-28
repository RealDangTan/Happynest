"""Bộ Python enum ánh xạ native PG enum types.

Re-plan VoC OS 2026-08-28 (decisions.md): reshape 0008 DROP các enum cũ
(ai_issue_enum, sentiment_enum, severity_enum, review_status, review_action,
draft_kind, draft_status) — sentiment/severity/business labels giờ sống TRONG
`feedback.ai_analysis` JSONB dưới dạng string. Các Python enum giữ lại làm
validation giá trị khi ghi/đọc JSONB, KHÔNG còn cột PG enum tương ứng.

Enum PG còn sống: user_role (0001), run_status + llm_call_type (0002),
import_status_enum (0008). Đổi bộ giá trị phải ALTER TYPE ADD VALUE qua
migration mới — không sửa tay.
"""

import enum

from sqlalchemy import Enum as SaEnum


class UserRole(str, enum.Enum):
    pm = "pm"
    operations = "operations"


class AiIssue(str, enum.Enum):
    """Giá trị JSONB `ai_analysis.ai_issue` — validation thuần, không PG column."""

    hallucination = "hallucination"
    inaccuracy = "inaccuracy"
    bias = "bias"
    safety = "safety"
    privacy = "privacy"
    performance = "performance"
    other = "other"


class Sentiment(str, enum.Enum):
    """Giá trị JSONB `ai_analysis.sentiment` — chỉ validation, không PG column."""

    positive = "positive"
    negative = "negative"
    neutral = "neutral"
    mixed = "mixed"


class Severity(str, enum.Enum):
    """Giá trị JSONB `ai_analysis.severity`."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RunStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class LlmCallType(str, enum.Enum):
    classify = "classify"
    embed = "embed"
    name_cluster = "name_cluster"
    generate_insight = "generate_insight"
    # value 'route'/'critic' đã ADD vào PG type ở 0007; graph cũ bị strip
    # 2026-08-28 — value giữ nguyên trong type (ADD VALUE không đảo được),
    # UNDERSTAND mới (plan 25) sẽ ADD value riêng.
    route = "route"
    critic = "critic"


class ImportStatus(str, enum.Enum):
    pending = "pending"
    mapping_review = "mapping_review"
    imported = "imported"
    failed = "failed"


def _pg(py_enum: type[enum.Enum], type_name: str) -> SaEnum:
    """SaEnum native PG, lưu VALUE (không phải name), chia sẻ instance giữa các bảng."""
    return SaEnum(
        py_enum,
        name=type_name,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
    )


USER_ROLE_ENUM = _pg(UserRole, "user_role")
RUN_STATUS_ENUM = _pg(RunStatus, "run_status")
LLM_CALL_TYPE_ENUM = _pg(LlmCallType, "llm_call_type")
IMPORT_STATUS_ENUM = _pg(ImportStatus, "import_status_enum")
