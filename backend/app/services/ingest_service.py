"""Service ingestion — Phase 05 (05-feedback-ingestion.md §3.2).

Tầng dùng chung cho API (`routes/feedback.py`) và CLI
(`scripts/import_csv.py`) để logic ingest không bị nhân bản.

Nguyên tắc phase này: chỉ lưu `raw_content`; `sanitized_content` cố ý NULL —
Phase 06 (Presidio) điền sau. `created_at` là event time do nguồn cung cấp,
thiếu thì lấy now() tại thời điểm ingest.
"""

import csv
import io
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.schemas.feedback import CsvImportError, CsvImportReport, FeedbackIn

_REQUIRED_COLUMNS = ("source", "content")


def ingest_one(session: Session, item: FeedbackIn) -> Feedback:
    """Tạo 1 row feedback; commit ngay. Trả row đã refresh (có id, imported_at)."""
    feedback = Feedback(
        source=item.source,
        raw_content=item.content,
        external_ref=item.external_ref,
        created_at=item.created_at or datetime.now(timezone.utc),
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
    buộc, hay `created_at` sai ISO 8601 → lỗi. `source` được strip (thường là
    artifact spreadsheet); `content` giữ nguyên văn.
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

    created_at_raw = (row.get("created_at") or "").strip() or None
    external_ref = (row.get("external_ref") or "").strip() or None

    try:
        # fromisoformat của Python 3.11+ nhận cả 'Z' suffix và offset.
        created_at = (
            datetime.fromisoformat(created_at_raw) if created_at_raw else None
        )
    except ValueError:
        return None, CsvImportError(
            row=0,
            reason=f"'created_at' không phải ISO 8601: {created_at_raw!r}",
        )

    return (
        FeedbackIn(
            source=source,
            content=content,
            external_ref=external_ref,
            created_at=created_at,
        ),
        None,
    )


def import_csv_rows(session: Session, rows: Iterable[dict]) -> CsvImportReport:
    """Ingest một lượt các dòng CSV đã parse.

    Dòng lỗi KHÔNG hủy toàn file — được ghi vào `report.errors`, các dòng
    hợp lệ vẫn import. Số dòng trong report tính theo thứ tự lặp (header =
    dòng 1 nên data bắt đầu từ 2); nếu file có field chứa xuống dòng trong
    ngoặc kép, số dòng có thể lệch so với trình soạn thảo — chấp nhận với
    dataset nhỏ.
    """
    imported = 0
    errors: list[CsvImportError] = []

    for offset, row in enumerate(rows, start=2):
        item, error = _parse_row(row)
        if error is not None:
            error.row = offset
            errors.append(error)
            continue
        assert item is not None
        ingest_one(session, item)
        imported += 1

    return CsvImportReport(
        imported=imported, failed=len(errors), errors=errors
    )
