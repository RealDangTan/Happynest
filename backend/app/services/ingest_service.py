"""Service ingestion — reshape VoC OS (plan 21).

Tầng dùng chung cho API (`routes/feedback.py`) và CLI (`scripts/import_csv.py`).

Thay đổi so thiết kế cũ:
- Mọi row gắn `product_id` (bắt buộc) + `import_id` (nguồn gốc lô).
- Event time đổi tên `occurred_at` (từ `created_at` cũ).
- `feedback_text` = text ĐÃ sanitize (đổi tên từ `sanitized_content`).

Ranh giới PII (hard rule #2): mọi content đi qua `sanitize()` NGAY tại đây —
`raw_content` giữ nguyên trong DB; chỉ `feedback_text` + metadata `pii_entities`
(không mang text raw) ra ngoài biên.

Phase 22 (LISTEN) sẽ thay đường CSV legacy bằng pipeline profiler → mapper →
Gate #1; `import_csv_rows` giữ lại làm đường nhanh không-schema cho đến lúc đó.
"""

import csv
import io
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ImportStatus
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.models.product import Product
from app.schemas.feedback import CsvImportError, CsvImportReport, FeedbackIn
from app.services.presidio_service import sanitize

_REQUIRED_COLUMNS = ("source", "content")


def get_default_product(session: Session) -> Product:
    """Product đầu tiên (migration 0008 seed 'Happynest'). Phase 22+ cho phép
    nhiều product — lúc đó routes sẽ nhận product_id tường minh."""
    product = session.scalars(select(Product).order_by(Product.created_at).limit(1)).first()
    if product is None:
        raise LookupError("Chưa có product nào — tạo POST /api/products trước.")
    return product


def ingest_one(
    session: Session,
    item: FeedbackIn,
    *,
    product_id: UUID,
    import_id: UUID | None = None,
) -> Feedback:
    """Tạo 1 row feedback (đã sanitize); commit ngay.
    Trả row đã refresh (có id, imported_at)."""
    result = sanitize(item.content)
    feedback = Feedback(
        product_id=product_id,
        import_id=import_id,
        source=item.source,
        source_record_id=item.source_record_id,
        occurred_at=item.occurred_at or datetime.now(timezone.utc),
        raw_content=item.content,
        feedback_text=result.sanitized_text,
        pii_detected=result.pii_detected,
        pii_entities=[e.model_dump() for e in result.entities],
        data=item.data,
        source_meta=item.source_meta,
    )
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return feedback


def iter_csv_dicts(binary_stream) -> Iterator[dict]:
    """Đọc stream nhị phân CSV → dict theo header.

    `utf-8-sig` để nuốt BOM mà Excel thêm vào file UTF-8; delimiter `,`
    theo plan. Caller chịu trách nhiệm đóng stream.
    """
    reader = csv.DictReader(
        io.TextIOWrapper(binary_stream, encoding="utf-8-sig", newline="")
    )
    yield from reader


def _row_error(row_num: int, reason: str) -> tuple[None, CsvImportError]:
    return None, CsvImportError(row=row_num, reason=reason)


def _parse_row(row: dict) -> tuple[FeedbackIn | None, CsvImportError | None]:
    """Validate 1 dòng CSV → (FeedbackIn, None) hoặc (None, lỗi).

    Dòng thiếu cột (DictReader gán None) hoặc rỗng/số-khoảng-trắng ở cột bắt
    buộc, hay `occurred_at` sai ISO 8601 → lỗi. `source` được strip (thường là
    artifact spreadsheet); `content` giữ nguyên văn. Cột ngoài `source`/
    `content`/`occurred_at`/`source_record_id` đi thẳng vào `source_meta`.
    """
    for col in _REQUIRED_COLUMNS:
        value = row.get(col)
        if value is None:
            return None, CsvImportError(row=0, reason=f"Thiếu cột bắt buộc '{col}'.")
        if col == "source":
            value = value.strip()

    source = row["source"].strip()
    content = row["content"]
    if not source:
        return None, CsvImportError(row=0, reason="Cột 'source' rỗng.")
    if not content.strip():
        return None, CsvImportError(row=0, reason="Cột 'content' rỗng.")

    occurred_raw = (row.get("occurred_at") or row.get("created_at") or "").strip() or None
    source_record_id = (row.get("source_record_id") or row.get("external_ref") or "").strip() or None

    try:
        # fromisoformat của Python 3.11+ nhận cả 'Z' suffix và offset.
        occurred_at = datetime.fromisoformat(occurred_raw) if occurred_raw else None
    except ValueError:
        return None, CsvImportError(
            row=0,
            reason=f"'occurred_at' không phải ISO 8601: {occurred_raw!r}",
        )

    core = {"source", "content", "occurred_at", "created_at", "source_record_id", "external_ref"}
    source_meta = {k: v for k, v in row.items() if k not in core and v not in (None, "")}

    return (
        FeedbackIn(
            source=source,
            content=content,
            source_record_id=source_record_id,
            occurred_at=occurred_at,
            source_meta=source_meta,
        ),
        None,
    )


def import_csv_rows(
    session: Session, rows: Iterable[dict], *, product_id: UUID
) -> CsvImportReport:
    """Ingest một lượt các dòng CSV đã parse.

    Dòng lỗi KHÔNG hủy toàn file — được ghi vào `report.errors`, các dòng
    hợp lệ vẫn import. Tạo 1 row `imports` (source_type='csv_legacy') gắn
    import_id vào mọi feedback của lô. Số dòng trong report tính theo thứ tự
    lặp (header = dòng 1 nên data bắt đầu từ 2); nếu file có field chứa xuống
    dòng trong ngoặc kép, số dòng có thể lệch so với trình soạn thảo — chấp
    nhận với dataset nhỏ.
    """
    import_row = Import(
        product_id=product_id, source_type="csv_legacy", status=ImportStatus.pending
    )
    session.add(import_row)
    session.commit()
    session.refresh(import_row)

    imported = 0
    errors: list[CsvImportError] = []

    try:
        for offset, row in enumerate(rows, start=2):
            item, error = _parse_row(row)
            if error is not None:
                error.row = offset
                errors.append(error)
                continue
            assert item is not None
            ingest_one(session, item, product_id=product_id, import_id=import_row.id)
            imported += 1
    except Exception as exc:  # noqa: BLE001 — lô hỏng nặng → import failed
        import_row.status = ImportStatus.failed
        import_row.error = f"{type(exc).__name__}: {exc}"[:2000]
        session.commit()
        raise

    import_row.status = ImportStatus.imported
    import_row.row_count = imported
    session.commit()

    return CsvImportReport(
        imported=imported,
        failed=len(errors),
        errors=errors,
        import_id=import_row.id,
    )
