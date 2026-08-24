# Phase 05 — Feedback Ingestion (POST · CSV · list · detail)

> **Nguồn:** execute-plan §7 (routes feedback) + DoD mục 3
> **Trạng thái:** ✅ 2026-08-24 · **Blocked by:** Phase 03, 04
> **Commit mẫu:** `feat(feedback): manual post, csv import, paginated list/detail`

## 1 · Mục tiêu

Đưa phản hồi vào hệ thống qua 2 đường: POST đơn lẻ và import CSV (API upload + CLI). List phân trang có filter. Ở phase này **chỉ lưu `raw_content`** — cột sanitize sẽ được Phase 06 điền.

## 2 · Việc CON NGƯỜI

- Chuẩn bị file CSV mẫu 20 dòng mixed VN-EN (có fake PII) để test — hoặc dùng fixture agent sinh trong tests (`tests/fixtures/feedback_sample_20.csv`, fake 100%).

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 Schemas — `app/schemas/feedback.py`
- `FeedbackIn{source:str, content:str, external_ref?:str, created_at?:datetime}` — created_at thiếu → dùng now() lúc ingest (đây là **event time**; phân biệt với `imported_at` do DB set).
- `FeedbackOut{id, source, external_ref?, created_at, imported_at, review_status, severity?, categories?, confidence?, requires_human_review, sanitized_content?}`.
  - **`raw_content` KHÔNG nằm trong FeedbackOut mặc định** — chỉ lộ khi query param `include_raw=true` (DoD mục 4) qua schema riêng `FeedbackDetailOut(FeedbackOut){raw_content}`.
- `CsvImportReport{imported:int, failed:int, errors:[{row:int, reason:str}]}`.

### 3.2 Service layer — `app/services/ingest_service.py`
(tách service để CLI và API dùng chung — tránh nhân bản logic)
- `ingest_one(session, item: FeedbackIn) -> Feedback`: tạo row, `raw_content=content`, `sanitized_content=None` (Phase 06 điền), commit.
- `import_csv_rows(session, rows: Iterable[dict]) -> CsvImportReport`:
  - cột bắt buộc `source,content`; tùy chọn `created_at` (ISO 8601), `external_ref`;
  - dòng thiếu cột / created_at sai format → ghi vào `errors`, KHÔNG abort toàn file;
  - đọc CSV bằng stdlib `csv`, encoding `utf-8-sig` (chống BOM từ Excel), hỗ trợ delimiter `,`.

### 3.3 Routes — `app/api/routes/feedback.py`
| Endpoint | Role | Ghi chú |
|---|---|---|
| `POST /api/feedbacks` | pm \| operations | body `FeedbackIn` → trả `FeedbackOut` |
| `POST /api/feedbacks/import-csv` | pm \| operations | multipart upload `.csv` (`python-multipart` đã pin) → `CsvImportReport` |
| `GET /api/feedbacks` | pm \| operations | `?limit<=100&offset&review_status&severity&category` (category match trong JSONB list); trả `{items:[FeedbackOut], total, limit, offset}` |
| `GET /api/feedbacks/{id}` | pm \| operations | `FeedbackDetailOut`; `?include_raw=true` mới kèm raw |
| `GET /api/feedbacks/{id}/similar` | — | **501 stub** có docstring "phase embedding" (Phase 08 thay) |

### 3.4 CLI — `backend/scripts/import_csv.py`
- `uv run python scripts/import_csv.py path/to/file.csv` — gọi đúng `import_csv_rows`, in report. Tự dựng session, không cần app chạy.

### 3.5 Tests — `backend/tests/test_ingest.py`
- POST đơn lẻ lưu đủ trường, `created_at` fallback đúng;
- import CSV fixture 20 dòng mixed VN-EN → `imported=20` (hoặc lỗi dòng chủ đích được đếm đúng);
- filter `severity`/`review_status` trên list hoạt động;
- `GET detail` mặc định không chứa raw; `include_raw=true` mới có;
- role sai → 403.

## 4 · Tiêu chí nghiệm thu (map DoD)

| DoD mục 3 | Bằng chứng |
|---|---|
| Import CSV 20 dòng mixed VN-EN (fake PII) thành công | test + curl thật |
| `raw_content` lưu nguyên vẹn; `sanitized_content` NULL ở giai đoạn này | query DB |
| Pagination + filter chạy | test |

## 5 · Lệnh kiểm chứng

```powershell
cd backend
uv run pytest tests/test_ingest.py
uv run python scripts/import_csv.py ../tests/fixtures/feedback_sample_20.csv
# API:
curl -s -X POST http://localhost:8000/api/feedbacks -H "Content-Type: application/json" -b cookie.txt -d '{"source":"app_review","content":"Ứng dụng hay nhưng hay lag khi dịch"}'
curl -s -X POST http://localhost:8000/api/feedbacks/import-csv -b cookie.txt -F "file=@sample.csv"
curl -s "http://localhost:8000/api/feedbacks?limit=5&offset=0" -b cookie.txt
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| CSV người dùng thực có encoding lạ (UTF-16…) | Thêm sniff encoding vào service, entry nhỏ |
| Filter category trên JSONB chậm/khó | Dataset ≤1500 nên chấp nhận full scan; chỉ entry nếu phải đổi cấu trúc cột |
| File quá lớn (memory) | Stream từng row thay vì load cả file — làm ngay nếu gặp, không cần entry |
