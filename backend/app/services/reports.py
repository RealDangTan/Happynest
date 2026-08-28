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
