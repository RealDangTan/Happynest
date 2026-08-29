"""ACT agent service — VoC OS §44–52, §61 (plan 26).

ACT KHÔNG thực thi business changes — chỉ ĐỀ XUẤT (§44):
1. Function routing: LLM đánh giá relevance cho 8 business functions; chỉ
   relevance ≥ ACT_RELEVANCE_THRESHOLD mới sinh candidate (§47).
2. Candidate actions + estimates (impact/effort/urgency 1–10, confidence 0–1)
   — MỘT call LLM duy nhất gộp routing+generate+estimate (kiềm chế tín dụng,
   lệch được ghi trong plan 26).
3. priority_score = DETERMINISTIC (§49) — LLM KHÔNG BAO GIỜ tự tính priority.
4. Gate #3 override: human_* columns ghi vị trí human, giá trị agent giữ
   nguyên làm evaluation data (§52); priority tính lại từ effective values.
"""

import json
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.action import Action
from app.models.enums import BusinessFunction, LlmCallType
from app.models.insight import Insight
from app.services.llm_client import LLMStructureError, chat_structured

PROMPT_VERSION = "act-v1"

_FUNCTIONS = [f.value for f in BusinessFunction]

_SYSTEM = """Bạn là cố vấn kinh doanh đa chức năng. Cho một insight ĐÃ ĐƯỢC DUYỆT, \
đề xuất hành động phù hợp cho TỪNG business function trong danh sách cố định: \
MARKETING, LEGAL, DESIGN, FINANCE, ENGINEERING, OPERATION, SALES, SUPPORT.

Với MỖI function trả relevance [0..1] — KHÔNG force action cho mọi function; \
chỉ function relevance >= {threshold} mới có candidate action. Function không liên quan \
→ recommendation null.

Với candidate action: recommendation (việc cụ thể nên làm), rationale (dựa trên \
insight + evidence, ≤2 câu), impact/effort/urgency thang 1–10, confidence [0..1]. \
KHÔNG tự tính priority — backend tính bằng công thức deterministic.

Chỉ trả JSON khớp schema."""


class ActCandidate(BaseModel):
    function: str = Field(pattern="^(" + "|".join(_FUNCTIONS) + ")$")
    relevance: float = Field(ge=0.0, le=1.0)
    recommendation: str | None = Field(default=None, max_length=1000)
    rationale: str | None = Field(default=None, max_length=1000)
    impact: int | None = Field(default=None, ge=1, le=10)
    effort: int | None = Field(default=None, ge=1, le=10)
    urgency: int | None = Field(default=None, ge=1, le=10)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ActProposalOut(BaseModel):
    functions: list[ActCandidate] = Field(min_length=1)


def priority_score(
    *, impact: int, effort: int, urgency: int, confidence: float
) -> float:
    """Công thức DETERMINISTIC §49 — weights từ config (env-tunable)."""
    s = get_settings()
    return round(
        impact * s.PRIORITY_WEIGHT_IMPACT
        + urgency * s.PRIORITY_WEIGHT_URGENCY
        + confidence * 10 * s.PRIORITY_WEIGHT_CONFIDENCE
        + (10 - effort) * s.PRIORITY_WEIGHT_EFFORT,
        3,
    )


def effective_scores(action: Action) -> tuple[int, int, int, float]:
    """Giá trị effective: human override nếu có, không thì agent (§51)."""
    return (
        action.human_impact if action.human_impact is not None else action.impact,
        action.human_effort if action.human_effort is not None else action.effort,
        action.human_urgency if action.human_urgency is not None else action.urgency,
        action.confidence,
    )


def recompute_priority(action: Action) -> float:
    impact, effort, urgency, confidence = effective_scores(action)
    action.priority_score = priority_score(
        impact=impact, effort=effort, urgency=urgency, confidence=confidence
    )
    return action.priority_score


def _insight_payload(insight: Insight) -> dict[str, Any]:
    return {
        "title": insight.title,
        "finding": insight.finding,
        "finding_confidence": insight.finding_confidence,
        "hypothesis": insight.hypothesis,
        "affected_context": insight.affected_context,
        "impact": insight.impact,
        "limitations": insight.limitations,
        "evidence": insight.evidence,
    }


def generate_actions(db: Session, insight: Insight) -> tuple[list[Action], list[str]]:
    """Sinh action portfolio cho insight ĐÃ DUYỆT — idempotent: chỉ replace
    các action 'proposed' CHƯA bị human chạm; action edited/accepted giữ nguyên.

    Returns (created_actions, skipped_functions) — skipped = relevance < threshold.
    """
    try:
        proposal = chat_structured(
            _SYSTEM.format(threshold=get_settings().ACT_RELEVANCE_THRESHOLD),
            json.dumps(_insight_payload(insight), ensure_ascii=False),
            ActProposalOut,
            call_type=LlmCallType.act_generate,
            prompt_version=PROMPT_VERSION,
        )
    except LLMStructureError:
        return [], []

    threshold = get_settings().ACT_RELEVANCE_THRESHOLD
    skipped = [c.function for c in proposal.functions if c.relevance < threshold]
    candidates = [
        c
        for c in proposal.functions
        if c.relevance >= threshold and c.recommendation
    ]

    # Idempotency: xoá action 'proposed' chưa human-touch, giữ lại cái đã edit
    existing = db.scalars(select(Action).where(Action.insight_id == insight.id)).all()
    keep = [a for a in existing if a.status in ("edited", "accepted")]
    for a in existing:
        if a.status not in ("edited", "accepted"):
            db.delete(a)
    db.flush()

    new_actions: list[Action] = []
    seen_functions = {a.function for a in keep}
    for c in candidates:
        if c.function in seen_functions or not (
            c.impact and c.effort is not None and c.urgency and c.confidence is not None
        ):
            continue
        action = Action(
            insight_id=insight.id,
            function=BusinessFunction(c.function),
            recommendation=c.recommendation,
            rationale=c.rationale or "",
            impact=c.impact,
            effort=c.effort,
            urgency=c.urgency,
            confidence=c.confidence,
            priority_score=0.0,
            status="proposed",
        )
        recompute_priority(action)
        db.add(action)
        new_actions.append(action)
        seen_functions.add(c.function)
    db.commit()
    for a in new_actions:
        db.refresh(a)
    return new_actions, skipped


def matrix_quadrant(impact: int, effort: int) -> str:
    """VoC OS §50: X=effort, Y=impact, ngưỡng 5/5."""
    high_impact = impact >= 5
    low_effort = effort <= 5
    if high_impact and low_effort:
        return "quick_wins"
    if high_impact:
        return "strategic_investments"
    if low_effort:
        return "low_priority"
    return "reconsider"
