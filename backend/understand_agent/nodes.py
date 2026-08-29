"""UNDERSTAND graph nodes — VoC OS §60 (plan 25 Task 2).

Safety boundaries (giữ từ graph cũ + §68):
- Planner CHỈ chọn tool từ registry; params đi qua pydantic input_model —
  tool lỗi → observation, KHÔNG CRASH graph.
- Evidence whitelist: synthesizer chỉ được trích evidence_id có thật trong
  state; không evidence → limited insight.
- Budget: đếm llm_call_logs (plan/evaluate/synthesize) TRƯỚC MỖI call LLM —
  hết ngân sách → buộc synthesize.
- finding vs hypothesis tách confidence (§41); edit text qua Gate #2 được
  RE-SANITIZE trước persist.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from langgraph.types import interrupt
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics import tools as analytics
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.analysis_run import AnalysisRun
from app.models.cluster import Cluster
from app.models.evidence import Evidence
from app.models.enums import LlmCallType
from app.services.llm_client import LLMStructureError, chat_structured
from app.services.presidio_service import sanitize
from understand_agent.state import UnderstandState

logger = logging.getLogger(__name__)

_STATEMENT_MAX = 300
_MAX_CLUSTERS_CONTEXT = 5
_TOOL_NAMES = sorted(analytics.TOOLS.keys())


def _llm_budget_used(db: Session, run_id: uuid.UUID) -> int:
    from app.models.llm_call_log import LlmCallLog

    return int(
        db.scalar(
            select(func.count())
            .select_from(LlmCallLog)
            .where(
                LlmCallLog.analysis_run_id == run_id,
                LlmCallLog.call_type.in_(
                    (LlmCallType.plan, LlmCallType.evaluate, LlmCallType.synthesize)
                ),
            )
        )
        or 0
    )


# ---------------------------------------------------------------- load context


def load_context(state: UnderstandState) -> dict[str, Any]:
    """Deterministic: product + schema + coverage + taxonomy + clusters (§27)."""
    from app.services import schema_registry, taxonomy_service
    from app.services.coverage import field_coverage
    from app.models.product import Product

    product_id = uuid.UUID(state["product_id"])
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        active = schema_registry.get_active_schema(db, product_id)
        context = {
            "product_name": product.name if product else "unknown",
            "schema_fields": schema_registry.schema_fields(active),
            "coverage": field_coverage(db, product_id),
            "taxonomy": taxonomy_service.get_taxonomy_names(db, product_id),
            "clusters": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "feedback_count": c.feedback_count,
                    "growth_ratio": c.growth_ratio,
                    "is_emerging": c.is_emerging,
                    "is_spike": c.is_spike,
                    "suggested_priority": c.suggested_priority,
                }
                for c in db.scalars(
                    select(Cluster)
                    .order_by(Cluster.suggested_priority.desc().nullslast())
                    .limit(_MAX_CLUSTERS_CONTEXT)
                ).all()
            ],
        }
    return {"product_context": context, "iteration": 0}


# -------------------------------------------------------------------- planner


class PlannerOut(BaseModel):
    """Next step do LLM chọn — action tool (tool + params) hoặc synthesize."""

    action: str = Field(pattern="^(tool|synthesize)$")
    tool: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    objective: str = Field(max_length=300)


def planner(state: UnderstandState) -> dict[str, Any]:
    """LLM chọn bước điều tra kế (§28). Hết iteration/budget → synthesize."""
    settings = get_settings()
    max_iter = settings.UNDERSTAND_MAX_ITERATIONS
    iteration = state.get("iteration", 0)

    force = ""
    with SessionLocal() as db:
        used = _llm_budget_used(db, uuid.UUID(state["run_id"]))
    budget = state.get("llm_budget", settings.UNDERSTAND_LLM_BUDGET_PER_RUN)
    if iteration >= max_iter:
        force = f"Đã đạt MAX_ITERATIONS={max_iter} — buộc synthesize."
    elif used >= budget:
        force = f"Đã hết LLM budget ({used}/{budget}) — buộc synthesize."

    user_payload = json.dumps(
        {
            "question": state["question"],
            "trigger_type": state.get("trigger_type", "user_question"),
            "product_context": state["product_context"],
            "evidence_so_far": [
                {"evidence_id": e["evidence_id"], "tool": e["tool"], "statement": e["statement"]}
                for e in state.get("evidence", [])
            ],
            "evaluations": state.get("evaluations", [])[-3:],
            "tool_history": state.get("tool_history", []),
            "iteration": iteration,
            "available_tools": _TOOL_NAMES,
            "force": force,
        },
        ensure_ascii=False,
    )

    system = (
        "Bạn là điều tra viên phân tích phản hồi khách hàng. Cho câu hỏi/signal và "
        "context đã có, chọn BƯỚC TIẾP: gọi 1 tool phân tích (action='tool', chỉ "
        "định nghĩa params cho tool đó) hoặc tổng hợp insight khi bằng chứng đã đủ "
        "(action='synthesize'). Aggregate first, drill down sau (§69). Chỉ trả JSON."
    )
    try:
        out = chat_structured(
            system,
            user_payload,
            PlannerOut,
            call_type=LlmCallType.plan,
            prompt_version="understand-v1",
            analysis_run_id=uuid.UUID(state["run_id"]),
        )
        next_action = out.model_dump()
    except LLMStructureError:
        # LLM fail → synthesize luôn nếu có evidence, không thì kết thúc sạch
        next_action = {"action": "synthesize", "params": {}, "objective": "fallback"}
    if force:
        next_action["action"] = "synthesize"
    return {"next_action": next_action}


# ------------------------------------------------------------------- dispatch


def dispatch(state: UnderstandState) -> dict[str, Any]:
    """Chạy tool từ registry + GHI evidence row (§38). Tool lỗi → observation."""
    action = state["next_action"] or {}
    tool_name = action.get("tool")
    run_id = uuid.UUID(state["run_id"])
    product_id = uuid.UUID(state["product_id"])

    if tool_name not in analytics.TOOLS:
        observation = {"error": f"tool '{tool_name}' không tồn tại."}
        result: dict[str, Any] = {}
    else:
        spec = analytics.TOOLS[tool_name]
        try:
            with SessionLocal() as tool_db:
                result = spec(tool_db, product_id, action.get("params", {}))
            observation = {"ok": True}
        except Exception as exc:  # noqa: BLE001 — tool fail không được crash graph
            logger.warning("tool %s fail: %s", tool_name, type(exc).__name__)
            result = {}
            observation = {"error": f"{type(exc).__name__}: {exc}"[:300]}

    statement = json.dumps(result, ensure_ascii=False)[:_STATEMENT_MAX] or "no data"
    with SessionLocal() as db:
        evidence = Evidence(
            run_id=run_id,
            product_id=product_id,
            type="tool_result",
            statement=f"{tool_name}: {statement}"[:_STATEMENT_MAX],
            payload={"tool": tool_name, "result": result, "observation": observation},
            coverage=result.get("coverage"),
            source_tool=tool_name,
        )
        db.add(evidence)
        db.commit()
        evidence_id = str(evidence.id)

    return {
        "evidence": [
            {
                "evidence_id": evidence_id,
                "tool": tool_name,
                "statement": f"{tool_name}: {statement}",
                "payload": result,
            }
        ],
        "tool_history": [tool_name or "unknown"],
    }


# ------------------------------------------------------------------ evaluator


class EvaluateOut(BaseModel):
    supports: list[dict[str, Any]] = Field(default_factory=list)  # {hypothesis, strength, evidence_ids}
    contradictions: list[str] = Field(default_factory=list)
    new_questions: list[str] = Field(default_factory=list)
    data_quality_warning: str | None = None
    sufficient_evidence: bool


def evaluator(state: UnderstandState) -> dict[str, Any]:
    """LLM đánh giá evidence mới nhất (§39) — lưu vào state.evaluations."""
    latest = (state.get("evidence") or [{}])[-1]
    user_payload = json.dumps(
        {
            "question": state["question"],
            "latest_evidence": latest,
            "all_evidence_statements": [
                e["statement"] for e in state.get("evidence", [])
            ],
        },
        ensure_ascii=False,
    )
    try:
        out = chat_structured(
            "Bạn là điều tra viên khách quan. Đánh giá evidence mới nhất: có hỗ trợ "
            "giả thuyết nào, mâu thuẫn gì, câu hỏi mới nào nảy sinh, dữ liệu có vấn "
            "đề chất lượng không, và bằng chứng đã ĐỦ để trả lời câu hỏi chưa (§39). "
            "Chỉ trả JSON.",
            user_payload,
            EvaluateOut,
            call_type=LlmCallType.evaluate,
            prompt_version="understand-v1",
            analysis_run_id=uuid.UUID(state["run_id"]),
        )
        evaluation = out.model_dump()
    except LLMStructureError:
        evaluation = {"sufficient_evidence": True, "supports": [], "contradictions": [], "new_questions": []}
    return {
        "evaluations": [evaluation],
        "iteration": state.get("iteration", 0) + 1,
    }


# ---------------------------------------------------------------- synthesizer


class InsightDraft(BaseModel):
    title: str = Field(max_length=255)
    finding: str = Field(max_length=2000)
    finding_confidence: float = Field(ge=0.0, le=1.0)
    hypothesis_statement: str | None = Field(default=None, max_length=1000)
    hypothesis_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    affected_context: dict[str, Any] = Field(default_factory=dict)
    impact: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(min_length=1)


def synthesizer(state: UnderstandState) -> dict[str, Any]:
    """Tổng hợp insight draft — evidence whitelist server-side (§38/§42)."""
    valid_ids = {e["evidence_id"] for e in state.get("evidence", [])}
    user_payload = json.dumps(
        {
            "question": state["question"],
            "product_context": state["product_context"],
            "evidence": state.get("evidence", []),
            "evaluations": state.get("evaluations", []),
            "rules": [
                "finding = fact có evidence; hypothesis = suy luận, KHÔNG trình bày như root cause xác nhận (§41).",
                "evidence_ids CHỈ được dùng id có trong danh sách evidence.",
                "limitations phải nêu coverage thấp nếu có (§42).",
            ],
        },
        ensure_ascii=False,
    )
    try:
        out = chat_structured(
            "Tổng hợp evidence-grounded insight cho người quyết định (VoC OS §42). "
            "Draft CHỈ từ evidence được cung cấp. Chỉ trả JSON khớp schema.",
            user_payload,
            InsightDraft,
            call_type=LlmCallType.synthesize,
            prompt_version="understand-v1",
            analysis_run_id=uuid.UUID(state["run_id"]),
        )
        draft = out.model_dump()
    except LLMStructureError:
        draft = None

    if draft is None:
        draft = _limited_insight(state)
    else:
        # Whitelist + fallback: id bịa → loại; rỗng → gán toàn bộ evidence
        draft["evidence_ids"] = [e for e in draft["evidence_ids"] if e in valid_ids]
        if not draft["evidence_ids"]:
            draft["evidence_ids"] = list(valid_ids)
    return {"draft_insight": draft}


def _limited_insight(state: UnderstandState) -> dict[str, Any]:
    """VoC OS §60 generate_limited_insight — không đủ evidence → nói thẳng."""
    return {
        "title": f"Không đủ bằng chứng: {state['question'][:180]}",
        "finding": "Không thu thập đủ evidence để trả lời câu hỏi trong giới hạn "
        "iteration/budget. Các bước đã thử: "
        + ", ".join(state.get("tool_history", [])[-6:]),
        "finding_confidence": 0.3,
        "hypothesis_statement": None,
        "hypothesis_confidence": None,
        "affected_context": {},
        "impact": [],
        "limitations": ["Investigation dừng sớm — kết luận tạm thời, cần thêm dữ liệu."],
        "evidence_ids": [e["evidence_id"] for e in state.get("evidence", [])][-5:],
    }


# ---------------------------------------------------------------- persist + HITL


def persist_insight(state: UnderstandState) -> dict[str, Any]:
    """INSERT insight status=pending + interrupt Gate #2 (payload cho human).

    Node chạy LẠI từ đầu khi resume (LangGraph semantics) — persist idempotent
    theo (run_id, title): row đã tồn tại thì tái dùng, KHÔNG INSERT lần 2.
    """
    draft = state["draft_insight"] or {}
    run_id = uuid.UUID(state["run_id"])
    with SessionLocal() as db:
        from app.models.insight import Insight

        insight = db.scalars(
            select(Insight).where(
                Insight.run_id == run_id, Insight.title == draft["title"]
            )
        ).first()
        if insight is None:
            insight = Insight_(
                db,
                draft,
                run_id=run_id,
                product_id=uuid.UUID(state["product_id"]),
            )
            db.add(insight)
            db.commit()
            db.refresh(insight)
        insight_id = str(insight.id)

    evidence_summaries = [
        {"evidence_id": e["evidence_id"], "statement": e["statement"]}
        for e in state.get("evidence", [])
    ]
    # LẦN ĐẦU: raise GraphInterrupt TẠI ĐÂY; lần resume: interrupt() trả payload.
    decision = interrupt(
        {
            "insight_id": insight_id,
            "insight": draft,
            "evidence": evidence_summaries,
            "options": ["approve", "edit", "investigate_more", "reject"],
        }
    )
    return {"decision": dict(decision), "insights_created": [insight_id]}


def Insight_(db: Session, draft: dict, *, run_id: uuid.UUID, product_id: uuid.UUID):
    from app.models.insight import Insight

    return Insight(
        product_id=product_id,
        run_id=run_id,
        title=draft["title"],
        finding=draft["finding"],
        finding_confidence=draft["finding_confidence"],
        hypothesis=(
            {
                "statement": draft.get("hypothesis_statement"),
                "confidence": draft.get("hypothesis_confidence"),
            }
            if draft.get("hypothesis_statement")
            else None
        ),
        affected_context=draft.get("affected_context", {}),
        impact=draft.get("impact", []),
        limitations=draft.get("limitations", []),
        evidence=draft.get("evidence_ids", []),
        status="pending",
    )


def apply_decision(state: UnderstandState) -> dict[str, Any]:
    """Gate #2: approve | edit (re-sanitize) | investigate_more | reject (§43)."""
    decision = state.get("decision") or {}
    action = decision.get("action")
    insight_id = uuid.UUID(state["insights_created"][-1])
    from app.models.enums import InsightReviewAction
    from app.models.insight import Insight
    from app.models.insight_review import InsightReview

    original = {k: (state.get("draft_insight") or {}).get(k) for k in
                ("title", "finding", "finding_confidence", "hypothesis_statement",
                 "hypothesis_confidence", "affected_context", "impact", "limitations",
                 "evidence_ids")}

    final_status = {
        "approve": "approved",
        "edit": "edited",
        "reject": "rejected",
        "investigate_more": "investigating",
    }.get(action, "approved")

    edited_value = None
    with SessionLocal() as db:
        insight = db.get(Insight, insight_id)
        if insight is not None:
            if action == "edit":
                edited = decision.get("edited_insight") or {}
                # RE-SANITIZE text human gõ trước persist (PII boundary)
                new_title = edited.get("title") or insight.title
                new_finding = edited.get("finding") or insight.finding
                s_title = sanitize(str(new_title))
                s_finding = sanitize(str(new_finding))
                insight.title = s_title.sanitized_text or insight.title
                insight.finding = s_finding.sanitized_text or insight.finding
                edited_value = {"title": insight.title, "finding": insight.finding}
            insight.status = final_status

            reviewer_id = uuid.UUID(decision["reviewer_id"])
            db.add(
                InsightReview(
                    insight_id=insight_id,
                    original_value=original,
                    edited_value=edited_value,
                    action=InsightReviewAction(action),
                    reason=decision.get("reason"),
                    reviewer_id=reviewer_id,
                )
            )
            db.commit()

            # Decision memory (§52–53, plan 27) — agent draft vs human quyết
            from app.models.enums import DecisionSubject
            from app.services.decision_log import log_decision

            log_decision(
                db,
                product_id=insight.product_id,
                subject_type=DecisionSubject.insight,
                subject_id=insight_id,
                agent_value=original,
                human_value={
                    "action": action,
                    "edited_insight": decision.get("edited_insight"),
                },
                reason=decision.get("reason"),
                reviewer_id=reviewer_id,
            )

    if action == "investigate_more":
        # quay lại planner với feedback — clear draft, tăng iteration
        return {
            "final_status": final_status,
            "draft_insight": None,
            "iteration": state.get("iteration", 0) + 1,
            "next_action": None,
        }
    return {"final_status": final_status}
