"""Routes feedback.

Lịch sử file: Phase 08 (chạy trước 05 theo quyết định owner — xem
docs/decisions.md 2026-08-24) dựng scaffold CHỈ với `/similar`; Phase 05
(docs/plans/05-feedback-ingestion.md §3.3) MỞ RỘNG — không viết lại — với
POST đơn lẻ, import-csv, list phân trang có filter, detail include_raw.
Guard role pm|operations gắn ở TẦNG ROUTER nên `/similar` cũng được bảo vệ
từ Phase 05 (trước đó tạm công khai ở dev theo entry Phase 08).
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
from app.models.enums import ReviewStatus, Severity
from app.models.feedback import Feedback
from app.schemas.feedback import (
    CsvImportReport,
    FeedbackDetailOut,
    FeedbackIn,
    FeedbackListOut,
    FeedbackOut,
)
from app.services.ingest_service import import_csv_rows, iter_csv_dicts, ingest_one

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
    """POST đơn lẻ — chỉ lưu raw_content; sanitized để Phase 06 điền."""
    return FeedbackOut.model_validate(ingest_one(session, item))


@router.post("/feedbacks/import-csv")
def import_feedbacks_csv(
    file: UploadFile = File(...), session: Session = Depends(get_db)
) -> CsvImportReport:
    """Import CSV multipart → report từng dòng lỗi, không abort toàn file.

    Đọc qua `iter_csv_dicts` (utf-8-sig chống BOM Excel) — cùng đường với CLI.
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File phải có đuôi .csv.",
        )
    report = import_csv_rows(session, iter_csv_dicts(file.file))
    return report


@router.get("/feedbacks")
def list_feedbacks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    review_status: ReviewStatus | None = Query(default=None),
    severity: Severity | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_db),
) -> FeedbackListOut:
    """List phân trang + filter. `category` match containment trong JSONB list
    (`categories @> '["..."]'`); dataset ≤1500 nên chấp nhận full scan."""
    conditions = []
    if review_status is not None:
        conditions.append(Feedback.review_status == review_status)
    if severity is not None:
        conditions.append(Feedback.severity == severity)
    if category is not None:
        conditions.append(Feedback.categories.contains([category]))

    total = session.scalar(select(func.count()).select_from(Feedback).where(*conditions))
    rows = session.scalars(
        select(Feedback)
        .where(*conditions)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())
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
    include_raw: bool = Query(default=False),
    session: Session = Depends(get_db),
) -> FeedbackOut | FeedbackDetailOut:
    """Detail; mặc định KHÔNG kèm raw_content (ranh giới PII) — chỉ khi
    `?include_raw=true` trả schema riêng chứa raw."""
    feedback = session.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback không tồn tại.")
    schema = FeedbackDetailOut if include_raw else FeedbackOut
    return schema.model_validate(feedback)


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
