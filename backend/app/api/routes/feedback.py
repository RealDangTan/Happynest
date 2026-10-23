"""Routes feedback — reshape VoC OS (plan 21).

Lịch sử: Phase 05/06/08 dựng POST/import-csv/list/detail/similar trên bảng
phẳng cũ. Reshape 2026-08-28: mọi row gắn product (default = product đầu tiên
cho tới khi FE có product switcher), JSONB zones thay các cột phẳng, toggle
`?include_raw` chết cùng feedback-level HITL (raw KHÔNG BAO GIỜ ra response).
Phase 22: route import-csv CHUYỂN sang `POST /api/imports` (LISTEN pipeline
profiler → mapper → Gate #1); POST đơn lẻ giữ nguyên cho nhập tay.
Tất cả endpoint yêu cầu đăng nhập và CHỈ đụng product của chính tài khoản
(isolation — decisions.md 2026-10-22).
"""

import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import Float, case, func, select, text
from sqlalchemy.orm import Session, defer

from app.api.deps import (
    get_current_user,
    get_db,
    owned_product_ids,
    product_or_404,
)
from app.models.feedback import Feedback
from app.models.product import Product
from app.models.user import User
from app.schemas.feedback import (
    BulkDeleteOut,
    FeedbackBulkDeleteIn,
    FeedbackIn,
    FeedbackListOut,
    FeedbackOut,
    FeedbackUpdate,
)
from app.services.ingest_service import get_default_product, ingest_one
from app.services.presidio_service import sanitize

router = APIRouter(
    prefix="/api",
    tags=["feedback"],
    dependencies=[Depends(get_current_user)],
)

_SNIPPET_CHARS = 200


def _get_feedback_or_404(
    session: Session, feedback_id: uuid.UUID, user: User
) -> Feedback:
    """Load feedback của `user`; row lạ hoặc thiếu → 404."""
    feedback = session.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback không tồn tại.")
    product_or_404(session, feedback.product_id, user)
    return feedback


@router.post("/feedbacks", status_code=status.HTTP_201_CREATED)
def create_feedback(
    item: FeedbackIn,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackOut:
    """POST đơn lẻ — sanitize tại ingest; gắn product mặc định (của chính
    tài khoản)."""
    try:
        product = get_default_product(session, current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return FeedbackOut.model_validate(
        ingest_one(session, item, product_id=product.id)
    )


_SEVERITY_ORDER = case(
    (Feedback.ai_analysis["severity"].astext == "low", 1),
    (Feedback.ai_analysis["severity"].astext == "medium", 2),
    (Feedback.ai_analysis["severity"].astext == "high", 3),
    (Feedback.ai_analysis["severity"].astext == "critical", 4),
    else_=0,
)
# Sort whitelist cho list feedbacks — FE DataTable gửi trực tiếp giá trị này.
_FEEDBACK_SORTS: dict[str, list] = {
    "newest": [Feedback.occurred_at.desc(), Feedback.id.desc()],
    "oldest": [Feedback.occurred_at.asc(), Feedback.id.asc()],
    "source": [Feedback.source.asc(), Feedback.occurred_at.desc()],
    "-source": [Feedback.source.desc(), Feedback.occurred_at.desc()],
    "severity": [_SEVERITY_ORDER.desc(), Feedback.occurred_at.desc()],
    "-severity": [_SEVERITY_ORDER.asc(), Feedback.occurred_at.desc()],
    "confidence": [
        func.cast(Feedback.ai_analysis["confidence"].astext, Float).desc().nulls_last(),
        Feedback.occurred_at.desc(),
    ],
    "-confidence": [
        func.cast(Feedback.ai_analysis["confidence"].astext, Float).asc().nulls_last(),
        Feedback.occurred_at.desc(),
    ],
}


@router.get("/feedbacks")
def list_feedbacks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    product_id: uuid.UUID | None = Query(default=None),
    import_id: uuid.UUID | None = Query(default=None),
    analysis_state: str | None = Query(
        default=None, pattern="^(pending|completed|uncategorized)$"
    ),
    severity: str | None = Query(default=None, min_length=1),
    sentiment: str | None = Query(default=None, min_length=1),
    topic: str | None = Query(default=None, min_length=1),
    source: str | None = Query(default=None, min_length=1),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    sort: str = Query(
        default="newest",
        pattern="^(newest|oldest|-?source|-?severity|-?confidence)$",
    ),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackListOut:
    """List phân trang + filter trên JSONB `ai_analysis` (severity/sentiment/
    topic containment) và cột `source`. Dataset ≤1500 nên chấp nhận full scan.
    Có thể lọc theo product; MẶC ĐỊNH chỉ feedback thuộc product của chính
    tài khoản (isolation 2026-10-22).

    `q` (2026-10-24): search text không phân biệt hoa thường trên
    `feedback_text` (đã sanitize) + `source` — search chạy trên TOÀN BỘ tập
    dữ liệu, không phải trang hiện tại (FE trước đây filter client-side từng
    trang nên kết quả sai lệch).
    `sort` (2026-10-24): whitelist `newest|oldest|source|-source|severity|
    -severity|confidence|-confidence`; severity xếp theo thứ tự ngữ nghĩa
    low<medium<high<critical (không phải alphabet), confidence cast float.
    `severity`/`sentiment` (2026-10-24): nhận comma-list (faceted multi-select
    FE: `severity=high,critical`) — giá trị đơn vẫn chạy như cũ.

    `analysis_state=uncategorized` (2026-10-23): rows ĐÃ analyzed nhưng đang
    mang nhãn UNCATEGORIZED — vault dùng đếm để gợi ý mở khoá re-enrich sau
    khi taxonomy đổi. Perf: 1 query duy nhất (count() OVER() kèm page) + defer
    cột `embedding` (vector 1536-d ~19KB/row không bao giờ nằm trong response —
    kéo nó qua WAN chỉ để vứt là nguồn chậm chính của vault trước đây)."""
    conditions = []
    if product_id is not None:
        product_or_404(session, product_id, current_user)
        conditions.append(Feedback.product_id == product_id)
    else:
        conditions.append(
            Feedback.product_id.in_(owned_product_ids(session, current_user))
        )
    if import_id is not None:
        conditions.append(Feedback.import_id == import_id)
    if analysis_state == "pending":
        conditions.append(Feedback.ai_analysis.is_(None))
    elif analysis_state == "completed":
        conditions.append(Feedback.ai_analysis.is_not(None))
    elif analysis_state == "uncategorized":
        conditions.append(Feedback.ai_analysis["uncategorized"].astext == "true")
    if severity is not None:
        _severities = [s for s in severity.split(",") if s]
        conditions.append(
            Feedback.ai_analysis["severity"].astext.in_(_severities)
        )
    if sentiment is not None:
        _sentiments = [s for s in sentiment.split(",") if s]
        conditions.append(
            Feedback.ai_analysis["sentiment"].astext.in_(_sentiments)
        )
    if topic is not None:
        conditions.append(Feedback.ai_analysis["topics"].contains([topic]))
    if source is not None:
        conditions.append(Feedback.source == source)
    if q is not None:
        like = f"%{q.lower()}%"
        conditions.append(
            func.lower(Feedback.feedback_text).like(like)
            | func.lower(Feedback.source).like(like)
        )

    rows = session.execute(
        select(func.count().over().label("_total"), Feedback)
        .where(*conditions)
        .options(defer(Feedback.embedding))
        .order_by(*_FEEDBACK_SORTS[sort])
        .offset(offset)
        .limit(limit)
    ).all()
    # Page trống (offset quá далеко) → window function không có row để đọc
    # total; rơi về count query riêng chỉ trong edge case này.
    total = int(rows[0][0]) if rows else int(
        session.scalar(select(func.count()).select_from(Feedback).where(*conditions)) or 0
    )
    return FeedbackListOut(
        items=[FeedbackOut.model_validate(r[1]) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/feedbacks/{feedback_id}")
def get_feedback(
    feedback_id: uuid.UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackOut:
    """Detail — `feedback_text` (đã sanitize) là dữ liệu phân tích; raw_content
    KHÔNG BAO GIỜ nằm trong response (ranh giới PII)."""
    feedback = _get_feedback_or_404(session, feedback_id, current_user)
    return FeedbackOut.model_validate(feedback)


@router.get("/feedbacks/{feedback_id}/similar")
def similar_feedbacks(
    feedback_id: uuid.UUID,
    k: int = Query(default=5, ge=1, le=50),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Cosine nearest-neighbor exact scan quanh embedding của 1 feedback.

    KHÔNG tạo ANN index (pgvector ivfflat/hnsw): dataset ≤1500 rows nên exact
    scan qua ~1500 vector 1536-d là tức thời; ANN chỉ đáng khi lớn gấp hàng trăm
    lần — quyết định đã khóa trong AGENTS.md / execute-plan §1.
    Scan giới hạn trong các product của chính tài khoản (isolation).
    """
    feedback = _get_feedback_or_404(session, feedback_id, current_user)
    if feedback.embedding is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Feedback này chưa có embedding. Chạy phân tích (POST "
                "/api/analysis/runs) rồi thử lại."
            ),
        )
    pids = owned_product_ids(session, current_user)
    if not pids:
        return []

    # Chuẩn hóa vector về dạng text '[a,b,...]' để cast AS vector trong SQL.
    # Cột Vector tùy driver có thể trả pgvector.Vector | ndarray | list.
    emb = feedback.embedding
    if hasattr(emb, "to_text"):  # pgvector.Vector (result processor)
        query_vec = emb.to_text()
    else:
        query_vec = "[" + ",".join(f"{float(x)!r}" for x in emb) + "]"
    rows = session.execute(
        text(
            """
            SELECT id::text          AS id,
                   source,
                   feedback_text,
                   1 - (embedding <=> CAST(:query_vec AS vector)) AS score
            FROM feedback
            WHERE id <> :id AND embedding IS NOT NULL
              AND product_id = ANY(CAST(:pids AS uuid[]))
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :k
            """
        ),
        {
            "query_vec": query_vec,
            "id": str(feedback_id),
            "k": k,
            "pids": [str(p) for p in pids],
        },
    ).mappings()

    return [
        {
            "id": row["id"],
            "score": float(row["score"]),
            "source": row["source"],
            # snippet từ feedback_text (PII-safe); chưa sanitize → None.
            "snippet": (row["feedback_text"] or "")[:_SNIPPET_CHARS] or None,
        }
        for row in rows
    ]


@router.patch("/feedbacks/{feedback_id}")
def update_feedback(
    feedback_id: uuid.UUID,
    item: FeedbackUpdate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackOut:
    """Sửa feedback — hard rule #2: text mới qua lại `sanitize()`; raw_content
    được thay bằng text mới do chính người dùng nhập. Text đổi → embedding NULL
    (vector cũ mô tả text cũ; `/similar` đã 409 cho embedding NULL)."""
    feedback = _get_feedback_or_404(session, feedback_id, current_user)
    changed = item.model_fields_set

    if "feedback_text" in changed and item.feedback_text is not None:
        result = sanitize(item.feedback_text)
        feedback.raw_content = item.feedback_text
        feedback.feedback_text = result.sanitized_text
        feedback.pii_detected = result.pii_detected
        feedback.pii_entities = [e.model_dump() for e in result.entities]
        feedback.embedding = None
        feedback.embedding_model = None
        feedback.embedding_dim = None

    if "source" in changed and item.source is not None:
        feedback.source = item.source
    if "occurred_at" in changed and item.occurred_at is not None:
        feedback.occurred_at = item.occurred_at
    if "ai_analysis" in changed and item.ai_analysis is not None:
        # Partial merge — nhãn người dùng sửa đè nhãn AI, phần còn lại giữ nguyên.
        merged = dict(feedback.ai_analysis or {})
        merged.update(item.ai_analysis)
        feedback.ai_analysis = merged

    session.commit()
    session.refresh(feedback)
    return FeedbackOut.model_validate(feedback)


@router.delete(
    "/feedbacks/{feedback_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_feedback(
    feedback_id: uuid.UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Hard delete 1 feedback — không có bảng con tham chiếu (embedding nằm
    trên row; cluster_id chỉ là con trỏ) nên xoá là sạch."""
    feedback = _get_feedback_or_404(session, feedback_id, current_user)
    session.delete(feedback)
    session.commit()


@router.post("/feedbacks/bulk-delete")
def bulk_delete_feedbacks(
    body: FeedbackBulkDeleteIn,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkDeleteOut:
    """Hard delete nhiều feedback trong 1 transaction; id lạ hoặc id thuộc
    product người khác bị bỏ qua (deleted = số row thật sự mất)."""
    rows = session.scalars(
        select(Feedback)
        .join(Product, Feedback.product_id == Product.id)
        .where(
            Feedback.id.in_(body.ids),
            Product.owner_id == current_user.id,
        )
    ).all()
    for row in rows:
        session.delete(row)
    session.commit()
    return BulkDeleteOut(deleted=len(rows))
