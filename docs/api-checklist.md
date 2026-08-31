# API Checklist — VoC OS (AI Feedback Agent)

> **Quy tắc đồng bộ (Hard rule #10 — AGENTS.md):** thêm/sửa/xóa endpoint, đổi request/response schema hay auth → BẮT BUỘC cập nhật bảng dưới trong cùng commit; đổi phía FE (nối/sửa call API) cũng cập nhật 2 cột cuối. Agent tự đập vào checklist này, không cần nhắc.
>
> List này là **bản đồ nối FE ↔ BE** cho toàn bộ surface backend expose (`backend/app/main.py` + `backend/app/api/routes/*`).

Snapshot: 2026-08-30 (phase 28 / FE-10 — Activity Center + scoped analysis) · Nguồn chân lý BE: `backend/app/main.py`, `backend/app/api/routes/*` · FE: `frontend/app/**`

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
| ✅ | GET | `/api/imports` | pm \| operations | Queue import, filter `product_id` + lặp `status`, action-first ordering | ✅ | `ActivityProvider` poll; queue ba nhóm trong navbar Activity Sheet |
| ✅ | POST | `/api/imports` | pm \| operations | Upload CSV → lưu raw + deterministic profile/sample đã sanitize → 201 `profile_ready`; **không gọi LLM**. 409 `active_import_exists` | ✅ | Dialog `/feedbacks`; thành công đóng dialog và mở `?activity=import:<id>` |
| ✅ | GET | `/api/imports/{import_id}` | pm \| operations | Chi tiết import + profile/report/progress fields | ✅ | Import detail trong Activity Sheet, poll khi mapping/import đang chạy |
| ✅ | GET | `/api/imports/{import_id}/preview` | pm \| operations | Profile/sample đã sanitize; không trả raw feedback | ✅ | Bước “Preview cấu trúc”, badge “Chưa gọi AI” |
| ✅ | POST | `/api/imports/{import_id}/mapping/proposal` | pm \| operations | Paid gate riêng → 202; claim atomically, chống double-click, reclaim sau 5 phút; fail về `profile_ready` | ✅ | Cost receipt + AlertDialog trước khi gọi AI mapping |
| ✅ | GET | `/api/imports/{import_id}/mapping` | pm \| operations | Proposal mapping đang chờ Gate #1 | ✅ | Mapping table/remap controls trong Activity Sheet |
| ✅ | POST | `/api/imports/{import_id}/mapping/decision` | pm \| operations | Human chốt mapping → 202 `importing`; FE poll detail đến `imported\|failed` | ✅ | Mapping review + import progress/report trong Activity Sheet |
| ✅ | POST | `/api/imports/{import_id}/cancel` | pm \| operations | Chỉ draft/review/failed; xóa raw file đúng storage root → `cancelled` | ✅ | Nút Hủy import trong detail |
| ✅ | GET | `/api/feedbacks` | pm \| operations | List phân trang + filter cũ và `import_id`, `analysis_state=pending\|completed` | ✅ | Trang `/feedbacks`; Activity Sheet dùng scope import để chọn analysis items |
| ✅ | GET | `/api/feedbacks/{feedback_id}` | pm \| operations | Chi tiết feedback; `feedback_text` (đã sanitize) là dữ liệu phân tích — **raw_content KHÔNG BAO GIỜ ra response** (toggle include_raw đã bỏ) | 🔶 | Trang chi tiết `/feedbacks/[id]` — dùng feedback_text thay sanitized_content |
| ✅ | GET | `/api/feedbacks/{feedback_id}/similar` | pm \| operations | Cosine nearest-neighbor exact scan quanh embedding của 1 feedback (`k` ≤ 50, snippet từ feedback_text); **409** khi chưa có embedding | ✅ | Panel "Phản hồi tương tự" — shape snippet giữ nguyên |
| ✅ | POST | `/api/analysis/runs/preview` | pm \| operations | Preview selected/batch trong đúng import; cap 100, token estimate + logical calls + max attempts | ✅ | Cost receipt trong Activity Sheet |
| ✅ | POST | `/api/analysis/runs` | pm \| operations | Body bắt buộc; selected/batch + `import_id` + `confirmed_item_count`; claim exact scope; lệch → 409 `selection_changed` | ✅ | AlertDialog xác nhận paid run trong Activity Sheet; không còn global trigger |
| ✅ | GET | `/api/analysis/runs` | pm \| operations | Queue/history run cho navbar | ✅ | `ActivityProvider` poll dùng chung cho navbar/Sheet/mascot tương lai |
| ✅ | GET | `/api/analysis/runs/{run_id}` | pm \| operations | Progress một run: status, processed/total, error + snapshot cấu hình | ✅ | Cùng trang — `useRunProgress` poll |
| ✅ | POST | `/api/analysis/runs/{run_id}/cancel` | pm \| operations | Request dừng sau item/chunk hiện tại; unclaim phần chưa chạy | ✅ | Run detail trong Activity Sheet |
| ✅ | GET | `/api/analysis/runs/{run_id}/results` | pm \| operations | Kết quả theo run, phân trang; item chưa xử lý có `ai_analysis` null | 🔶 | Cùng trang — FE đọc labels từ JSONB mới |
| ✅ | POST | `/api/clusters/run` | pm \| operations | Chạy lại toàn bộ clustering HDBSCAN cosine + LLM naming — idempotent trong 1 transaction (C5) | ✅ | Nút "Tạo lại phân cụm" tại `/clusters` |
| ✅ | GET | `/api/clusters` | pm \| operations | Danh sách cụm theo C1 (`sort=feedback_count\|growth_ratio\|recent`, kèm `sample_feedback_ids` ≤5) | ✅ | Trang `/clusters` — giữ nguyên hợp đồng |
| ✅ | GET | `/api/reports/summary` | pm \| operations | Báo cáo tổng hợp PM thuần SQL theo C4 — `?days=7\|30\|90`; severity/sentiment/topics đọc từ `ai_analysis` JSONB; `totals` bỏ `pending_review_count` | 🔶 | Trang `/reports` + `/dashboard` — totals shape đổi |
| ✅ | GET | `/api/reports/kpis` | pm \| operations | **KPIs (plan 27):** 3-latency (time_to_listen/insight/action, median percentile_cont) + evaluation 3 gate — LISTEN mapping acceptance, UNDERSTAND approval/evidence-grounding, ACT acceptance/impact-effort agreement/matrix displacement + closed-loop impact_checks; thuần SQL, 200 với null khi chưa đủ data | ⬜ | — |
| ✅ | POST | `/api/agent/runs` | pm \| operations | **UNDERSTAND (plan 25):** trigger investigation `{product_id, question, trigger_type?}` → 200 `{run_id}` ngay; graph LangGraph chạy nền (planner → tool từ registry → record evidence → evaluator → synthesizer, budget `UNDERSTAND_LLM_BUDGET_PER_RUN=18` call, MAX_ITERATIONS=8) tới interrupt Gate #2 | ⬜ | — (FE Understand series sau) |
| ✅ | GET | `/api/agent/runs/{run_id}` | pm \| operations | Trạng thái run (AnalysisRun: status/error/snapshot) + `pending_approval` chứa interrupt payload `{insight, evidence, options}` khi graph đậu chờ human | ⬜ | — |
| ✅ | POST | `/api/agent/runs/{run_id}/decision` | pm \| operations | **Gate #2 (VoC OS §43):** `approve` \| `edit` (`edited_insight` re-sanitize) \| `investigate_more` (graph quay lại planner, insight status=investigating) \| `reject`; reviewer_id từ token. 404 thread chưa start · 409 thread completed · 503 checkpoint down | ⬜ | — |
| ✅ | GET | `/api/insights` | pm \| operations | Insights shape MỚI: finding/finding_confidence tách hypothesis (§41), affected_context/impact/limitations, evidence mở rộng thành `{evidence_id, statement, source_tool}` (§38); filter `?product_id=` `?status_filter=` | ⬜ | — |
| ✅ | POST | `/api/insights/{insight_id}/actions/generate` | pm \| operations | **ACT (plan 26):** LLM routing 8 business functions (relevance ≥ `ACT_RELEVANCE_THRESHOLD` → candidate) + estimates + priority deterministic → `{actions_created, functions_skipped}`; **409** nếu insight chưa approved/edited (§44); idempotent — action đã human-touch giữ nguyên | ⬜ | — (FE Act series sau) |
| ✅ | GET | `/api/insights/{insight_id}/actions` | pm \| operations | Portfolio actions (sort priority desc) + `matrix` grouping quadrant theo X=effort, Y=impact (quick_wins/strategic_investments/low_priority/reconsider — §50) | ⬜ | — |
| ✅ | POST | `/api/insights/{insight_id}/actions` | pm \| operations | Human tự thêm action → 201, priority tính cùng công thức deterministic, status `accepted` | ⬜ | — |
| ✅ | PATCH | `/api/actions/{action_id}` | pm \| operations | **Gate #3 (VoC OS §51–52):** human override scores → ghi `human_*` (agent value GIỮ NGUYÊN làm evaluation data) + `override_reason`; priority TÍNH LẠI deterministic từ effective values; status edited/accepted/rejected | ⬜ | — |

**Đã drop (phase 21) — trở lại shape mới ở plans 22/25/26/27:** `/api/sources` (GET/POST/PATCH) · `/api/reviews/{id}` · `/api/corrections/{id}` · `/api/insights/run` · `/api/insights` · `/api/reports/kpis` · `/api/agent/runs` + status/decision.

## Quy ước chung

- **Roles:** chỉ `pm` và `operations`; register mở (role mặc định `operations` — P1.5).
- **Bộ lỗi chuẩn:** 401 sai/thiếu credentials · 403 sai role · 404 thiếu row · 409 trạng thái không hợp lệ · 422 body sai schema · 500 generic (không leak chi tiết).
- **PII boundary:** `raw_content` KHÔNG BAO GIỜ xuất hiện trong response nào; `feedback_text` (đã sanitize) là dữ liệu phân tích hợp lệ; log chỉ method + path.
- **Routing FE→BE:** mọi request `/api/*` từ browser được Next.js rewrite về FastAPI `http://127.0.0.1:8000/api/*` (same-origin giữ cookie httpOnly — `frontend/next.config.ts`). FE gọi qua helper `apiFetch` (`frontend/lib/api.ts`) + React Query hooks.
- **Swagger:** `http://localhost:8000/docs` khi chạy `uvicorn app.main:app`.
