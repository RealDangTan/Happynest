# API Checklist — VoC OS (AI Feedback Agent)

> **Quy tắc đồng bộ (Hard rule #10 — AGENTS.md):** thêm/sửa/xóa endpoint, đổi request/response schema hay auth → BẮT BUỘC cập nhật bảng dưới trong cùng commit; đổi phía FE (nối/sửa call API) cũng cập nhật 2 cột cuối. Agent tự đập vào checklist này, không cần nhắc.
>
> List này là **bản đồ nối FE ↔ BE** — đủ 22/22 endpoint mà backend expose (`backend/app/main.py` + `backend/app/api/routes/*`, không có route nào khác).

Snapshot: 2026-08-28 (phase 22 — LISTEN) · Nguồn chân lý BE: `backend/app/main.py`, `backend/app/api/routes/*` · FE: `frontend/app/**` (🔶 = đã nối nhưng shape/API đổi sau reshape — series FE mới sẽ nối lại)

> ⚠️ **RE-PLAN 2026-08-28:** series 21–27 ([`plans/21-27-voc-os-index.md`](plans/21-27-voc-os-index.md)) viết lại surface BE theo kiến trúc VoC OS. Endpoint drop: `/api/sources`, `/api/reviews`, `/api/corrections`, `/api/insights`, `/api/reports/kpis`, `/api/agent/*` cũ, `/api/feedbacks/import-csv` (phase 22 thay bằng `/api/imports` + Gate #1). Sẽ trở lại shape mới ở plans 25/26/27.

Chú thích:
- **Trạng thái (BE):** ✅ production
- **Trên FE:** ✅ đã nối, hợp đồng giữ nguyên · 🔶 đã nối nhưng shape/API đã đổi (FE cần update series sau) · ⬜ chưa nối

## Bảng endpoint

| Trạng thái | Method | Endpoint | Auth | Tác dụng | Trên FE | Vị trí trên FE |
|---|---|---|---|---|---|---|
| ✅ | GET | `/api/health` | public | Health check: DB (`SELECT 1`), `structured_output_mode`, LLM/embedding model, `pii_mode` | ⬜ | — (chỉ cần khi debug deploy) |
| ✅ | POST | `/api/auth/token` | public | Đăng nhập (OAuth2 password form, username = email) → JWT vào cookie httpOnly SameSite=Lax + `TokenOut` body | ✅ | Trang `/login` — `frontend/app/login/page.tsx`; gọi lại sau đăng ký ở `/register` |
| ✅ | POST | `/api/auth/register` | public | Đăng ký email/mật khẩu → `201 UserOut` role `operations`; trùng email 409; sai dạng 422 | ✅ | Trang `/register` — `frontend/app/register/page.tsx` |
| ✅ | POST | `/api/auth/logout` | public (idempotent) | Xoá cookie `access_token` (Max-Age=0) → 204 | ✅ | Menu avatar sidebar footer — `frontend/app/(app)/layout.tsx` |
| ✅ | GET | `/api/auth/me` | cookie/Bearer | Thông tin user hiện tại (email, role) | ✅ | Guard toàn khu `(app)` + header — `frontend/app/(app)/layout.tsx` (hook `useMe`) |
| ✅ | GET | `/api/products` | pm \| operations | List products (product = workspace — quyết định re-plan 2026-08-28) | ⬜ | — (product switcher FE series sau) |
| ✅ | POST | `/api/products` | pm \| operations | Tạo product `{name, description?}` → 201; trùng tên → 409 | ⬜ | — |
| ✅ | GET | `/api/products/{product_id}` | pm \| operations | Chi tiết product | ⬜ | — |
| ✅ | PATCH | `/api/products/{product_id}` | pm \| operations | Sửa name/description; trùng tên → 409 | ⬜ | — |
| ✅ | GET | `/api/products/{product_id}/schema` | pm \| operations | Schema ACTIVE hiện hành (definition fields + version) + core fields; `schema: null` khi chưa bootstrap | ⬜ | — |
| ✅ | GET | `/api/products/{product_id}/schema/versions` | pm \| operations | Toàn bộ version schema (mới nhất trước) + active_version | ⬜ | — |
| ✅ | GET | `/api/products/{product_id}/schema/coverage` | pm \| operations | Coverage per product field từ `data` JSONB (VoC OS §19) — `records_with_field/total` | ⬜ | — |
| ✅ | POST | `/api/feedbacks` | pm \| operations | Ingest 1 feedback đơn lẻ — sanitize tại ingest, gắn product mặc định + JSONB zones (`data`, `source_meta`) | 🔶 | Dialog "Nhập liệu" trang Feedbacks — response shape mới (feedback_text/occurred_at/data) |
| ✅ | GET | `/api/taxonomies` | pm \| operations | Tree taxonomy product (`?product_id=`, filter `?status_filter=`) — canonical + emerging (VoC OS §20) | ⬜ | — |
| ✅ | GET | `/api/taxonomies/review` | pm \| operations | Hàng chờ emerging theme `pending_review` (accumulate evidence — §21) | ⬜ | — |
| ✅ | POST | `/api/taxonomies/review/{taxonomy_id}` | pm \| operations | **Human Gate taxonomy:** `approve` (lên canonical) \| `merge` (`merge_into_id` bắt buộc — feedback topics redirect) \| `reject`. 409 node không ở pending_review; 422 merge thiếu target | ⬜ | — |
| ❌ | POST | `/api/feedbacks/import-csv` | — | **ĐÃ BỎ phase 22** — thay bằng `POST /api/imports` (LISTEN pipeline) | ❌ | Route không còn tồn tại |
| ✅ | GET | `/api/imports` | pm \| operations | List import lô (status: pending/mapping_review/imported/failed) | ⬜ | — |
| ✅ | POST | `/api/imports` | pm \| operations | **LISTEN (plan 22):** upload CSV multipart → lưu raw (disk — decisions 2026-08-28) → deterministic profile → LLM schema mapping proposal → 201 `ImportOut` status `mapping_review`. 409 khi product đang có import chờ review; 422 sai đuôi; 502 LLM fail | ⬜ | — (FE Mapping Review series sau) |
| ✅ | GET | `/api/imports/{import_id}` | pm \| operations | Chi tiết 1 import | ⬜ | — |
| ✅ | GET | `/api/imports/{import_id}/mapping` | pm \| operations | Proposal mapping đang chờ Gate #1 — per source_field: MAP/PROMOTE/SOURCE_META/IGNORE/AMBIGUOUS + confidence + reason (VoC OS §10–11) | ⬜ | — |
| ✅ | POST | `/api/imports/{import_id}/mapping/decision` | pm \| operations | **Gate #1 (VoC OS §12):** human quyết per field `approve\|remap\|promote\|demote\|ignore` (phủ ĐỦ mọi source_field) → (tùy) activate schema version mới → parse + sanitize + import feedback rows. 422 AMBIGUOUS approve máy móc / thiếu-dư field / 2 cột trùng target / thiếu feedback_text; 409 re-decision; `?default_source=` khi CSV không có cột source | ⬜ | — |
| ✅ | GET | `/api/feedbacks` | pm \| operations | List phân trang (`limit` ≤100, `offset`) + filter `product_id` / `severity` / `sentiment` / `topic` (JSONB ai_analysis) / `source` | 🔶 | Trang `/feedbacks` — filter cũ (review_status/category) đã bỏ |
| ✅ | GET | `/api/feedbacks/{feedback_id}` | pm \| operations | Chi tiết feedback; `feedback_text` (đã sanitize) là dữ liệu phân tích — **raw_content KHÔNG BAO GIỜ ra response** (toggle include_raw đã bỏ) | 🔶 | Trang chi tiết `/feedbacks/[id]` — dùng feedback_text thay sanitized_content |
| ✅ | GET | `/api/feedbacks/{feedback_id}/similar` | pm \| operations | Cosine nearest-neighbor exact scan quanh embedding của 1 feedback (`k` ≤ 50, snippet từ feedback_text); **409** khi chưa có embedding | ✅ | Panel "Phản hồi tương tự" — shape snippet giữ nguyên |
| ✅ | POST | `/api/analysis/runs` | pm \| operations | Tạo run batch phân loại + đẩy job nền → 201 `{run_id}` ngay; marker "đã xử lý" = `ai_analysis IS NOT NULL`; pipeline_version `v2` (reshape) | ✅ | Trang `/analysis` — giữ nguyên hợp đồng |
| ✅ | GET | `/api/analysis/runs/{run_id}` | pm \| operations | Progress một run: status, processed/total, error + snapshot cấu hình | ✅ | Cùng trang — `useRunProgress` poll |
| ✅ | GET | `/api/analysis/runs/{run_id}/results` | pm \| operations | Kết quả theo run, phân trang; item chưa xử lý có `ai_analysis` null | 🔶 | Cùng trang — FE đọc labels từ JSONB mới |
| ✅ | POST | `/api/clusters/run` | pm \| operations | Chạy lại toàn bộ clustering HDBSCAN cosine + LLM naming — idempotent trong 1 transaction (C5) | ✅ | Nút "Tạo lại phân cụm" tại `/clusters` |
| ✅ | GET | `/api/clusters` | pm \| operations | Danh sách cụm theo C1 (`sort=feedback_count\|growth_ratio\|recent`, kèm `sample_feedback_ids` ≤5) | ✅ | Trang `/clusters` — giữ nguyên hợp đồng |
| ✅ | GET | `/api/reports/summary` | pm \| operations | Báo cáo tổng hợp PM thuần SQL theo C4 — `?days=7\|30\|90`; severity/sentiment/topics đọc từ `ai_analysis` JSONB; `totals` bỏ `pending_review_count` | 🔶 | Trang `/reports` + `/dashboard` — totals shape đổi |

**Đã drop (phase 21) — trở lại shape mới ở plans 22/25/26/27:** `/api/sources` (GET/POST/PATCH) · `/api/reviews/{id}` · `/api/corrections/{id}` · `/api/insights/run` · `/api/insights` · `/api/reports/kpis` · `/api/agent/runs` + status/decision.

## Quy ước chung

- **Roles:** chỉ `pm` và `operations`; register mở (role mặc định `operations` — P1.5).
- **Bộ lỗi chuẩn:** 401 sai/thiếu credentials · 403 sai role · 404 thiếu row · 409 trạng thái không hợp lệ · 422 body sai schema · 500 generic (không leak chi tiết).
- **PII boundary:** `raw_content` KHÔNG BAO GIỜ xuất hiện trong response nào; `feedback_text` (đã sanitize) là dữ liệu phân tích hợp lệ; log chỉ method + path.
- **Routing FE→BE:** mọi request `/api/*` từ browser được Next.js rewrite về FastAPI `http://127.0.0.1:8000/api/*` (same-origin giữ cookie httpOnly — `frontend/next.config.ts`). FE gọi qua helper `apiFetch` (`frontend/lib/api.ts`) + React Query hooks.
- **Swagger:** `http://localhost:8000/docs` khi chạy `uvicorn app.main:app`.