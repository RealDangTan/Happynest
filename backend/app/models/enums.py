"""Bộ Python enum ánh xạ 9 native PG enum types (execute-plan §6).

Bộ giá trị ai_issue_enum / sentiment_enum chốt theo entry dated
2026-08-24 trong docs/decisions.md (= đề xuất khởi điểm plan §3.5).
Đổi sau này phải ALTER TYPE ADD VALUE qua migration mới — không sửa tay.

Phase 07 phải nhất quán với bộ này qua schemas/taxonomy.py.
Migration 0007 (agent substrate) bổ sung draft_kind/draft_status và 2
value 'route'/'critic' của llm_call_type.
"""

import enum

from sqlalchemy import Enum as SaEnum


class UserRole(str, enum.Enum):
    pm = "pm"
    operations = "operations"


class AiIssue(str, enum.Enum):
    hallucination = "hallucination"
    inaccuracy = "inaccuracy"
    bias = "bias"
    safety = "safety"
    privacy = "privacy"
    performance = "performance"
    other = "other"


class Sentiment(str, enum.Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"
    mixed = "mixed"


class Severity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ReviewStatus(str, enum.Enum):
    unreviewed = "unreviewed"
    pending = "pending"
    approved = "approved"
    edited = "edited"
    rejected = "rejected"


class ReviewAction(str, enum.Enum):
    approve = "approve"
    edit = "edit"
    reject = "reject"


class RunStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class LlmCallType(str, enum.Enum):
    classify = "classify"
    embed = "embed"
    name_cluster = "name_cluster"
    generate_insight = "generate_insight"
    # agent-router graph (phase 19): router node + critic reflection.
    # KHÔNG có 'tool_call' — tool không-LLM không thuộc bảng llm call logs
    # (decisions 2026-08-26).
    route = "route"
    critic = "critic"


class DraftKind(str, enum.Enum):
    """Loại artifact draft mà agent sinh ra để người copy-paste (plan 19)."""

    draft_ticket = "draft_ticket"
    slack_message = "slack_message"
    report = "report"


class DraftStatus(str, enum.Enum):
    draft = "draft"
    exported = "exported"


def _pg(py_enum: type[enum.Enum], type_name: str) -> SaEnum:
    """SaEnum native PG, lưu VALUE (không phải name), chia sẻ instance giữa các bảng."""
    return SaEnum(
        py_enum,
        name=type_name,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
    )


USER_ROLE_ENUM = _pg(UserRole, "user_role")
AI_ISSUE_ENUM = _pg(AiIssue, "ai_issue_enum")
SENTIMENT_ENUM = _pg(Sentiment, "sentiment_enum")
SEVERITY_ENUM = _pg(Severity, "severity_enum")
REVIEW_STATUS_ENUM = _pg(ReviewStatus, "review_status")
REVIEW_ACTION_ENUM = _pg(ReviewAction, "review_action")
RUN_STATUS_ENUM = _pg(RunStatus, "run_status")
LLM_CALL_TYPE_ENUM = _pg(LlmCallType, "llm_call_type")
DRAFT_KIND_ENUM = _pg(DraftKind, "draft_kind_enum")
DRAFT_STATUS_ENUM = _pg(DraftStatus, "draft_status_enum")
