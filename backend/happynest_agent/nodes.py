"""Nodes của agent graph fully LLM-routed (phase 19 Task 2).

Luồng: assess → route → dispatch → assess → … → synthesize → critic →
persist_insight → risk_gate → auto_finalize | await_approval → apply_decision.

Biên an toàn chốt cứng plan §2:
- AGENT_MAX_STEPS — conditional edge ép về nhánh finish khi vượt;
- AGENT_LLM_BUDGET_PER_RUN — guard TRƯỚC MỌI call tốn LLM qua
  ``_llm_calls_used`` (COUNT llm_call_logs theo run);
- Router chỉ chọn được tên trong TOOLS() — Literal chặn từ Pydantic.

PII boundary: mọi payload prompt dùng metrics/quotes/precedents từ
sanitized_content; raw_content không bao giờ xuất hiện.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Literal

from langgraph.types import interrupt
from openai import APIError
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.action_draft import ActionDraft
from app.models.cluster import Cluster
from app.models.enums import (
    DraftKind,
    LlmCallType,
    ReviewAction,
    ReviewStatus,
)
from app.models.feedback import Feedback
from app.models.insight import Insight
from app.models.insight_review import InsightReview
from app.services.embedder import EmbeddingDimError, embed_one, store_embedding
from app.services.llm_client import chat_structured
from happynest_agent.state import AgentState
from happynest_agent.tools import EXECUTORS, TOOLS

logger = logging.getLogger(__name__)

#: Registry dựng 1 lần khi import — các module tool không vòng phụ thuộc ngược.
TOOLS_REG = TOOLS()
EXECUTORS_REG = EXECUTORS()

#: call types tính vào ngân sách LLM mỗi run (plan §2 danh sách khóa)
_BUDGET_CALL_TYPES = (
    "classify",
    "embed",
    "name_cluster",
    "generate_insight",
    "route",
    "critic",
)

# --- Schemas cho structured output ------------------------------------------


class RouteDecision(BaseModel):
    """Router CHỈ được chọn tên tool nằm trong registry + 2 nhánh kết."""

    next: Literal[
        "classify_batch",
        "embed_batch",
        "get_cluster_metrics",
        "fetch_evidence_quotes",
        "retrieve_similar_insights",
        "synthesize",
        "finish",
    ]
    rationale: str = Field(max_length=200)


class InsightDraft(BaseModel):
    title: str = Field(max_length=120)
    summary: str = Field(max_length=600)
    suggested_action: str = Field(max_length=400)
    evidence_feedback_ids: list[uuid.UUID] = Field(default_factory=list)


# --- Helpers -----------------------------------------------------------------


def _llm_calls_used(db: Session, run_id: uuid.UUID) -> int:
    placeholders = ", ".join(f":t{i}" for i in range(len(_BUDGET_CALL_TYPES)))
    params: dict[str, Any] = {"rid": str(run_id)}
    for i, t in enumerate(_BUDGET_CALL_TYPES):
        params[f"t{i}"] = t
    return int(
        db.execute(
            text(
                f"SELECT count(*) FROM llm_call_logs "
                f"WHERE analysis_run_id = :rid "
                f"AND call_type IN ({placeholders})"
            ),
            params,
        ).scalar_one()
    )


def _budget_left(db: Session, run_id: uuid.UUID) -> int:
    return get_settings().AGENT_LLM_BUDGET_PER_RUN - _llm_calls_used(db, run_id)


def _cluster_members(db: Session, cluster_id: uuid.UUID) -> list[uuid.UUID]:
    """Whitelist member cụm — evidence ids ngoài list này bị lọc (plan §2.4)."""
    return list(
        db.scalars(
            select(Feedback.id).where(Feedback.cluster_id == cluster_id)
        ).all()
    )


def _obs_digest(state: AgentState, cap_per_obs: int = 160, tail: int = 6) -> str:
    """Digest NGẮN từ observations thô — dữ liệu phái sinh, KHÔNG lưu vào state
    (nguyên tắc LangGraph "keep state raw": node tự format prompt của mình)."""
    lines = [
        f"- {o.get('tool', '?')}: {_obs_summary(o.get('output_summary') or o.get('error'), cap_per_obs)}"
        for o in state.get("observations", [])
        if o.get("tool")
    ]
    return "\n".join(lines[-tail:])


def _obs_summary(value: Any, cap: int = 500) -> str:
    try:
        s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        s = str(value)
    return s[:cap]


def _evidence_of(state: AgentState) -> dict[str, Any]:
    key = str(state.get("current_cluster"))
    return state.get("evidence", {}).get(key, {})


def _draft_templates(
    run_id: uuid.UUID, title: str, summary: str, suggested_action: str
) -> list[dict[str, str]]:
    """Khuôn tiếng Việt fill cứng — auto path KHÔNG tốn LLM (plan §2.7)."""
    ticket = (
        f"[Happynest][Insight] {title}\n\n"
        f"Mô tả: {summary}\n\n"
        f"Hành động đề xuất: {suggested_action}\n\n"
        f"(Sinh tự động bởi agent run {run_id} — vui lòng xác nhận trước xử lý.)"
    )
    slack = (
        f":clipboard: *{title}*\n{summary[:200]}\n"
        f"> Đề xuất: {suggested_action[:150]}"
    )
    return [
        {"kind": DraftKind.draft_ticket.value, "body": ticket},
        {"kind": DraftKind.slack_message.value, "body": slack},
    ]


def _pop_target(state: AgentState) -> dict[str, Any]:
    targets = list(state.get("targets", []))
    cur = state.get("current_cluster")
    if cur is not None and cur in targets:
        targets.remove(cur)
    return {
        "targets": targets,
        "current_cluster": None,
        "insight_draft": None,
        "critic_failed_once": False,
        "critic_result": None,
        "risk_level": None,
    }


def _safe_embed(text_to_embed: str) -> list[float] | None:
    """Embed với degrade an toàn — lỗi API/dim trả None (backfill script bù sau),
    không làm chết run giữa chừng."""
    try:
        return embed_one(text_to_embed)
    except (EmbeddingDimError, APIError) as exc:
        logger.warning("agent embed fail (sẽ backfill): %s: %s", type(exc).__name__, exc)
        return None


# --- Nodes -------------------------------------------------------------------


def assess(state: AgentState) -> dict[str, Any]:
    """Chọn target kế tiếp; reset tín hiệu vòng critic/risk của cụm trước."""
    targets = state.get("targets", [])
    updates: dict[str, Any] = {"critic_result": None, "risk_level": None}
    updates["current_cluster"] = targets[0] if targets else None
    return updates


def route(state: AgentState) -> dict[str, Any]:
    """LLM router temperature=0 — MỖI BƯỚC một quyết định. Guard budget trước
    khi gọi; hết ngân sách → finish cứng không tốn call."""
    settings = get_settings()
    with SessionLocal() as db:
        if _budget_left(db, state["run_id"]) <= 0:
            return {
                "route_decision": {
                    "next": "finish",
                    "rationale": "budget exhausted",
                }
            }

        specs = [
            {"name": name, "description": spec.description}
            for name, spec in sorted(TOOLS_REG.items())
        ]
        system = (
            "You are the router of a feedback-analysis agent. Each step choose "
            "exactly one next action. Gather cluster metrics and evidence "
            "quotes first, then precedents, then synthesize when enough "
            "evidence exists for the current cluster. Choose 'finish' only "
            "when all target clusters are done or no useful action remains."
        )
        user = (
            f"Current cluster: {state.get('current_cluster')}\n"
            f"Remaining clusters after this one: {len(state.get('targets', [])) - 1}\n"
            f"Steps used: {state.get('steps_used')}/{settings.AGENT_MAX_STEPS}\n\n"
            f"Recent observations:\n{_obs_digest(state) or '(none yet)'}\n\n"
            f"Available actions:\n"
            + "\n".join(f"- {s['name']}: {s['description']}" for s in specs)
            + "\n- synthesize: draft an insight from gathered evidence\n"
            "- finish: end the run now\n\n"
            "Reply with JSON {next, rationale}."
        )
        decision = chat_structured(
            system,
            user,
            RouteDecision,
            call_type=LlmCallType.route,
            prompt_version=settings.PROMPT_VERSION,
            analysis_run_id=state["run_id"],
        )
        return {"route_decision": decision.model_dump()}


def dispatch(state: AgentState) -> dict[str, Any]:
    """Thực thi tool router chọn; lỗi tool thành observation rồi QUAY LẠI route
    (conditional edge đọc obs cuối). Tăng steps_used."""
    decision = state.get("route_decision") or {}
    tool_name = decision.get("next")
    run_id = state["run_id"]

    with SessionLocal() as db:
        try:
            executor = EXECUTORS_REG[tool_name]
            input_model = TOOLS_REG[tool_name].input_model
        except KeyError:
            return {
                "steps_used": state.get("steps_used", 0) + 1,
                "observations": [
                    {"tool": tool_name, "error": "unknown tool (không nằm trong registry)"}
                ],
            }

        # Fill tham số từ context — router KHÔNG tự đẻ tham số.
        kwargs: dict[str, Any] = {"run_id": run_id}
        if tool_name in ("get_cluster_metrics", "fetch_evidence_quotes"):
            kwargs["cluster_id"] = state["current_cluster"]
        elif tool_name == "retrieve_similar_insights":
            cluster = db.get(Cluster, state["current_cluster"])
            kwargs["query_text"] = f"{cluster.name}. {cluster.summary}" if cluster else "cluster"

        try:
            result = executor(db, input_model(**kwargs))
            data = json.loads(result.model_dump_json())
            obs = {
                "tool": tool_name,
                "input_summary": _obs_summary(kwargs, 120),
                "output_summary": _obs_summary(data),
            }
        except Exception as exc:  # noqa: BLE001 - lỗi tool là observation, không crash
            db.rollback()
            obs = {"tool": tool_name, "error": f"{type(exc).__name__}: {exc}"[:500]}
            return {
                "steps_used": state.get("steps_used", 0) + 1,
                "observations": [obs],
            }

        # Lưu evidence theo cluster để synthesize/risk_gate dùng lại (raw data).
        ev_key = str(state["current_cluster"])
        evidence = dict(state.get("evidence", {}))
        bucket = dict(evidence.get(ev_key, {}))
        if tool_name == "get_cluster_metrics":
            bucket["metrics"] = data
        elif tool_name == "fetch_evidence_quotes":
            bucket["quotes"] = data.get("quotes", [])
        elif tool_name == "retrieve_similar_insights":
            bucket["precedents"] = data.get("matches", [])
        evidence[ev_key] = bucket

        return {
            "steps_used": state.get("steps_used", 0) + 1,
            "observations": [obs],
            "evidence": evidence,
        }


def synthesize(state: AgentState) -> dict[str, Any]:
    """1 call generate_insight → draft; validate server-side evidence whitelist."""
    settings = get_settings()
    ev = _evidence_of(state)
    with SessionLocal() as db:
        members = set(_cluster_members(db, state["current_cluster"]))
        user_payload = {
            "metrics": ev.get("metrics"),
            "quotes": ev.get("quotes", []),
            "precedents": ev.get("precedents", []),
            "member_count_hint": len(members),
        }
        system = (
            "You synthesize customer-feedback insights. Use ONLY provided "
            "metrics/quotes/precedents. Reply JSON {title<=120 chars, summary"
            "<=600, suggested_action<=400, evidence_feedback_ids[] drawn from "
            "quote feedback_ids}."
        )
        draft = chat_structured(
            system,
            _obs_summary(user_payload, 8000),
            InsightDraft,
            call_type=LlmCallType.generate_insight,
            prompt_version=settings.PROMPT_VERSION,
            analysis_run_id=state["run_id"],
        )
        data = draft.model_dump()
        # whitelist + cap ≤5 (nguyên tắc plan 15 Task 2.4)
        data["evidence_feedback_ids"] = [
            fid for fid in data["evidence_feedback_ids"] if fid in members
        ][:5]
        return {"insight_draft": data}


def _checklist(state: AgentState) -> list[str]:
    """Deterministic checklist — trả danh sách deficit (rỗng = pass)."""
    draft = state.get("insight_draft") or {}
    problems: list[str] = []
    with SessionLocal() as db:
        members = set(_cluster_members(db, state["current_cluster"]))
    if not any(fid in members for fid in draft.get("evidence_feedback_ids", [])):
        problems.append("no valid evidence id thuộc cụm")
    if not (draft.get("title") or "").strip():
        problems.append("title rỗng")
    if not (draft.get("summary") or "").strip():
        problems.append("summary rỗng")
    if not (draft.get("suggested_action") or "").strip():
        problems.append("suggested_action rỗng")
    if "precedents" not in _evidence_of(state):
        problems.append("chưa tra precedent nào (memory tổ chức)")
    return problems


def critic(state: AgentState) -> dict[str, Any]:
    """Checklist deterministic + đúng 1 lần reflection LLM. Fail ×2 → bỏ cụm.

    Trả critic_result: "pass" | "drop" | None (= vừa reflection xong, graph
    điều hướng sang node ``critic_recheck`` kiểm tra lần 2 thuần code).
    """
    settings = get_settings()
    problems = _checklist(state)
    if not problems:
        return {"critic_result": "pass"}
    if state.get("critic_failed_once"):
        # lần 2 vẫn fail → bỏ cụm này, không persist insight yếu
        updates = _pop_target(state)
        updates["observations"] = [
            {
                "tool": "critic",
                "output_summary": f"BỎ cụm {state.get('current_cluster')}: "
                f"fail checklist lần 2 ({'; '.join(problems)})",
            }
        ]
        updates["critic_result"] = "drop"
        return updates

    # đúng 1 lần reflection
    with SessionLocal() as db:
        if _budget_left(db, state["run_id"]) <= 0:
            updates = _pop_target(state)
            updates["observations"] = [
                {"tool": "critic", "output_summary": "BỎ cụm — budget cạn trước reflection"}
            ]
            updates["critic_result"] = "drop"
            return updates
        revised = chat_structured(
            "You are a strict critic. Fix the insight draft to satisfy this "
            "checklist. Reply the same JSON schema.",
            f"Deficits: {problems}\nDraft: {_obs_summary(state.get('insight_draft'), 3000)}\n"
            f"Evidence: {_obs_summary(_evidence_of(state), 4000)}",
            InsightDraft,
            call_type=LlmCallType.critic,
            prompt_version=settings.PROMPT_VERSION,
            analysis_run_id=state["run_id"],
        )
        return {
            "insight_draft": revised.model_dump(),
            "critic_failed_once": True,
            "critic_result": None,  # nhánh conditional sẽ đi critic_recheck
        }


def critic_recheck(state: AgentState) -> dict[str, Any]:
    """Kiểm tra lần 2 sau reflection — node thuần code tách để conditional rõ."""
    if not _checklist(state):
        return {"critic_result": "pass"}
    updates = _pop_target(state)
    updates["observations"] = [
        {"tool": "critic", "output_summary": "BỎ cụm — fail checklist lần 2 sau reflection"}
    ]
    updates["critic_result"] = "drop"
    return updates


def persist_insight(state: AgentState) -> dict[str, Any]:
    """INSERT Insight review_status=pending (+embedding nếu còn budget) trong 1 tx;
    tính risk_level ngay tại đây cho risk_gate đọc (thuần rule, xem _escalate)."""
    draft = state["insight_draft"]
    settings = get_settings()
    with SessionLocal() as db:
        ins = Insight(
            cluster_id=state["current_cluster"],
            title=draft["title"],
            summary=draft["summary"],
            suggested_action=draft["suggested_action"],
            evidence_ids=[str(fid) for fid in draft["evidence_feedback_ids"]],
            review_status=ReviewStatus.pending,
        )
        db.add(ins)
        db.flush()

        if _budget_left(db, state["run_id"]) > 0:
            vec = _safe_embed(f"{draft['title']}. {draft['summary']}")
            if vec is not None:
                store_embedding(db, ins, vec)
        else:
            logger.warning(
                "agent %s: budget cạn — insight lưu KHÔNG embedding (backfill sau)",
                state["run_id"],
            )

        db.commit()

        metrics = _evidence_of(state).get("metrics", {})
        risk_level = _escalate(metrics, _high_critical_share(metrics))
        return {
            "insights_created": [ins.id],
            "risk_level": risk_level,
            "insight_draft": {**draft, "id": str(ins.id)},
        }


def _high_critical_share(metrics: dict[str, Any]) -> float:
    dist = metrics.get("severity_dist") or {}
    total = sum(dist.values()) or 1
    return (dist.get("high", 0) + dist.get("critical", 0)) / total


def _escalate(metrics: dict[str, Any], share_hc: float) -> str:
    """Risk gate THUẦN RULE (plan §2.7) — không LLM phán rủi ro."""
    s = get_settings()
    priority = metrics.get("suggested_priority") or 0.0
    if priority >= s.AGENT_RISK_PRIORITY_THRESHOLD:
        return "high"
    if share_hc >= s.AGENT_RISK_SEVERITY_SHARE:
        return "high"
    if metrics.get("is_emerging") and metrics.get("is_spike"):
        return "high"
    return "low"


def finalize_no_insight(state: AgentState) -> dict[str, Any]:
    """Nhánh finish-sớm — chỉ đánh dấu, đóng run ở runner job."""
    return {"observations": [{"tool": "finalize", "output_summary": "run kết thúc sớm"}]}


def risk_gate(state: AgentState) -> dict[str, Any]:
    """Đã tính risk_level trong persist_insight — node giữ làm điểm neo edge."""
    level = state.get("risk_level") or "low"
    return {"risk_level": level}


def auto_finalize(state: AgentState) -> dict[str, Any]:
    """Rủi ro thấp: drafts template + status approved, KHÔNG insight_reviews
    (marker KPI phase 20 phân biệt auto/HITL nhờ vắng row này)."""
    draft = state.get("insight_draft") or {}
    with SessionLocal() as db:
        ins = db.get(Insight, uuid.UUID(draft["id"]))
        ins.review_status = ReviewStatus.approved
        for tpl in _draft_templates(
            state["run_id"], draft["title"], draft["summary"], draft["suggested_action"]
        ):
            db.add(ActionDraft(insight_id=ins.id, kind=tpl["kind"], body=tpl["body"]))
        db.commit()
    updates = _pop_target(state)
    updates["observations"] = [
        {"tool": "auto_finalize", "output_summary": f"auto-approved insight {draft['id']}"}
    ]
    return updates


def await_approval(state: AgentState) -> dict[str, Any]:
    """Rủi ro cao: interrupt() — payload chỉ chứa dữ liệu đã sanitize.
    Resume value (payload POST /runs/{id}/decision) trở thành ``decision``."""
    draft = state.get("insight_draft") or {}
    ev = _evidence_of(state)
    resume: dict[str, Any] = interrupt(  # type: ignore[misc]
        {
            "insight": draft,
            "quotes": ev.get("quotes", []),
            "metrics": ev.get("metrics"),
            "precedents": ev.get("precedents", []),
            "options": ["approve", "edit", "reject"],
        }
    )
    return {"decision": dict(resume)}


def apply_decision(state: AgentState) -> dict[str, Any]:
    """Resume HITL: approve/edit/reject — 1 transaction, sanitize text người gõ
    TRƯỚC khi lưu (nguyên tắc phase 13: presidio là biên PII duy nhất)."""
    from app.services.presidio_service import sanitize

    dec = state.get("decision") or {}
    action = dec.get("action")
    draft = state.get("insight_draft") or {}

    with SessionLocal() as db:
        ins = db.get(Insight, uuid.UUID(draft["id"]))
        original_snapshot = {
            "title": ins.title,
            "summary": ins.summary,
            "suggested_action": ins.suggested_action,
        }
        reviewer_id = dec.get("reviewer_id")

        if action == "approve":
            ins.review_status = ReviewStatus.approved
            for tpl in _draft_templates(
                state["run_id"], ins.title, ins.summary, ins.suggested_action
            ):
                db.add(ActionDraft(insight_id=ins.id, kind=tpl["kind"], body=tpl["body"]))
            db.add(
                InsightReview(
                    insight_id=ins.id,
                    original_value=original_snapshot,
                    action=ReviewAction.approve,
                    reason=dec.get("reason"),
                    reviewer_id=reviewer_id,
                )
            )
        elif action == "edit":
            new_title = dec.get("edited_title") or ins.title
            new_summary = dec.get("edited_summary") or ins.summary
            new_action_text = dec.get("edited_suggested_action") or ins.suggested_action
            # presidio trước lưu — raw người gõ không bao giờ lưu thẳng
            new_title = sanitize(new_title).sanitized_text
            new_summary = sanitize(new_summary).sanitized_text
            new_action_text = sanitize(new_action_text).sanitized_text
            content_changed = (new_title, new_summary) != (ins.title, ins.summary)
            ins.title, ins.summary, ins.suggested_action = (
                new_title,
                new_summary,
                new_action_text,
            )
            ins.review_status = ReviewStatus.edited
            if content_changed:
                vec = _safe_embed(f"{new_title}. {new_summary}")
                if vec is not None:
                    store_embedding(db, ins, vec)
            for tpl in _draft_templates(
                state["run_id"], new_title, new_summary, new_action_text
            ):
                db.add(ActionDraft(insight_id=ins.id, kind=tpl["kind"], body=tpl["body"]))
            db.add(
                InsightReview(
                    insight_id=ins.id,
                    original_value=original_snapshot,
                    edited_value={
                        "title": new_title,
                        "summary": new_summary,
                        "suggested_action": new_action_text,
                    },
                    action=ReviewAction.edit,
                    reason=dec.get("reason"),
                    reviewer_id=reviewer_id,
                )
            )
        elif action == "reject":
            ins.review_status = ReviewStatus.rejected
            # KHÔNG sinh draft — rejection thành precedent âm cho các run sau
            db.add(
                InsightReview(
                    insight_id=ins.id,
                    original_value=original_snapshot,
                    action=ReviewAction.reject,
                    reason=dec.get("reason"),
                    reviewer_id=reviewer_id,
                )
            )
        else:
            raise ValueError(f"action không hợp lệ: {action!r}")
        db.commit()

    return {
        "decision": {**dec, "insight_id": str(ins.id)},
        "observations": [
            {"tool": "apply_decision", "output_summary": f"{action} → {ins.review_status.value}"}
        ],
    }
