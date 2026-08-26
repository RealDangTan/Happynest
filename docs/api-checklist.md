# API Checklist — AI Feedback Agent

> **Quy tắc đồng bộ (Hard rule #10 — AGENTS.md):** thêm/sửa/xóa endpoint, đổi request/response schema hay auth → BẮT BUỘC cập nhật bảng dưới trong cùng commit; đổi phía FE (nối/sửa call API) cũng cập nhật 2 cột cuối. Agent tự đập vào checklist này, không cần nhắc.
>
> List này là **bản đồ nối FE ↔ BE** — đủ 21/21 endpoint mà backend expose (`backend/app/main.py` + `backend/app/api/routes/*`, không có route nào khác).

Snapshot: 2026-08-26 · Nguồn chân lý BE: `backend/app/main.py`, `backend/app/api/routes/*` · FE: `frontend/app/**`, `frontend/hooks/*`

Chú thích:
- **Trạng thái (BE):** ✅ production · 🚧 stub 501 — *không còn dòng nào từ 2026-08-26: plans 14–16 đã thay hết stub*
- **Trên FE:** ✅ đã nối · 🔶 đã có hook/API client nhưng chưa gắn UI · ⬜ chưa nối

## Bảng endpoint

| Trạng thái | Method | Endpoint | Auth | Tác dụng | Trên FE | Vị trí trên FE |
|---|---|---|---|---|---|---|
| ✅ | GET | `/api/health` | public | Health check: DB (`SELECT 1`), `structured_output_mode`, LLM/embedding model, `pii_mode` | ⬜ | — (chỉ cần khi debug deploy) |
| ✅ | POST | `/api/auth/token` | public | Đăng nhập (OAuth2 password form, username = email) → JWT vào cookie httpOnly SameSite=Lax + `TokenOut` body | ✅ | Trang `/login` — `frontend/app/login/page.tsx` |
| ✅ | GET | `/api/auth/me` | cookie/Bearer | Thông tin user hiện tại (email, role) | ✅ | Guard toàn khu `(app)` + header — `frontend/app/(app)/layout.tsx` (hook `useMe`) |
| ✅ | POST | `/api/feedbacks` | pm \| operations | Ingest 1 feedback đơn lẻ → 201 (chỉ lưu `raw_content`; sanitize chạy ở pipeline) | ✅ | Dialog "Nhập liệu" trong trang Feedbacks — `frontend/app/(app)/feedbacks/data-entry-dialog.tsx` |
| ✅ | POST | `/api/feedbacks/import-csv` | pm \| operations | Import CSV multipart (utf-8-sig chống BOM Excel) → `CsvImportReport` lỗi theo dòng, không abort cả file | ✅ | Cùng dialog trên (tab import CSV) — `data-entry-dialog.tsx` |
| ✅ | GET | `/api/feedbacks` | pm \| operations | List phân trang (`limit` ≤100, `offset`) + filter `review_status` / `severity` / `category` | ✅ | Trang `/feedbacks` — `frontend/app/(app)/feedbacks/page.tsx` (hook `useFeedbacks`) |
| ✅ | GET | `/api/feedbacks/{feedback_id}` | pm \| operations | Chi tiết feedback; mặc định KHÔNG kèm `raw_content` (ranh giới PII), chỉ trả khi `?include_raw=true` | ✅ | Trang chi tiết `/feedbacks/[id]` — `frontend/app/(app)/feedbacks/[id]/page.tsx` (hook `useFeedbackDetail`) |
| ✅ | GET | `/api/feedbacks/{feedback_id}/similar` | pm \| operations | Cosine nearest-neighbor exact scan quanh embedding của 1 feedback (`k` ≤ 50, snippet sanitized); **409** khi chưa có embedding → UI hiện Empty | ✅ | Panel "Phản hồi tương tự" cùng trang `[id]/page.tsx` (hook `useSimilarFeedbacks`) |
| ✅ | GET | `/api/sources` | pm \| operations | List toàn bộ nguồn registry (kể cả inactive — UI tự lọc theo flag), order theo tên | ✅ | Select nguồn + wizard — `frontend/app/(app)/feedbacks/data-entry-dialog.tsx` (hook `useSources`) |
| ✅ | POST | `/api/sources` | pm \| operations | Đăng ký nguồn mới `{name ≤100, description? ≤500}` → 201; trùng tên → 409 | ✅ | Wizard 2 bước trong dialog trên (mutation `useCreateSource`) |
| ✅ | PATCH | `/api/sources/{source_id}` | pm \| operations | Bật/tắt nguồn `{is_active}` (không DELETE — feedback trỏ source bằng string) | ⬜ | Chưa có UI quản lý nguồn riêng (backlog sau P1) |
| ✅ | POST | `/api/analysis/runs` | pm \| operations | Tạo run batch phân loại + đẩy job nền (`BackgroundTasks`) → 201 `{run_id}` ngay; idempotent (chỉ nhặt row chưa có run) | ✅ | Trang `/analysis` — nút "Chạy phân loại" qua AlertDialog confirm (`useTriggerRun`) rồi `router.replace(?run=)` |
| ✅ | GET | `/api/analysis/runs/{run_id}` | pm \| operations | Progress một run: status, processed/total, error + snapshot cấu hình lúc tạo run (`pipeline_version`, `llm_model`, `prompt_version`, `embedding_model` — OQ-7) | ✅ | Cùng trang — `useRunProgress` poll 4s khi running, dừng khi completed/failed |
| ✅ | GET | `/api/analysis/runs/{run_id}/results` | pm \| operations | Kết quả phân loại theo run, phân trang (item chưa xử lý xong có labels NULL) | ✅ | Cùng trang — bảng kết quả phân trang Trước/Sau (`useRunResults`) |
| ✅ | POST | `/api/reviews/{feedback_id}` | pm \| operations | HITL duyệt/sửa/từ chối (`approve\|edit\|reject`) qua LangGraph interrupt/resume + Postgres checkpoint | ✅ | Thanh ReviewActions tại `/feedbacks/[id]` khi pending — `review-actions.tsx` (`useSubmitReview`); kèm toggle raw qua `useFeedbackRaw` (call site `include_raw` DUY NHẤT) |
| ✅ | POST | `/api/corrections/{feedback_id}` | pm \| operations | Sửa nhãn trực tiếp (thuần DB) trên feedback đã classify + ghi `CorrectionExample` nuôi few-shot loop | ✅ | Dialog "Sửa nhãn" cùng trang khi đã classify — `correction-dialog.tsx` (`useSubmitCorrection`) |
| ✅ | POST | `/api/clusters/run` | pm \| operations | Chạy lại toàn bộ clustering HDBSCAN cosine + LLM naming — idempotent trong 1 transaction (xoá insights cũ → clusters cũ → tạo mới), response C5 `{clusters_upserted, assigned_count, unassigned_count, duration_ms}` (plan 14) | ✅ | Nút "Tạo lại phân cụm" tại `/clusters` qua AlertDialog cảnh báo rebuild (`useRunClustering`), toast tổng kết C5 |
| ✅ | GET | `/api/clusters` | pm \| operations | Danh sách cụm theo C1 (`sort=feedback_count\|growth_ratio\|recent`, kèm `sample_feedback_ids` ≤5); chưa từng run → `items: []`. Lưu ý: data demo hiện chưa có nhóm chủ đề thật → hay ra rỗng/noise cao (decisions 2026-08-26, dời evidence P5) | ✅ | Trang `/clusters` — card grid + sort URL param (`useClusters`); sentinel 9.99 hiển thị chữ "Mới" |
| ✅ | POST | `/api/insights/run` | pm \| operations | Sinh insight evidence-backed cho các cụm ưu tiên cao (`INSIGHT_MAX_CLUSTERS` cap, default 10) — replace-all idempotent; **409** "Chưa có cụm nào. Chạy POST /api/clusters/run trước." khi bảng clusters rỗng; response C6 `{insights_generated, duration_ms}` + `skipped` ngoài hợp đồng (được phép); LLM bịa evidence id → server whitelist lọc, rỗng → fallback 3 member ưu tiên cao (plan 15) | ✅ | Nút "Sinh insight" tại `/insights` — 409 → Alert đúng chữ server + link `/clusters`; loading disable ~1 phút; toast tổng kết (FE-06b) |
| ✅ | GET | `/api/insights` | pm \| operations | Danh sách insight theo C2 — evidence_ids mở rộng thành `{feedback_id, snippet ≤200 từ sanitized_content (không bao giờ raw), severity, created_at}`, ≤5/insight; chưa từng run → `items: []`; `review_status` luôn `unreviewed` v1 (non-goal đổi trạng thái — UI ẨN badge này, OQ-11) | ✅ | Trang `/insights` card list dọc + khối "Hành động đề xuất" + evidence blockquote link `/feedbacks/{id}` (FE-06b) |
| ✅ | GET | `/api/reports/summary` | pm \| operations | Báo cáo tổng hợp PM thuần SQL theo C4 — `?days=7\|30\|90` (khác → 422), cửa sổ event-time; `by_sentiment` có 4 key gồm `mixed` (decisions 2026-08-26); `emerging` rỗng khi chưa chạy clustering là hợp lệ. Response mẫu: `docs/evidence/reports-summary-sample.json`. Warm ~1.2s trên pooler cloud (RTT, không phải SQL — decisions cùng ngày) | ✅ | Trang `/reports` (selector days URL param) VÀ `/dashboard` days=30 — dùng chung queryKey cache share, số liệu khớp 1:1 (FE-06b) |

## Quy ước chung

- **Roles:** chỉ `pm` và `operations`; register DISABLED — user chỉ tạo bằng `scripts/seed_users.py`.
- **Bộ lỗi chuẩn:** 401 sai/thiếu credentials · 403 sai role · 404 thiếu row · 409 trạng thái không hợp lệ · 422 body sai schema · 500 generic (không leak chi tiết).
- **PII boundary:** `raw_content` không bao giờ xuất hiện trong response trừ `GET /feedbacks/{id}?include_raw=true`; log chỉ method + path.
- **Routing FE→BE:** mọi request `/api/*` từ browser được Next.js rewrite về FastAPI `http://127.0.0.1:8000/api/*` (same-origin giữ cookie httpOnly — `frontend/next.config.ts`). FE gọi qua helper `apiFetch` (`frontend/lib/api.ts`) + React Query hooks trong `frontend/hooks/`.
- **Swagger:** `http://localhost:8000/docs` khi chạy `uvicorn app.main:app --reload`.
