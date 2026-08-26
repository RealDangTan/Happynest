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
