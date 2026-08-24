"""Routes feedback.

⚠️ SCAFFOLD PHASE 08: phase 08 chạy trước 05 nên file này CHỈ chứa endpoint
/similar. Phase 05 (docs/plans/05-feedback-ingestion.md §3.3) sẽ MỞ RỘNG —
không viết lại — với: POST /api/feedbacks, import-csv, list phân trang,
detail; và wire auth deps (get_current_user, require_role) cho toàn bộ router.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.feedback import Feedback

router = APIRouter(prefix="/api", tags=["feedback"])

_SNIPPET_CHARS = 200


@router.get("/feedbacks/{feedback_id}/similar")
def similar_feedbacks(
    feedback_id: uuid.UUID,
    k: int = Query(default=5, ge=1, le=50),
    session: Session = Depends(get_db),
) -> list[dict]:
    """Cosine nearest-neighbor exact scan quanh embedding của 1 feedback.

    KHÔNG tạo ANN index (pgvector ivfflat/hnsw): dataset ≤1500 rows nên exact
    scan qua ~1500 vector 1536-d là tức thời; ANN chỉ đáng khi lớn gấp hàng trăm
    lần — quyết định đã khóa trong AGENTS.md / execute-plan §1.
    """
    feedback = session.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback không tồn tại.")
    if feedback.embedding is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Feedback này chưa có embedding. Chạy embed (Phase 09 analysis "
                "hoặc embed_one thủ công) rồi thử lại."
            ),
        )

    from pgvector.utils import to_db  # noqa: PLC0415 - import cục bộ nhẹ

    query_vec = to_db(feedback.embedding)  # dạng text '[a,b,...]' cast về vector
    rows = session.execute(
        text(
            """
            SELECT id::text          AS id,
                   source,
                   sanitized_content,
                   1 - (embedding <=> CAST(:query_vec AS vector)) AS score
            FROM feedbacks
            WHERE id <> :id AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :k
            """
        ),
        {"query_vec": query_vec, "id": str(feedback_id), "k": k},
    ).mappings()

    return [
        {
            "id": row["id"],
            "score": float(row["score"]),
            "source": row["source"],
            # snippet từ sanitized_content (PII-safe); chưa sanitize → None.
            "snippet": (row["sanitized_content"] or "")[:_SNIPPET_CHARS] or None,
        }
        for row in rows
    ]
