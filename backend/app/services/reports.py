"""Báo cáo PM thuần SQL — Phase 16, reshape VoC OS (plan 21).

CẤM gọi LLM/embedding ở module này — C4 ghi rõ thuần SQL làm đệm rủi ro hết
tín dụng (spec §8); acceptance criterion assert không import/mock llm_client.

Mọi aggregate tính trên cửa sổ EVENT TIME `occurred_at ≥ now − days`
(nhất quán với trend phase 14) — KHÔNG dùng imported_at.

Reshape 2026-08-28: severity/sentiment/topics đọc từ `ai_analysis` JSONB
(pattern CASE-guard jsonb_typeof — decisions.md 2026-08-26); KPI 3-latency
(phase-20 cũ) đã chết cùng bảng insights/action_drafts — dựng lại ở plan 27.
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.enums import Sentiment, Severity
from app.services.clustering import sample_feedback_ids_by_cluster

_TOP_CATEGORIES_LIMIT = 10
_EMERGING_LIMIT = 5

# Key đúng thứ tự contracts C4; sentiment thêm `mixed` theo enum thật (xem header)
SEVERITY_KEYS = [s.value for s in Severity]   # low, medium, high, critical
SENTIMENT_KEYS = ["positive", "neutral", "negative", "mixed"]

# --- Guard kiểu nằm TRONG lateral (không WHERE) — xem decisions 2026-08-26:
# hàm trong FROM đánh giá trước WHERE, 1 ô json-null/scalar là nổ cả query.
# topics là JSONB array → unnest với CASE-guard; severity/sentiment đọc qua
# `->>` (scalar text) nên json-null tự thành NULL comparison, vô hại.
_TOP_CATEGORIES_SQL = text("""
    SELECT cat AS category, count(*) AS count
    FROM feedback f,
         LATERAL jsonb_array_elements_text(
             CASE WHEN jsonb_typeof(f.ai_analysis->'topics') = 'array'
                  THEN f.ai_analysis->'topics' END
         ) AS cat
    WHERE f.occurred_at >= :cut
    GROUP BY cat
    ORDER BY count DESC, cat ASC
    LIMIT :lim
""")

# 1 select: totals + từng key severity/sentiment FILTER trên string JSONB —
# value lạ ngoài enum tự không khớp key nào (bị bỏ qua), key luôn đủ.
_AGG_SQL = text(f"""
    SELECT count(*),
           count(*) FILTER (WHERE f.pii_detected),
           {", ".join(
               f"count(*) FILTER (WHERE f.ai_analysis->>'severity' = '{sev}')"
               for sev in SEVERITY_KEYS
           )},
           {", ".join(
               f"count(*) FILTER (WHERE f.ai_analysis->>'sentiment' = '{sen}')"
               for sen in SENTIMENT_KEYS
           )}
    FROM feedback f
    WHERE f.occurred_at >= :cut
""")


def build_summary(db: Session, days: int, now: datetime) -> dict:
    """Aggregate C4 field-by-field trên cửa sổ event-time. Không LLM.

    Số round-trip được siết tối đa (pooler Supabase có RTT đáng kể):
    totals + 2 bộ key severity/sentiment trong MỘT select FILTER; query
    samples chỉ chạy khi emerging khác rỗng.
    """
    cut = now - timedelta(days=days)

    row = db.execute(_AGG_SQL, {"cut": cut}).one()
    total, pii = int(row[0]), int(row[1])
    n_sev = len(SEVERITY_KEYS)
    # FILTER so sánh string JSONB — NULL/không khớp → 0; key luôn đủ theo enum
    by_severity = dict(zip(SEVERITY_KEYS, (int(v) for v in row[2 : 2 + n_sev])))
    by_sentiment = dict(zip(SENTIMENT_KEYS, (int(v) for v in row[2 + n_sev :])))

    top_categories = [
        {"category": r.category, "count": r.count}
        for r in db.execute(_TOP_CATEGORIES_SQL, {"cut": cut, "lim": _TOP_CATEGORIES_LIMIT})
    ]

    emerging_rows = (
        db.execute(
            select(Cluster)
            .where(
                Cluster.is_emerging.is_(True) | Cluster.is_spike.is_(True)
            )
            .order_by(Cluster.suggested_priority.desc().nullslast())
            .limit(_EMERGING_LIMIT)
        )
        .scalars()
        .all()
    )
    samples = sample_feedback_ids_by_cluster(db) if emerging_rows else {}
    emerging = [
        {
            "id": c.id,
            "name": c.name,
            "summary": c.summary,
            "feedback_count": c.feedback_count,
            "first_seen": c.first_seen,
            "last_seen": c.last_seen,
            "current_count": c.current_count,
            "previous_count": c.previous_count,
            "growth_ratio": c.growth_ratio,
            "is_emerging": c.is_emerging,
            "is_spike": c.is_spike,
            "suggested_priority": c.suggested_priority,
            "sample_feedback_ids": samples.get(c.id, []),
        }
        for c in emerging_rows
    ]

    return {
        "generated_at": now,
        "window_days": days,
        "totals": {
            "feedback_count": int(total),
            "pii_detected_count": int(pii),
        },
        "by_severity": by_severity,
        "by_sentiment": by_sentiment,
        "top_categories": top_categories,
        "emerging": emerging,
    }


# ---------------------------------------------------------------------------
# KPIs — 3 latency + evaluation metrics 3 HITL gate (VoC OS §65–67, plan 27)
# ---------------------------------------------------------------------------

_UNDERSTAND_PIPELINE = "understand-v1"

_FINAL_INSIGHT_STATUS = ("approved", "edited", "rejected")


def _median_seconds(db: Session, stmt) -> float | None:
    """percentile_cont(0.5) trả None khi không có row nào — giữ nguyên là null."""
    v = db.execute(stmt).scalar()
    return round(float(v), 2) if v is not None else None


def build_kpis(db: Session, now: datetime) -> dict:
    """KPI thuần SQL (plan 27 Task 3): 3 latency + LISTEN/UNDERSTAND/ACT eval.

    Không một call LLM. Bảng rỗng / chưa đo → median None, count 0 (200).
    """
    from sqlalchemy import exists

    from app.models.action import Action
    from app.models.analysis_run import AnalysisRun
    from app.models.decision_log import DecisionLog
    from app.models.enums import DecisionSubject
    from app.models.feedback import Feedback
    from app.models.impact_check import ImpactCheck
    from app.models.insight import Insight

    # --- 3 latency (median theo PERCENTILE_CONT) ---
    listen = _median_seconds(
        db,
        select(
            func.percentile_cont(0.5).within_group(
                func.extract("epoch", AnalysisRun.started_at - Feedback.occurred_at)
            )
        )
        .select_from(Feedback)
        .join(AnalysisRun, Feedback.analysis_run_id == AnalysisRun.id)
        .where(
            AnalysisRun.pipeline_version != _UNDERSTAND_PIPELINE,
            Feedback.ai_analysis.isnot(None),
        ),
    )
    to_insight = _median_seconds(
        db,
        select(
            func.percentile_cont(0.5).within_group(
                func.extract("epoch", Insight.created_at - AnalysisRun.started_at)
            )
        )
        .select_from(Insight)
        .join(AnalysisRun, Insight.run_id == AnalysisRun.id),
    )
    first_action = (
        select(
            Action.insight_id.label("iid"),
            func.min(Action.created_at).label("t"),
        )
        .group_by(Action.insight_id)
        .subquery()
    )
    to_action = _median_seconds(
        db,
        select(
            func.percentile_cont(0.5).within_group(
                func.extract("epoch", first_action.c.t - Insight.created_at)
            )
        )
        .select_from(first_action)
        .join(Insight, first_action.c.iid == Insight.id),
    )

    insights_total = int(db.scalar(select(func.count()).select_from(Insight)) or 0)
    insights_with_action = int(
        db.scalar(select(func.count(func.distinct(Action.insight_id)))) or 0
    )

    # --- UNDERSTAND eval (§66): approval/edit/reject + evidence grounding ---
    has_review = exists().where(DecisionLog.subject_id == Insight.id)
    finalized_base = select(func.count()).select_from(Insight).where(
        Insight.status.in_(_FINAL_INSIGHT_STATUS)
    )
    insight_hitl = int(db.scalar(finalized_base.where(has_review)) or 0)
    insight_auto = int(db.scalar(finalized_base.where(~has_review)) or 0)
    grounded = int(
        db.scalar(
            select(func.count())
            .select_from(Insight)
            .where(func.jsonb_array_length(Insight.evidence) > 0)
        )
        or 0
    )

    # --- LISTEN eval (§65): mapping acceptance/edit rate từ decision_logs ---
    mapping_base = select(func.count()).select_from(DecisionLog).where(
        DecisionLog.subject_type == DecisionSubject.schema_mapping
    )
    mapping_total = int(db.scalar(mapping_base) or 0)
    mapping_accepted = int(
        db.scalar(
            mapping_base.where(DecisionLog.human_value["gate1_auto_imported"].is_(None))
        )
        or 0
    )  # mọi import qua Gate #1 đều là human-approved — direct acceptance = 100%

    # --- ACT eval (§67): acceptance/edit rate + agreement + displacement ---
    actions_total = int(db.scalar(select(func.count()).select_from(Action)) or 0)
    actions_accepted = int(
        db.scalar(
            select(func.count())
            .select_from(Action)
            .where(Action.status.in_(["accepted", "edited"]))
        )
        or 0
    )
    overridden = int(
        db.scalar(
            select(func.count())
            .select_from(Action)
            .where(Action.human_impact.isnot(None))
        )
        or 0
    )
    # impact agreement: 1 − |agent − human| / 10 (mean trên action bị override)
    impact_agreement = db.scalar(
        select(
            func.avg(
                1 - func.abs(Action.impact - Action.human_impact) / 10.0
            )
        ).where(Action.human_impact.isnot(None))
    )
    effort_agreement = db.scalar(
        select(
            func.avg(
                1 - func.abs(Action.effort - Action.human_effort) / 10.0
            )
        ).where(Action.human_effort.isnot(None))
    )
    # matrix displacement: khoảng cách Euclid (impact, effort) agent vs human —
    # trục chưa bị override dùng COALESCE(human, agent) (chỉ 1 trục cũng đo được)
    displacement = db.scalar(
        select(
            func.avg(
                func.sqrt(
                    func.pow(Action.impact - func.coalesce(Action.human_impact, Action.impact), 2)
                    + func.pow(Action.effort - func.coalesce(Action.human_effort, Action.effort), 2)
                )
            )
        ).where(Action.human_impact.isnot(None) | Action.human_effort.isnot(None))
    )

    checks_count = int(db.scalar(select(func.count()).select_from(ImpactCheck)) or 0)
    avg_delta = db.scalar(select(func.avg(ImpactCheck.delta_ratio)))

    def _pct(numer: int, denom: int) -> float:
        return round(numer / denom * 100, 2) if denom else 0.0

    def _r3(v) -> float | None:
        return round(float(v), 3) if v is not None else None

    return {
        "generated_at": now,
        "time_to_listen_median_s": listen,
        "time_to_insight_median_s": to_insight,
        "time_to_action_median_s": to_action,
        "insights_total": insights_total,
        "insights_with_action": insights_with_action,
        "pct_insight_with_action": _pct(insights_with_action, insights_total),
        "insight_hitl_count": insight_hitl,
        "insight_auto_count": insight_auto,
        "insight_evidence_grounding_pct": _pct(grounded, insights_total),
        "mapping_total": mapping_total,
        "mapping_accepted": mapping_accepted,
        "actions_total": actions_total,
        "actions_accepted": actions_accepted,
        "pct_action_accepted": _pct(actions_accepted, actions_total),
        "actions_overridden": overridden,
        "impact_agreement": _r3(impact_agreement),
        "effort_agreement": _r3(effort_agreement),
        "matrix_displacement_avg": _r3(displacement),
        "impact": {
            "checks_count": checks_count,
            "avg_delta_ratio": _r3(avg_delta),
        },
    }
