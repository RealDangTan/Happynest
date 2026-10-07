# API Checklist — VoC OS (AI Feedback Agent)

> **Quy tắc đồng bộ (Hard rule #10 — AGENTS.md):** thêm/sửa/xóa endpoint, đổi request/response schema hay auth → BẮT BUỘC cập nhật bảng dưới trong cùng commit; đổi phía FE (nối/sửa call API) cũng cập nhật 2 cột cuối. Agent tự đập vào checklist này, không cần nhắc.
>
> List này là **bản đồ nối FE ↔ BE** cho toàn bộ surface backend expose (`backend/app/main.py` + `backend/app/api/routes/*`).

Snapshot: 2026-09-15 (FE-12 — six-screen rebuild per docs/design/2026-09-15-ui-flow) · Nguồn chân lý BE: `backend/app/main.py`, `backend/app/api/routes/*` · FE: `frontend/app/**`

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
| ✅ | POST | `/api/auth/logout` | public (idempotent) | Xoá cookie `access_token` (Max-Age=0) → 204 | ✅ | Menu avatar trên top navbar — `components/shell/account-menu.tsx` (FE-13) |
| ✅ | GET | `/api/auth/me` | cookie/Bearer | Thông tin user hiện tại (email, role) | ✅ | Guard toàn khu `(app)` + avatar top navbar (hook `useMe`) |
| ✅ | GET | `/api/products` | pm \| operations | List products (product = workspace — quyết định re-plan 2026-08-28) | ✅ | Product breadcrumb dropdown trên top navbar — `components/shell/top-navbar.tsx` (FE-13) |
| ✅ | POST | `/api/products` | pm \| operations | Tạo product `{name, description?}` → 201; trùng tên → 409 | ✅ | Dialog "Create product" từ breadcrumb — sau tạo → `/importer` (FE-13) |
| ✅ | GET | `/api/products/{product_id}` | pm \| operations | Chi tiết product | ⬜ | — |
| ✅ | PATCH | `/api/products/{product_id}` | **pm** (destructive — trước đây pm \| operations) | Sửa name/description; trùng tên → 409 | ✅ | Dialog Settings trong panel footer (FE-13) + "Rename product" từ breadcrumb dropdown (CRUD 2026-09-16) |
| ✅ | GET | `/api/products/{product_id}/schema` | pm \| operations | Schema ACTIVE hiện hành (definition fields + version) + core fields; `schema: null` khi chưa bootstrap | ⬜ | — |
| ✅ | GET | `/api/products/{product_id}/schema/versions` | pm \| operations | Toàn bộ version schema (mới nhất trước) + active_version | ⬜ | — |
| ✅ | GET | `/api/products/{product_id}/schema/coverage` | pm \| operations | Coverage per product field từ `data` JSONB (VoC OS §19) — `records_with_field/total` | ⬜ | — |
| ✅ | POST | `/api/feedbacks` | pm \| operations | Ingest 1 feedback đơn lẻ — sanitize tại ingest, gắn product mặc định + JSONB zones (`data`, `source_meta`) | 🔶 | Dialog "Nhập liệu" trang Feedbacks — response shape mới (feedback_text/occurred_at/data) |
| ✅ | GET | `/api/taxonomies` | pm \| operations | Tree taxonomy product (`?product_id=`, filter `?status_filter=`) — canonical + emerging (VoC OS §20) | ⬜ | — |
| ✅ | GET | `/api/taxonomies/review` | pm \| operations | Hàng chờ emerging theme `pending_review` (accumulate evidence — §21) | ⬜ | — |
| ✅ | POST | `/api/taxonomies/review/{taxonomy_id}` | pm \| operations | **Human Gate taxonomy:** `approve` (lên canonical) \| `merge` (`merge_into_id` bắt buộc — feedback topics redirect) \| `reject`. 409 node không ở pending_review; 422 merge thiếu target | ⬜ | — |
| ❌ | POST | `/api/feedbacks/import-csv` | — | **ĐÃ BỎ phase 22** — thay bằng `POST /api/imports` (LISTEN pipeline) | ❌ | Route không còn tồn tại |
| ✅ | GET | `/api/imports` | pm \| operations | Queue import, filter `product_id` + lặp `status`, action-first ordering | ✅ | `ActivityProvider` poll; rail "Files" trong `/vault` + "Current tasks — imports" tại `/importer` (FE-12) |
| ✅ | POST | `/api/imports` | pm \| operations | Upload CSV → lưu raw + deterministic profile/sample đã sanitize → 201 `profile_ready`; **không gọi LLM**. 409 `active_import_exists` | ✅ | Wizard bước 1 (File) tại `/importer` — "Upload and preview" (FE-12) |
| ✅ | GET | `/api/imports/{import_id}` | pm \| operations | Chi tiết import + profile/report/progress fields | ✅ | Wizard `/importer` (poll khi mapping/importing); StepResult receipt (FE-12) |
| ✅ | GET | `/api/imports/{import_id}/preview` | pm \| operations | Profile/sample đã sanitize; không trả raw feedback | ✅ | Wizard bước 2 (Preview) tại `/importer` — badge "No AI used yet" (FE-12) |
| ✅ | POST | `/api/imports/{import_id}/mapping/proposal` | pm \| operations | Paid gate riêng → 202; claim atomically, chống double-click, reclaim sau 5 phút; fail về `profile_ready` | ✅ | Cost receipt + AlertDialog trước khi gọi AI mapping |
| ✅ | GET | `/api/imports/{import_id}/mapping` | pm \| operations | Proposal mapping đang chờ Gate #1 | ✅ | Wizard bước 3 (Mapping, G1) tại `/importer` — bảng quyết định human (FE-12) |
| ✅ | POST | `/api/imports/{import_id}/mapping/decision` | pm \| operations | Human chốt mapping → 202 `importing`; FE poll detail đến `imported\|failed` | ✅ | Dialog "Confirm mapping & import" bước 3 → bước 4 Result (FE-12) |
| ✅ | POST | `/api/imports/{import_id}/cancel` | pm \| operations | Chỉ draft/review/failed; xóa raw file đúng storage root → `cancelled` | ✅ | Nút Cancel import trong Activity Sheet (FE-12 giữ nguyên) |
| ✅ | GET | `/api/feedbacks` | pm \| operations | List phân trang + filter cũ và `import_id`, `analysis_state=pending\|completed` | ✅ | Trang `/vault` (S02): rail Files + filters + selection + Analyze/Explore (FE-12) |
| ✅ | GET | `/api/feedbacks/{feedback_id}` | pm \| operations | Chi tiết feedback; `feedback_text` (đã sanitize) là dữ liệu phân tích — **raw_content KHÔNG BAO GIỜ ra response** (toggle include_raw đã bỏ) | 🔶 | Drawer D01 tại `/vault` — dùng feedback_text thay sanitized_content (FE-12) |
| ✅ | GET | `/api/feedbacks/{feedback_id}/similar` | pm \| operations | Cosine nearest-neighbor exact scan quanh embedding của 1 feedback (`k` ≤ 50, snippet từ feedback_text); **409** khi chưa có embedding | ✅ | Drawer D01 "Similar feedback" tại `/vault` (FE-12) |
| ✅ | POST | `/api/analysis/runs/preview` | pm \| operations | Preview selected/batch trong đúng import; cap 100, token estimate + logical calls + max attempts | ✅ | L05 analysis receipt dialog tại `/vault` — "Analyze pending items" (FE-12) |
| ✅ | POST | `/api/analysis/runs` | pm \| operations | Body bắt buộc; selected/batch + `import_id` + `confirmed_item_count`; claim exact scope; lệch → 409 `selection_changed` | ✅ | L05 receipt "Start analysis" tại `/vault` → progress card (FE-12) |
| ✅ | GET | `/api/analysis/runs` | pm \| operations | Queue/history run cho navbar | ✅ | ActivityProvider poll; Vault tự tìm running run theo import (FE-12) |
| ✅ | GET | `/api/analysis/runs/{run_id}` | pm \| operations | Progress một run: status, processed/total, error + snapshot cấu hình | ✅ | Vault progress card "Processing selected feedback" — `useRunProgress` poll (FE-12) |
| ✅ | POST | `/api/analysis/runs/{run_id}/cancel` | pm \| operations | Request dừng sau item/chunk hiện tại; unclaim phần chưa chạy | ✅ | Vault progress card "Stop analysis" (FE-12) |
| ✅ | GET | `/api/analysis/runs/{run_id}/results` | pm \| operations | Kết quả theo run, phân trang; item chưa xử lý có `ai_analysis` null | 🔶 | Chưa nối riêng — Vault đọc lại `/api/feedbacks` theo import (FE-12) |
| ✅ | POST | `/api/clusters/run` | pm \| operations | Chạy lại toàn bộ clustering HDBSCAN cosine + LLM naming — idempotent trong 1 transaction (C5) | ✅ | Nút "Tạo lại phân cụm" tại `/clusters` |
| ✅ | GET | `/api/clusters` | pm \| operations | Danh sách cụm theo C1 (`sort=feedback_count\|growth_ratio\|recent`, kèm `sample_feedback_ids` ≤5) | ✅ | Trang `/clusters` — giữ nguyên hợp đồng |
| ✅ | GET | `/api/reports/summary` | pm \| operations | Báo cáo tổng hợp PM thuần SQL theo C4 — `?days=7\|30\|90`; severity/sentiment/topics đọc từ `ai_analysis` JSONB; `totals` bỏ `pending_review_count` | 🔶 | Trang cũ chuyển sang `/reports/summary` (giữ nguyên); màn Reports mới FE-12 dùng `/api/insights` |
| ✅ | GET | `/api/reports/kpis` | pm \| operations | **KPIs (plan 27):** 3-latency (time_to_listen/insight/action, median percentile_cont) + evaluation 3 gate — LISTEN mapping acceptance, UNDERSTAND approval/evidence-grounding, ACT acceptance/impact-effort agreement/matrix displacement + closed-loop impact_checks; thuần SQL, 200 với null khi chưa đủ data | ⬜ | — |
| ✅ | POST | `/api/agent/runs` | pm \| operations | **UNDERSTAND (plan 25):** trigger investigation `{product_id, question, trigger_type?}` → 200 `{run_id}` ngay; graph LangGraph chạy nền (planner → tool từ registry → record evidence → evaluator → synthesizer, budget `UNDERSTAND_LLM_BUDGET_PER_RUN=18` call, MAX_ITERATIONS=8) tới interrupt Gate #2 | ✅ | S03 "Ask AI" tại `/data-graph` + trang Chat `/chat` (FE-12/FE-13) — hỏi về data đang scope |
| ✅ | GET | `/api/agent/runs/{run_id}` | pm \| operations | Trạng thái run (AnalysisRun: status/error/snapshot) + `pending_approval` chứa interrupt payload `{insight, evidence, options}` khi graph đậu chờ human; **`progress` mới (khi running): `{iteration, max_iterations, last_tool, llm_calls_used, llm_budget, evidence_count}` đếm từ Evidence/LlmCallLog để FE hiển thị tiến độ (HAX G9: calls used/budget); quyết định Gate #2 cuối (`approve/edit/reject`) chuyển run sang `completed`, `investigate_more` giữ `running` | ✅ | Activity Trace tại `/data-graph` + draft "Needs review" tại `/reports?run=` + progress live tại `/chat` — `useAgentRun` poll (FE-12/FE-13) |
| ✅ | GET | `/api/agent/runs/{run_id}/trace` | pm \| operations | **HAX G4/G16:** trace metadata-only các LLM call của run từ `llm_call_logs` (≤200 row, asc) — `{items: [{call_type, status "ok"\|"error", latency_ms, prompt_tokens, completion_tokens, model, prompt_version, error[:200], created_at}]}`; **KHÔNG prompt/response** (PII boundary plan 29); 404 run không tồn tại | ✅ | Live trace panel trong chat-thread + ActivityTrace `/data-graph` — `useAgentTrace` poll 2s (HAX plan) |
| ✅ | POST | `/api/agent/runs/{run_id}/decision` | pm \| operations | **Gate #2 (VoC OS §43):** `approve` \| `edit` (`edited_insight` re-sanitize) \| `investigate_more` (graph quay lại planner, insight status=investigating) \| `reject`; reviewer_id từ token. Quyết định cuối ghi `processed_count=1` + `completed_at`; 404 thread chưa start · 409 thread completed · 503 checkpoint down | ✅ | G2 bar tại `/reports` — Reject / Investigate more / Edit finding / Approve finding (FE-12; verify live 2026-09-15: approve → `insights_created`) |
| ✅ | GET | `/api/insights` | pm \| operations | Insights shape MỚI: finding/finding_confidence tách hypothesis (§41), affected_context/impact/limitations, evidence mở rộng thành `{evidence_id, statement, source_tool}` (§38); filter `?product_id=` `?status_filter=` | ✅ | S04 Reports list + report body + evidence panel tại `/reports` — `useInsights` (FE-12) |
| ✅ | POST | `/api/insights/{insight_id}/actions/generate` | pm \| operations | **ACT (plan 26):** LLM routing 8 business functions (relevance ≥ `ACT_RELEVANCE_THRESHOLD` → candidate) + estimates + priority deterministic → `{actions_created, functions_skipped, generation_error?}` (HAX G14: LLM fail trả `generation_error` thay vì nuốt im lặng); **409** nếu insight chưa approved/edited (§44); idempotent — action đã human-touch giữ nguyên | ✅ | Nút "Generate actions" tại `/reports` cho report approved/edited (FE-12) — hiện Alert lỗi khi `generation_error` |
| ✅ | GET | `/api/insights/{insight_id}/actions` | pm \| operations | Portfolio actions (sort priority desc) + `matrix` grouping quadrant theo X=effort, Y=impact (quick_wins/strategic_investments/low_priority/reconsider — §50) | ✅ | S05 Matrix 2×2 tại `/matrix` + bảng actions `/stakeholders` — `useActions` (FE-12) |
| ✅ | POST | `/api/insights/{insight_id}/actions` | pm \| operations | Human tự thêm action → 201, priority tính cùng công thức deterministic, status `accepted` | ✅ | Dialog "Add manual action" tại `/matrix` — nút cuối "Add and accept action" (FE-12) |
| ✅ | PATCH | `/api/actions/{action_id}` | pm \| operations | **Gate #3 (VoC OS §51–52):** human override scores → ghi `human_*` (agent value GIỮ NGUYÊN làm evaluation data) + `override_reason`; priority TÍNH LẠI deterministic từ effective values; status edited/accepted/rejected | ✅ | Drawer D02 tại `/matrix` — Reject / Save edits / Accept action; AI estimate vẫn hiển thị cạnh Your decision (FE-12) |

## Bổ sung CRUD quản lý — 2026-09-16 (hard delete, guard pm-only)

Toàn bộ destructive ops (PATCH/DELETE trong section này) chỉ role **pm** — operations gọi → 403. Hard delete = xoá cứng khỏi DB.

| Trạng thái | Method | Endpoint | Auth | Tác dụng | Trên FE | Vị trí trên FE |
|---|---|---|---|---|---|---|
| ✅ | PATCH | `/api/feedbacks/{feedback_id}` | pm | Sửa feedback: `feedback_text` (re-sanitize tại server + `embedding`/`embedding_model`/`embedding_dim` → NULL), `source`, `occurred_at`, `ai_analysis` partial merge (nhãn user = ground truth cho agent) | ✅ | `/vault` drawer D01 nút "Edit" → FeedbackEditDialog (text/source/occurred_at/severity/sentiment/topics) |
| ✅ | DELETE | `/api/feedbacks/{feedback_id}` | pm | Hard delete 1 feedback → 204; GET sau xoá → 404 | ✅ | `/vault` drawer D01 nút "Delete" → AlertDialog confirm |
| ✅ | POST | `/api/feedbacks/bulk-delete` | pm | Hard delete hàng loạt `{ids: UUID[]}` (≤500) → `{deleted: n}`; id lạ bỏ qua; 1 transaction | ✅ | `/vault` bulk bar "Delete selected" (khi có selection) |
| ✅ | DELETE | `/api/imports/{import_id}` | pm | Xoá cả lô: feedback (import_id) → insights tham chiếu runs → evidence → llm_call_logs → analysis_runs → import → 204; **409** khi status `mapping_generating`/`importing` | ✅ | `/vault` rail Files — nút trash hiện khi hover từng import → confirm đếm số row |
| ✅ | PATCH | `/api/insights/{insight_id}` | pm | Sửa title/finding trực tiếp → status `edited` + ghi 1 row `insight_reviews` (action=edit, reviewer từ token) | ✅ | `/reports` nút "Edit report" → ReportEditDialog |
| ✅ | DELETE | `/api/insights/{insight_id}` | pm | Hard delete insight → 204; `actions`, `insight_reviews`, `impact_checks` cascade DB (ondelete=CASCADE sẵn) | ✅ | `/reports` nút "Delete report" → AlertDialog confirm |
| ✅ | DELETE | `/api/products/{product_id}` | pm | Cascade toàn bộ dữ liệu product trong 1 transaction (feedback → evidence → llm_call_logs → insights → taxonomies → product_schemas → decision_logs → analysis_runs → imports → product) → `{product_id, deleted_counts}`; **409** khi còn import đang xử lý | ✅ | Breadcrumb product dropdown → "Delete product…" (bắt buộc gõ đúng tên product) |

**Đã drop (phase 21) — trở lại shape mới ở plans 22/25/26/27:** `/api/sources` (GET/POST/PATCH) · `/api/reviews/{id}` · `/api/corrections/{id}` · `/api/insights/run` · `/api/insights` · `/api/reports/kpis` · `/api/agent/runs` + status/decision.

## Quy ước chung

### Bổ sung terminal BE — 2026-09-07

| Trạng thái | Method | Endpoint | Auth | Tác dụng | Trên FE | Vị trí trên FE |
|---|---|---|---|---|---|---|
| ✅ | POST | `/api/impact-checks/run` | pm \| operations | `{product_id}` bắt buộc; 404 product không tồn tại; đo action accepted/edited đủ tuổi của đúng product; trả `{product_id, window_days, results:[{action_id, insight_id, before_count, after_count, delta_ratio}]}`. Mảng rỗng khi không có phép đo mới; idempotent; không gọi LLM. | ⬜ | Terminal `agent_terminal.py --flow` |

- `GET /api/feedbacks`, `GET /api/feedbacks/{id}` và `GET /api/analysis/runs/{id}/results`: `FeedbackOut` thêm `has_embedding: boolean`; không trả vector/raw content. FE hiện có có thể bỏ qua field mới.
- `POST /api/agent/runs`: sanitize câu hỏi trước graph/checkpoint, áp dụng cả CLI cũ.
- `POST /api/agent/runs/{id}/decision`: chỉ title/finding từ `edited_insight` vào graph; sanitize các text này và reason trước checkpoint/decision memory. Shape request giữ nguyên.
- `POST /api/insights/{id}/actions`, `PATCH /api/actions/{id}`: sanitize recommendation/rationale/override_reason trước persist; giữ điểm AI và công thức priority. Shape request giữ nguyên.
- Terminal mới gọi API cho mọi gate; reviewer lấy từ token, không tự chọn user trong database.
- `GET /api/imports/{id}`: lỗi ngày trong `report.errors` chỉ nêu số dòng và định dạng ISO 8601, không echo giá trị CSV chưa sanitize; lỗi import fatal chỉ chứa loại lỗi, không chứa exception payload.

### Quy ước dùng chung

- **Roles:** chỉ `pm` và `operations`; register mở (role mặc định `operations` — P1.5).
- **Bộ lỗi chuẩn:** 401 sai/thiếu credentials · 403 sai role · 404 thiếu row · 409 trạng thái không hợp lệ · 422 body sai schema · 500 generic (không leak chi tiết).
- **PII boundary:** `raw_content` KHÔNG BAO GIỜ xuất hiện trong response nào; `feedback_text` (đã sanitize) là dữ liệu phân tích hợp lệ; log chỉ method + path.
- **Routing FE→BE:** mọi request `/api/*` từ browser được Next.js rewrite về FastAPI `http://127.0.0.1:8000/api/*` (same-origin giữ cookie httpOnly — `frontend/next.config.ts`). FE gọi qua helper `apiFetch` (`frontend/lib/api.ts`) + React Query hooks.
- **Swagger:** `http://localhost:8000/docs` khi chạy `uvicorn app.main:app`.
