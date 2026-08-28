"""Báo cáo PM thuần SQL — Phase 16 (contract C4).

CẤM gọi LLM/embedding ở module này — C4 ghi rõ thuần SQL làm đệm rủi ro hết
tín dụng (spec §8); acceptance criterion assert không import/mock llm_client.

Mọi aggregate tính trên cửa sổ EVENT TIME `created_at ≥ now − days`
(nhất quán với trend phase 14) — KHÔNG dùng imported_at.

Lệch hợp đồng có chủ đích (decisions.md 2026-08-26): `by_sentiment` có 4 key
gồm `mixed` — enum Sentiment thực tế có mixed và data demo có 7/25 row mixed;
bỏ key này làm tổng by_sentiment lệch hẳn feedback_count.
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.cluster import Cluster
from app.models.enums import ReviewStatus, Sentiment, Severity
from app.models.feedback import Feedback
from app.services.clustering import sample_feedback_ids_by_cluster

_TOP_CATEGORIES_LIMIT = 10
_EMERGING_LIMIT = 5

# Key đúng thứ tự contracts C4; sentiment thêm `mixed` theo enum thật (xem header)
SEVERITY_KEYS = [s.value for s in Severity]   # low, medium, high, critical
SENTIMENT_KEYS = ["positive", "neutral", "negative", "mixed"]

# Guard kiểu nằm TRONG lateral chứ KHÔNG phải WHERE: hàm trong FROM đánh giá
# trước WHERE trên từng row, mà SQLAlchemy JSONB mặc định bind None tường minh
# thành JSON `null` (không phải SQL NULL) → 1 ô json-null/scalar là nổ cả query
# (root cause: tests/test_reports_service.py, decisions.md 2026-08-26).
# CASE không ELSE → SQL NULL → hàm strict trả 0 row cho ô lỗi, query sống sót.
_TOP_CATEGORIES_SQL = text("""
    SELECT cat AS category, count(*) AS count
    FROM feedbacks f,
         LATERAL jsonb_array_elements_text(
             CASE WHEN jsonb_typeof(f.categories) = 'array'
                  THEN f.categories END
         ) AS cat
    WHERE f.created_at >= :cut
    GROUP BY cat
    ORDER BY count DESC, cat ASC
    LIMIT :lim
""")


def build_summary(db: Session, days: int, now: datetime) -> dict:
    """Aggregate C4 field-by-field trên cửa sổ event-time. Không LLM.

    Số round-trip được siết tối đa (pooler Supabase có RTT đáng kể):
    totals + 2 bộ enum gọn trong MỘT select FILTER; query samples chỉ chạy
    khi emerging khác rỗng.
    """
    cut = now - timedelta(days=days)

    # --- 1 select: tổng, pending, pii + từng key severity/sentiment ---
    exprs = [
        func.count(),
        func.count().filter(Feedback.review_status == ReviewStatus.pending),
        func.count().filter(Feedback.pii_detected.is_(True)),
    ]
    for key in SEVERITY_KEYS:
        exprs.append(func.count().filter(Feedback.severity == Severity(key)))
    for key in SENTIMENT_KEYS:
        exprs.append(func.count().filter(Feedback.sentiment == Sentiment(key)))
    row = db.execute(select(*exprs).where(Feedback.created_at >= cut)).one()

    total, pending, pii = row[0], row[1], row[2]
    n_sev = len(SEVERITY_KEYS)
    # NULL tự loại vì filter so sánh enum → False trên NULL; key thiếu vẫn 0
    by_severity = dict(zip(SEVERITY_KEYS, (int(v) for v in row[3 : 3 + n_sev])))
    by_sentiment = dict(zip(SENTIMENT_KEYS, (int(v) for v in row[3 + n_sev :])))

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
            "feedback_count": total,
            "pending_review_count": pending,
            "pii_detected_count": pii,
        },
        "by_severity": by_severity,
        "by_sentiment": by_sentiment,
        "top_categories": top_categories,
        "emerging": emerging,
    }


# Pipeline phân biệt đường sản xuất (runner deterministic) với agent (phase 19)
# — KPI time_to_listen chỉ đo đường classify sản xuất (plan 20 §3 Task 2.1).
_AGENT_PIPELINE = "agent-router-v1"
_FINALIZED = [ReviewStatus.approved, ReviewStatus.edited, ReviewStatus.rejected]


def _median_seconds(db: Session, stmt) -> float | None:
    """percentile_cont(0.5) trả None khi không có row nào — giữ nguyên là null."""
    v = db.execute(stmt).scalar()
    return round(float(v), 2) if v is not None else None


def build_kpis(db: Session, now: datetime) -> dict:
    """KPI 3-latency + tỉ lệ insight→action + HITL/auto + impact — THUẦN SQL.

    Không một call LLM (điểm khác biệt luận văn, plan 20 §2). Mỗi dòng KPI là
    1 aggregate riêng; median tính bằng PERCENTILE_CONT trên PG17. Bảng rỗng
    → median None / count 0 — KHÔNG bao giờ lỗi "chưa có cụm".
    """
    from sqlalchemy import exists

    from app.models.action_draft import ActionDraft
    from app.models.analysis_run import AnalysisRun
    from app.models.impact_check import ImpactCheck
    from app.models.insight import Insight
    from app.models.insight_review import InsightReview

    # time_to_listen: feedback → run bắt đầu xử lý (classify sản xuất)
    listen = _median_seconds(
        db,
        select(
            func.percentile_cont(0.5).within_group(
                func.extract("epoch", AnalysisRun.started_at - Feedback.created_at)
            )
        )
        .join(AnalysisRun, Feedback.analysis_run_id == AnalysisRun.id)
        .where(
            AnalysisRun.pipeline_version != _AGENT_PIPELINE,
            Feedback.categories.isnot(None),
        ),
    )

    # time_to_insight: cụm last_seen → insight được sinh
    to_insight = _median_seconds(
        db,
        select(
            func.percentile_cont(0.5).within_group(
                func.extract("epoch", Insight.created_at - Cluster.last_seen)
            )
        ).join(Cluster, Insight.cluster_id == Cluster.id),
    )

    # time_to_action: insight → ticket draft ĐẦU TIÊN (median theo insight);
    # inner join tự loại insight chưa có draft → None khi chưa có draft nào
    first_draft = (
        select(
            ActionDraft.insight_id.label("iid"),
            func.min(ActionDraft.created_at).label("t"),
        )
        .group_by(ActionDraft.insight_id)
        .subquery()
    )
    to_action = _median_seconds(
        db,
        select(
            func.percentile_cont(0.5).within_group(
                func.extract("epoch", first_draft.c.t - Insight.created_at)
            )
        ).join(Insight, first_draft.c.iid == Insight.id),
    )

    insights_total = int(db.scalar(select(func.count()).select_from(Insight)) or 0)
    insights_with_action = int(
        db.scalar(select(func.count(func.distinct(ActionDraft.insight_id)))) or 0
    )

    has_review = exists().where(InsightReview.insight_id == Insight.id)
    finalized_base = select(func.count()).select_from(Insight).where(
        Insight.review_status.in_(_FINALIZED)
    )
    hitl = int(db.scalar(finalized_base.where(has_review)) or 0)
    auto = int(db.scalar(finalized_base.where(~has_review)) or 0)
    finalized_n = hitl + auto

    checks_count = int(db.scalar(select(func.count()).select_from(ImpactCheck)) or 0)
    avg_delta = db.scalar(select(func.avg(ImpactCheck.delta_ratio)))

    def _pct(numer: int, denom: int) -> float:
        return round(numer / denom * 100, 2) if denom else 0.0

    return {
        "generated_at": now,
        "time_to_listen_median_s": listen,
        "time_to_insight_median_s": to_insight,
        "time_to_action_median_s": to_action,
        "insights_total": insights_total,
        "insights_with_action": insights_with_action,
        "pct_insight_with_action": _pct(insights_with_action, insights_total),
        "hitl_count": hitl,
        "auto_count": auto,
        "hitl_share": _pct(hitl, finalized_n),
        "impact": {
            "checks_count": checks_count,
            "avg_delta_ratio": round(float(avg_delta), 3) if avg_delta is not None else None,
        },
    }
