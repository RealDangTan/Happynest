"""Routes feedback — reshape VoC OS (plan 21).

Lịch sử: Phase 05/06/08 dựng POST/import-csv/list/detail/similar trên bảng
phẳng cũ. Reshape 2026-08-28: mọi row gắn product (default = product đầu tiên
cho tới khi FE có product switcher), JSONB zones thay các cột phẳng, toggle
`?include_raw` chết cùng feedback-level HITL (raw KHÔNG BAO GIỜ ra response).
Guard role pm|operations gắn ở TẦNG ROUTER.
"""

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.feedback import Feedback
from app.schemas.feedback import (
    CsvImportReport,
    FeedbackIn,
    FeedbackListOut,
    FeedbackOut,
)
from app.services.ingest_service import (
    get_default_product,
    import_csv_rows,
    iter_csv_dicts,
    ingest_one,
)

router = APIRouter(
    prefix="/api",
    tags=["feedback"],
    # Guard toàn router (kể cả /similar): chỉ pm | operations.
    dependencies=[Depends(require_role("pm", "operations"))],
)

_SNIPPET_CHARS = 200


@router.post("/feedbacks", status_code=status.HTTP_201_CREATED)
def create_feedback(
    item: FeedbackIn, session: Session = Depends(get_db)
) -> FeedbackOut:
    """POST đơn lẻ — sanitize tại ingest; gắn product mặc định."""
    try:
        product = get_default_product(session)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return FeedbackOut.model_validate(
        ingest_one(session, item, product_id=product.id)
    )


@router.post("/feedbacks/import-csv")
def import_feedbacks_csv(
    file: UploadFile = File(...), session: Session = Depends(get_db)
) -> CsvImportReport:
    """Import CSV multipart → report từng dòng lỗi, không abort toàn file.

    Đường legacy (phase 21) — gắn product mặc định, cột ngoài core đi vào
    `source_meta`. Phase 22 (LISTEN) sẽ thay bằng pipeline profiler → mapper
    → Gate #1 với product schema.
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File phải có đuôi .csv.",
        )
    try:
        product = get_default_product(session)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return import_csv_rows(session, iter_csv_dicts(file.file), product_id=product.id)


@router.get("/feedbacks")
def list_feedbacks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    product_id: uuid.UUID | None = Query(default=None),
    severity: str | None = Query(default=None, min_length=1),
    sentiment: str | None = Query(default=None, min_length=1),
    topic: str | None = Query(default=None, min_length=1),
    source: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_db),
) -> FeedbackListOut:
    """List phân trang + filter trên JSONB `ai_analysis` (severity/sentiment/
    topic containment) và cột `source`. Dataset ≤1500 nên chấp nhận full scan."""
    conditions = []
    if product_id is not None:
        conditions.append(Feedback.product_id == product_id)
    if severity is not None:
        conditions.append(Feedback.ai_analysis["severity"].astext == severity)
    if sentiment is not None:
        conditions.append(Feedback.ai_analysis["sentiment"].astext == sentiment)
    if topic is not None:
        conditions.append(Feedback.ai_analysis["topics"].contains([topic]))
    if source is not None:
        conditions.append(Feedback.source == source)

    total = session.scalar(select(func.count()).select_from(Feedback).where(*conditions))
    rows = session.scalars(
        select(Feedback)
        .where(*conditions)
        .order_by(Feedback.occurred_at.desc(), Feedback.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return FeedbackListOut(
        items=[FeedbackOut.model_validate(r) for r in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get("/feedbacks/{feedback_id}")
def get_feedback(
    feedback_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> FeedbackOut:
    """Detail — `feedback_text` (đã sanitize) là dữ liệu phân tích; raw_content
    KHÔNG BAO GIỜ nằm trong response (ranh giới PII)."""
    feedback = session.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback không tồn tại.")
    return FeedbackOut.model_validate(feedback)


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
                "Feedback này chưa có embedding. Chạy phân tích (POST "
                "/api/analysis/runs) rồi thử lại."
            ),
        )

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
            # snippet từ feedback_text (PII-safe); chưa sanitize → None.
            "snippet": (row["feedback_text"] or "")[:_SNIPPET_CHARS] or None,
        }
        for row in rows
    ]
