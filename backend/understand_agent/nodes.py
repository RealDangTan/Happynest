"""UNDERSTAND graph nodes — VoC OS §60 (plan 25 Task 2).

Safety boundaries (giữ từ graph cũ + §68):
- Planner CHỈ chọn tool từ registry; params đi qua pydantic input_model —
  tool lỗi → observation, KHÔNG CRASH graph.
- Evidence whitelist: synthesizer chỉ được trích evidence_id có thật trong
  state; không evidence → limited insight.
- Budget: đếm llm_call_logs (plan/evaluate/synthesize) TRƯỚC MỖI call LLM —
  hết ngân sách → buộc synthesize.
- Stop deterministic (planner, KHÔNG tốn plan call): hết iteration/budget,
  evaluator đủ bằng chứng 2 lần liên tiếp, hoặc planner chọn lại đúng
  tool+params bước vừa chạy → synthesize ngay.
- finding vs hypothesis tách confidence (§41); edit text qua Gate #2 được
  RE-SANITIZE trước persist.
"""

import json
import logging
import re
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
from app.models.feedback import Feedback
from app.models.enums import LlmCallType, RunStatus
from app.services.llm_client import LLMStructureError, chat_structured
from app.services.presidio_service import sanitize
from understand_agent.state import UnderstandState

logger = logging.getLogger(__name__)

_STATEMENT_MAX = 12000
_PROMPT_STATEMENT_MAX = 6000
_MAX_CLUSTERS_CONTEXT = 5
_TOOL_NAMES = sorted(analytics.TOOLS.keys())
#: Evaluator xác nhận "đủ bằng chứng" đủ N lần liên tiếp → dừng điều tra, không
#: hỏi planner LLM nữa (chặn vòng plan→evaluate kéo dài dù evidence đã đủ).
_SUFFICIENT_ROUNDS_TO_STOP = 2


def _tool_catalog() -> list[dict[str, Any]]:
    """Catalog tool kèm signature params — sinh 1 lần từ registry (giảm chọn sai params)."""
    catalog = []
    for name in _TOOL_NAMES:
        spec = analytics.TOOLS[name]
        props = spec.input_model.model_json_schema().get("properties", {})
        params = {k: str(v.get("type", "any")) for k, v in props.items()}
        catalog.append({"tool": name, "description": spec.description, "params": params,
                        "input_schema": spec.input_model.model_json_schema()})
    return catalog


_TOOL_CATALOG = _tool_catalog()


def _compact_evaluations(evaluations: list[dict[str, Any]], last_n: int) -> list[dict[str, Any]]:
    keep = ("sufficient_evidence", "contradictions", "new_questions", "data_quality_warning")
    return [{k: ev.get(k) for k in keep} for ev in evaluations[-last_n:]]


def _consecutive_sufficient(evaluations: list[dict[str, Any]]) -> int:
    """Số lần 'sufficient_evidence=True' liên tiếp tính từ cuối."""
    count = 0
    for ev in reversed(evaluations):
        if ev.get("sufficient_evidence") is True:
            count += 1
        else:
            break
    return count


def _action_sig(action: dict[str, Any] | None) -> str:
    """Chữ ký canonical (tool + params) — dùng để phát hiện bước lặp lại đúng
    bước vừa chạy (cùng tool + cùng params → kết quả sẽ giống hệt, không có
    evidence mới)."""
    if not isinstance(action, dict):
        return ""
    params = action.get("params") or {}
    spec = analytics.TOOLS.get(action.get("tool"))
    if spec is not None:
        try:
            params = spec.input_model.model_validate(params).model_dump(mode="json")
        except ValueError:
            pass
    return json.dumps(
        {"tool": action.get("tool"), "params": params},
        sort_keys=True,
        ensure_ascii=False,
    )


def _opener_action(state: UnderstandState) -> dict[str, Any]:
    """Bước mở màn deterministic khi CHƯA có evidence nào.

    Model yếu có xu hướng chọn synthesize ngay ở iteration 0 → investigation
    'không điều tra' và insight rỗng. Chính sách §69 aggregate-first: mở bằng
    aggregate theo chiều dữ liệu đầu tiên của schema; nếu schema chưa có field
    nào thì get_schema (0 params, luôn chạy được)."""
    fields = (state.get("product_context") or {}).get("schema_fields") or []
    first_key = next(
        (f.get("key") for f in fields if isinstance(f, dict) and f.get("key")), None
    )
    if first_key:
        return {
            "action": "tool",
            "tool": "aggregate_feedback",
            "params": {"group_by": first_key},
            "objective": (
                f"Chưa có evidence — aggregate toàn bộ feedback theo '{first_key}' "
                "(bắt buộc ở bước đầu tiên)."
            ),
        }
    return {
        "action": "tool",
        "tool": "get_schema",
        "params": {},
        "objective": "Chưa có evidence — xem schema và coverage trước (bắt buộc ở bước đầu tiên).",
    }


def _usable_evidence(item: dict) -> bool:
    if item.get("ok") is False:
        return False
    payload = item.get("payload")
    if payload is None:  # older checkpoints and statement-only evidence
        return bool(item.get("statement"))
    if not payload:
        return False
    for key in ("samples", "matches", "rows", "dimensions", "segments", "results"):
        if key in payload and not payload[key]:
            return False
    return True


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
                    .where(
                        Cluster.id.in_(select(Feedback.cluster_id).where(Feedback.product_id == product_id)),
                        ~select(Feedback.id).where(
                            Feedback.cluster_id == Cluster.id,
                            Feedback.product_id != product_id,
                        ).exists(),
                    )
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
    """LLM chọn bước điều tra kế (§28). Stop conditions kiểm tra TRƯỚC khi tốn
    plan call — thoả điều kiện nào thì buộc synthesize NGAY không gọi LLM:

    - iteration >= UNDERSTAND_MAX_ITERATIONS;
    - LLM budget đã dùng hết (llm_call_logs plan+evaluate+synthesize);
    - evaluator xác nhận đủ bằng chứng `_SUFFICIENT_ROUNDS_TO_STOP` lần liên tiếp
      (chặn vòng plan→evaluate kéo dài vô nghĩa dù evidence đã đủ);
    """
    settings = get_settings()
    max_iter = settings.UNDERSTAND_MAX_ITERATIONS
    iteration = state.get("iteration", 0)

    # Iteration cap must work even if the DB is temporarily unavailable.
    if iteration >= max_iter:
        return {"next_action": {"action": "synthesize", "params": {},
                                "objective": f"Buộc tổng hợp: đã đạt MAX_ITERATIONS={max_iter}."}}
    with SessionLocal() as db:
        used = _llm_budget_used(db, uuid.UUID(state["run_id"]))
    budget = state.get("llm_budget", settings.UNDERSTAND_LLM_BUDGET_PER_RUN)
    evaluations = state.get("evaluations", [])[state.get("review_round_start", 0):]
    latest = evaluations[-1] if evaluations else {}

    force_reason = ""
    if iteration >= max_iter:
        force_reason = f"đã đạt MAX_ITERATIONS={max_iter}"
    elif used >= budget - 1:
        force_reason = f"đã hết LLM budget ({used}/{budget})"
    elif (state.get("evidence") and latest.get("sufficient_evidence") is True
          and not latest.get("contradictions") and not latest.get("new_questions")):
        force_reason = "đã đủ bằng chứng để trả lời câu hỏi"
    elif _consecutive_sufficient(evaluations) >= _SUFFICIENT_ROUNDS_TO_STOP:
        force_reason = (
            "evaluator xác nhận đủ bằng chứng "
            f"{_SUFFICIENT_ROUNDS_TO_STOP} lần liên tiếp"
        )
    if force_reason:
        return {
            "next_action": {
                "action": "synthesize",
                "params": {},
                "objective": f"Buộc tổng hợp: {force_reason}.",
            }
        }

    sample_action = {"action": "tool", "tool": "representative_feedback", "params": {},
                     "objective": "Tra cứu trước chưa có dữ liệu; đọc mẫu phản hồi thật của sản phẩm trước khi kết luận."}
    if (state.get("evidence") and not any(_usable_evidence(e) for e in state["evidence"])
            and not any(h.get("sig") == _action_sig(sample_action) for h in state.get("tool_history", []))):
        return {"next_action": sample_action}

    user_payload = json.dumps(
        {
            "question": state["question"],
            "review_feedback": state.get("review_feedback"),
            "trigger_type": state.get("trigger_type", "user_question"),
            "product_context": state["product_context"],
            "evidence_so_far": [
                {
                    "evidence_id": e["evidence_id"],
                    "tool": e["tool"],
                    "statement": e["statement"][:_PROMPT_STATEMENT_MAX],
                }
                for e in state.get("evidence", [])[-5:]
            ],
            "evaluations": _compact_evaluations(evaluations, 2),
            "tool_history": state.get("tool_history", [])[-5:],
            "iteration": iteration,
            "iteration_limit": max_iter,
            "available_tools": _TOOL_CATALOG,
        },
        ensure_ascii=False,
    )

    system = (
        "Bạn là điều tra viên phân tích phản hồi khách hàng. Cho câu hỏi/signal và "
        "context đã có, chọn BƯỚC TIẾP: gọi 1 tool phân tích (action='tool', chỉ "
        "định nghĩa params cho tool đó — params PHẢI khớp đúng signature trong "
        "available_tools) hoặc tổng hợp insight khi bằng chứng đã đủ "
        "(action='synthesize'). Aggregate first, drill down sau (§69). Nếu "
        "evidence_so_far đang RỖNG thì action PHẢI là 'tool' — chưa điều tra mà "
        "chưa tổng hợp là sai. KHÔNG chọn lại đúng tool+params đã chạy ngay trước "
        "đó — kết quả sẽ giống hệt. Chỉ trả JSON."
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

    if not state.get("evidence") and next_action.get("action") != "tool":
        # Chưa chạy tool nào mà đã đòi synthesize (LLM yếu hay thế) → ép mở màn
        # bằng aggregate-first; synthesize chỉ hợp lệ khi đã có evidence.
        return {"next_action": _opener_action(state)}

    if next_action.get("action") == "tool" and next_action.get("tool") not in _TOOL_NAMES:
        # Model chọn action='tool' nhưng thiếu/tên sai (quan sát thật 2026-10-23:
        # tool=None → dispatch insert evidence source_tool NULL → crash). Tự phục
        # hồi: chưa có evidence → opener; đã có → synthesize phần đã có.
        if not state.get("evidence"):
            return {"next_action": _opener_action(state)}
        return {
            "next_action": {
                "action": "synthesize",
                "params": {},
                "objective": (
                    f"Planner chọn tool không hợp lệ "
                    f"({next_action.get('tool')!r}) — tổng hợp từ evidence hiện có."
                ),
            }
        }

    if (
        next_action.get("action") == "tool"
        and any(_action_sig(next_action) == step.get("sig")
                for step in state.get("tool_history", []))
    ):
        # Planner chọn lại đúng bước vừa chạy — sẽ không có thông tin mới;
        # tổng hợp luôn thay vì quét thêm vòng plan→evaluate.
        return {
            "next_action": {
                "action": "synthesize",
                "params": {},
                "objective": "Bước kế trùng đúng bước vừa chạy — tổng hợp từ evidence hiện có.",
            }
        }
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

    # source_tool là NOT NULL — tool thiếu tên/sai (planner lỗi) vẫn phải ghi
    # được evidence để graph không crash; observation đã mang lỗi cho planner.
    safe_tool = tool_name if tool_name in analytics.TOOLS else (tool_name or "unknown")
    statement = json.dumps(result, ensure_ascii=False)[:_STATEMENT_MAX] or "no data"
    with SessionLocal() as db:
        evidence = Evidence(
            run_id=run_id,
            product_id=product_id,
            type="tool_result",
            statement=f"{safe_tool}: {statement}"[:_STATEMENT_MAX],
            payload={"tool": tool_name, "result": result, "observation": observation},
            coverage=result.get("coverage"),
            source_tool=safe_tool,
        )
        db.add(evidence)
        db.commit()
        evidence_id = str(evidence.id)

    return {
        "evidence": [
            {
                "evidence_id": evidence_id,
                "tool": safe_tool,
                "statement": f"{safe_tool}: {statement}",
                "payload": result,
                "ok": "ok" in observation,
            }
        ],
        "tool_history": [
            {
                "tool": tool_name or "unknown",
                "ok": "ok" in observation,
                "error": observation.get("error"),
                "sig": _action_sig(action),
            }
        ],
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
    if not _usable_evidence(latest):
        return {"evaluations": [{"sufficient_evidence": False,
                                 "data_quality_warning": "Bước tra cứu chưa có dữ liệu khả dụng; không suy ra rằng sản phẩm không có vấn đề."}],
                "iteration": state.get("iteration", 0) + 1}
    user_payload = json.dumps(
        {
            "question": state["question"],
            "latest_evidence": {
                "tool": latest.get("tool"),
                "statement": latest.get("statement", "")[:_PROMPT_STATEMENT_MAX],
            },
            "all_evidence_statements": [
                e["statement"][:150] for e in state.get("evidence", [])
            ],
        },
        ensure_ascii=False,
    )
    with SessionLocal() as db:
        used = _llm_budget_used(db, uuid.UUID(state["run_id"]))
    if used >= state.get("llm_budget", get_settings().UNDERSTAND_LLM_BUDGET_PER_RUN) - 1:
        return {"evaluations": [{"sufficient_evidence": False}],
                "iteration": state.get("iteration", 0) + 1}
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
        evaluation = {"sufficient_evidence": False, "supports": [], "contradictions": [], "new_questions": []}
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
    evidence = [e for e in state.get("evidence", []) if _usable_evidence(e)]
    if not evidence:
        return {"draft_insight": _limited_insight(state)}
    valid_ids = {e["evidence_id"] for e in evidence}
    user_payload = json.dumps(
        {
            "question": state["question"],
            "product_context": state["product_context"],
            "evidence": [
                {
                    "evidence_id": e["evidence_id"],
                    "tool": e["tool"],
                    "statement": e["statement"][:_PROMPT_STATEMENT_MAX],
                }
                for e in evidence
            ],
            "evaluations": _compact_evaluations(state.get("evaluations", []), 5),
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
            "Draft CHỈ từ evidence được cung cấp. title/finding là PHÁT HIỆN cụ thể "
            "đọc từ evidence — không lặp lại instructions, không diễn đạt chung "
            "chung. Mẫu phản hồi và tìm kiếm ngữ nghĩa không đại diện toàn bộ sản phẩm; "
            "không dùng chúng để khẳng định không có vấn đề/phản hồi. Nêu giới hạn mẫu "
            "và điều chưa xác minh. Chỉ trả JSON khớp schema.",
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
        # Whitelist: id bịa → loại
        draft["evidence_ids"] = [e for e in draft["evidence_ids"] if e in valid_ids]
        if not draft["evidence_ids"]:
            if not valid_ids:
                # Không còn evidence khả dụng → insight trung thực "chưa đủ
                # bằng chứng", KHÔNG persist draft rỗng/hallucinate (model yếu
                # từng echo nguyên system prompt làm title với confidence 1.0).
                draft = _limited_insight(state)
            else:
                # Toàn bộ id LLM đưa là bịa → gán toàn bộ evidence thật
                draft["evidence_ids"] = list(valid_ids)
    if all(e.get("tool") in {"representative_feedback", "semantic_search"} for e in evidence):
        if re.search(r"không có (?:phản hồi|bằng chứng|vấn đề)|no (?:user )?(?:feedback|reports|complaints|evidence)",
                     f"{draft['title']} {draft['finding']}", re.IGNORECASE):
            draft = _limited_insight(state)
        else:
            draft["finding_confidence"] = min(draft["finding_confidence"], .7)
        draft.setdefault("limitations", []).append("Chỉ dựa trên mẫu phản hồi đã đọc; chưa đại diện toàn bộ sản phẩm.")
    return {"draft_insight": draft}


def _limited_insight(state: UnderstandState) -> dict[str, Any]:
    """VoC OS §60 generate_limited_insight — không đủ evidence → nói thẳng."""
    return {
        "title": f"Không đủ bằng chứng: {state['question'][:180]}",
        "finding": "Không thu thập đủ evidence để trả lời câu hỏi trong giới hạn "
        "iteration/budget. Các bước đã thử: "
        + ", ".join(
            h.get("tool", "?") if isinstance(h, dict) else str(h)
            for h in state.get("tool_history", [])[-6:]
        ),
        "finding_confidence": 0.3,
        "hypothesis_statement": None,
        "hypothesis_confidence": None,
        "affected_context": {},
        "impact": [],
        "limitations": ["Investigation dừng sớm — kết luận tạm thời, cần thêm dữ liệu."],
        "evidence_ids": [e["evidence_id"] for e in state.get("evidence", []) if _usable_evidence(e)][-5:],
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
        if e["evidence_id"] in draft.get("evidence_ids", [])
    ]
    # LẦN ĐẦU: raise GraphInterrupt TẠI ĐÂY; lần resume: interrupt() trả payload.
    decision = interrupt(
        {
            "insight_id": insight_id,
            "insight": draft,
            "evidence": evidence_summaries,
            "options": ["approve", "edit", "investigate_more", "reject"],
            "question": state.get("question"),
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
            if action != "investigate_more":
                run = db.get(AnalysisRun, uuid.UUID(state["run_id"]))
                if run is not None:
                    run.status = RunStatus.completed
                    run.processed_count = 1
                    run.completed_at = datetime.now(timezone.utc)
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
            "review_round_start": len(state.get("evaluations", [])),
            "review_feedback": decision.get("reason"),
        }
    return {"final_status": final_status}
