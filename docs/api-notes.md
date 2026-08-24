# API Notes — Backend Foundation (chốt 2026-08-25)

Trạng thái thực tế sau Phase 12. Base URL dev: `http://127.0.0.1:8000`.
Swagger tương tác: `/docs`. Xác thực: cookie httpOnly `access_token` (Next.js proxy)
HOẶC header `Authorization: Bearer <jwt>` song song (curl/Swagger/test) —
cookie ưu tiên khi cả hai có mặt (decisions.md 2026-08-24).

## Bảng endpoint đã ship

| Method | Path | Role | Body / Query chính | Response chính |
|---|---|---|---|---|
| GET | `/api/health` | công khai | — | `{status, app_env, db, structured_output_mode, llm_model, embedding_model, pii_mode}` |
| POST | `/api/auth/token` | công khai | form `username`, `password` (OAuth2) | `{access_token, token_type:"bearer"}` + Set-Cookie httpOnly |
| GET | `/api/auth/me` | pm, operations | — | `{id, email, role}` |
| POST | `/api/feedbacks` | pm, operations | `{source, content, external_ref?, created_at?}` — sanitize chạy ngay lúc ingest | 201 `FeedbackOut` (KHÔNG có raw mặc định; có `pii_detected`) |
| POST | `/api/feedbacks/import-csv` | pm, operations | multipart file CSV cột `source,content[,external_ref][,created_at]`; UTF-8/BOM OK | 200 `{imported, failed, errors:[{row, reason}]}` — dòng lỗi không cản dòng hợp lệ |
| GET | `/api/feedbacks` | pm, operations | `limit(≤100), offset, category, severity, review_status, source?` | `{total, limit, offset, items:[FeedbackOut]}` |
| GET | `/api/feedbacks/{id}` | pm, operations | `include_raw=true` → mới trả raw | `FeedbackOut`; 404 nếu không tồn tại |
| GET | `/api/feedbacks/{id}/similar` | pm, operations | `k` (1–50, default 5) | `[{…FeedbackOut, score}]` cosine GIẢM dần, loại self; 409 nếu row chưa có embedding |
| POST | `/api/analysis/runs` | pm, operations | — (snapshot cấu hình tự động vào row run) | 201 `{run_id}` NGAY LẬC TỨC; job nền qua BackgroundTasks |
| GET | `/api/analysis/runs/{id}` | pm, operations | — | `{status: running\|completed\|failed, processed_count, total_count, error, started_at, completed_at}` |
| GET | `/api/analysis/runs/{id}/results` | pm, operations | `limit(1–100), offset` | trang FeedbackOut của CÁC row thuộc run (labels/severity/confidence/review flag) |
| GET | `/api/clusters` · `/api/insights` | pm, operations | — | **501 stub** — giai đoạn sau (clustering/insight) |
| POST | `/api/reviews/{feedback_id}` · `/api/corrections/{feedback_id}` | pm, operations | — | **501 stub** — HITL flow + few-shot loop giai đoạn sau |
| GET | `/api/reports/summary` | pm, operations | — | **501 stub** — báo cáo PM giai đoạn sau |

Lỗi chuẩn: 401 vô danh (khác 403 role sai — route-level guard `require_role`),
404 id lạ, 409 thiếu embedding trên `/similar`, 422 validation (limit >100,
k ngoài 1–50, file không phải CSV…).

## Hành vi pipeline hiện hành

- **Structured output mode**: `json_schema` strict (Mode A, temperature=0) là
  đường chính — xác nhận chạy được với model hiện hành bằng spike S2 + unit test;
  runtime TỰ DETECT lần gọi đầu (`GET /api/health` phản ánh sau khi process đã
  classify ít nhất 1 row); provider từ chối `response_format` → fallback
  prompt-JSON + validate Pydantic (Mode B), mọi chuyển mode được ghi log.
- **PROMPT_VERSION = `"v1"`** (hằng trong `app/services/classifier.py`,
  mirror ở `Settings.PROMPT_VERSION`); mỗi call classify ghi `llm_call_logs`
  với `prompt_version`, `model`, token counts, latency.
- **PIPELINE_VERSION = `"v1"`** (`app/jobs/analysis_runner.py`) — snapshot vào
  mỗi row `analysis_runs` cùng llm_model/prompt_version/embedding_model.
- **Công thức HITL** (`compute_requires_human_review`, decisions.md 2026-08-24):
  `severity==critical OR safety_issue OR pii_detected OR confidence < 0.60
  OR (severity ∈ {high,critical} AND confidence < 0.75)` — ngưỡng config qua env.
- **Runner idempotent/resumable**: marker "đã xử lý" = `categories IS NOT NULL`;
  resume CÙNG run bằng cách gọi lại `run_analysis(run_id)` trực tiếp (POST luôn
  tạo run MỚI — muốn heal run fail giữa chừng thì gọi hàm, xem decisions.md 2026-08-25).
- **PII boundary**: chỉ `sanitized_content` đi vào prompt LLM và response mặc định;
  `pii_entities` chỉ chứa metadata `{type,start,end,score}` — không text.

## Model đang dùng (.env của máy dev)

`LLM_MODEL=gemini-3-flash` (qua proxy OpenAI-compatible) ·
`EMBEDDING_MODEL=text-embedding-3-small` (1536 dims, pgvector cosine).
Đổi model chỉ cần sửa `.env` + tạo lại run — `analysis_runs` snapshot đúng
cấu hình từng lô để đối chiếu chất lượng giữa các model.
