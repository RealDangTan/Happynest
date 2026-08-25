# DELIVERY PHASE — DESIGN SPEC (Frontend + Pipeline Completion)

> **Ngày:** 2026-08-25 · **Trạng thái:** đã duyệt qua brainstorming với owner cùng ngày (5 section, từng phần một) — chờ review file trước khi phân rã plan thực thi
> **Nguồn:** [AGENTS.md](../../AGENTS.md) §CURRENT PHASE (khai báo delivery 2026-08-25) · entry dated cùng ngày trong [`decisions.md`](../decisions.md) · API hiện hành: [`api-checklist.md`](../api-checklist.md)
> **Cách dùng file này:** nguồn sự thật kiến trúc cho toàn bộ plan series mới (`delivery-execute-plan.md`, `UF-*`, `FE-*`, `13–16`). Lệch spec khi thực thi → entry dated vào `decisions.md` TRƯỚC khi làm tiếp.

---

## 0. Phạm vi & ràng buộc

**In scope (khai báo 2026-08-25):**
- Frontend Next.js trong `frontend/` — shadcn/ui, preset `b4IdeDqtkJ`
- 4 nhóm route stub → production: clusters, insights, reviews+corrections (HITL), reports/summary
- Production LangGraph HITL graph + correction→few-shot loop (spike S5 làm nền khả thi)

**Out of scope v1 (khai báo rõ để chống scope creep):**
- MCP agent / expose hệ thống ra ngoài — chỉ *đảm bảo không chặn đường* (xem §6)
- Multi-tenant / SSO / mở rộng auth
- WebSocket/SSE realtime (polling đủ)
- CRUD cluster/insight; endpoint đổi `review_status` của insight (cột tồn tại, chưa có API)
- Docker mọi hình thức — cấm vĩnh viễn (không đổi)
- Monorepo/Turborepo — bỏ theo quyết định owner

**Ràng buộc cứng:** deadline ~2026-10-22 (~8 tuần từ 2026-08-25) · máy dev 8 GB RAM · tín dụng LLM thấp → thực thi inline, không subagent fan-out · Windows native, Supabase session pooler.

## 1. Quyết định owner đã chốt

| Vấn đề | Quyết định |
|---|---|
| Chiến lược phân đoạn | **Hướng A — contract-first, vertical slices P0→P5**, mỗi pha kết thúc bằng 1 demo point |
| Chạy song song | **2 Claude session cùng repo root + ranh giới file nghiêm ngặt** (bảng §2); không worktree |
| Lệnh init shadcn | Đơn giản hoá: bỏ `--monorepo --rtl`; giữ `--preset b4IdeDqtkJ --base radix --template next --pointer` |
| Deliverable workstream user-flow | UI flow spec series mới trong `docs/plans/UF-*`; `user-flows.md` giữ nguyên làm truth tầng API/pipeline |

## 2. Kiến trúc tổng quan

```text
Browser ──► Next.js App Router (frontend/, :3000)
              │   /api/* proxy bằng next.config.ts rewrites
              ▼
           FastAPI (backend/, :8000)  ← KHÔNG đổi auth/CORS; cookie httpOnly SameSite=Lax
              │                         vẫn same-origin nhờ proxy
              ▼
           Supabase PG (session pooler) — giữ nguyên; migration DUY NHẤT cả giai đoạn: feedbacks.cluster_id
```

- Data fetching: server components cho phần tĩnh; TanStack Query cho list/mutation/polling (`refetchInterval` cho tiến độ run).
- Filter/pagination = URL search params là nguồn sự thật.
- Auth FE: middleware đọc presence cookie → redirect `/login`; xác minh JWT vẫn hoàn toàn phía FastAPI.

### Ranh giới 2 session (chống ghi đè — memory dự án có tiền lệ va chạm)

| Vùng | Session UF (docs) | Session FE (build) |
|---|---|---|
| `docs/plans/UF-*` | ✅ viết/sửa | chỉ đọc |
| `docs/plans/FE-*`, `13–16-*` | chỉ đọc | ✅ viết/sửa |
| `frontend/` | 🚫 cấm | ✅ |
| `backend/` | 🚫 cấm | ✅ |
| `AGENTS.md` · `decisions.md` · `delivery-execute-plan.md` | chỉ append, re-read trước ghi | chỉ append, re-read trước ghi |

Quy tắc kèm theo: commit ngay sau mỗi bước; session UF luôn đi trước 1 pha (spec xong trước khi FE mount màn tương ứng).

### Cấu trúc file plan mới

```text
docs/plans/
├── delivery-design-spec.md     # ← file này
├── delivery-execute-plan.md    # roadmap ACTIVE MISSION: P0–P5, lãnh thổ, DoD từng pha
├── delivery-contracts.md       # P0 output: contract đóng băng (nội dung §3)
├── UF-00-index.md, UF-01…      # workstream user-flow (session UF sở hữu)
├── FE-00-index.md, FE-01…      # workstream frontend (session FE sở hữu)
└── 13…16-*.md                  # backend slices, tiếp nối đánh số cũ
```

`00-index.md` giữ nguyên làm hồ sơ Backend Foundation, thêm 1 dòng trỏ sang `delivery-execute-plan.md`.

## 3. API contract (đóng băng cuối P0)

Bám 100% cột/enums có sẵn (`clusters`, `insights`, `ReviewAction`, `LlmCallType.name_cluster|generate_insight`). Auth mọi endpoint mới = `pm|operations`; bộ lỗi chuẩn 401/403/404/409/422; không response nào chứa `raw_content` hay text PII (snippet chỉ từ `sanitized_content`).

### C1 · GET /api/clusters
```jsonc
// ?sort=growth_ratio|recent (tuỳ chọn, mặc định feedback_count desc)
{ "items": [ {
  "id": "uuid", "name": "…", "summary": "…",
  "feedback_count": 12, "first_seen": "ISO", "last_seen": "ISO",
  "current_count": 8, "previous_count": 4, "growth_ratio": 1.0,
  "is_emerging": false, "is_spike": true, "suggested_priority": 0.82,
  "sample_feedback_ids": ["uuid × ≤5"]
} ] }
```
Chưa từng chạy clustering → `items: []` (không lỗi).

### C2 · GET /api/insights
```jsonc
{ "items": [ {
  "id": "uuid", "cluster_id": "uuid|null",
  "title": "…", "summary": "…", "suggested_action": "…",
  "evidence": [ { "feedback_id": "uuid", "snippet": "từ sanitized_content",
                  "severity": "high", "created_at": "ISO" } ],   // ≤5/insight
  "review_status": "unreviewed"
} ] }
```

### C3 · HITL
Queue dùng lại endpoint đã ship: `GET /api/feedbacks?review_status=pending`.

**POST /api/reviews/{feedback_id}** — phê duyệt NỘI DUNG:
```jsonc
// Req: { "action": "approve"|"edit"|"reject", "edited_content": "…" }  // edit ⇒ bắt buộc nội dung, else 422
// Res 200: FeedbackOut sau cập nhật (review_status = approved|edited|rejected)
```
`edited_content` do người dùng gõ → backend chạy lại Presidio trước khi lưu thành `sanitized_content`. Side effect: edit/reject tự ghi `correction_examples`.

**POST /api/corrections/{feedback_id}** — sửa NHÃN:
```jsonc
// Req: ít nhất 1 trong { categories[], ai_issue, severity, sentiment } (+ note?) — rỗng ⇒ 422
// Res 200: FeedbackOut cập nhật nhãn + { "correction_recorded": true }
// Effect: ghi correction_examples (input đã-sanitize + output-sửa) — nền few-shot v2
```
Không phụ thuộc review_status (áp dụng cho feedback đã classify).

### C4 · GET /api/reports/summary
```jsonc
// ?days=7|30|90 (default 30) — thuần SQL aggregate, KHÔNG gọi LLM
{ "generated_at": "ISO", "window_days": 30,
  "totals": { "feedback_count": 22, "pending_review_count": 4, "pii_detected_count": 4 },
  "by_severity": { "low": 5, "medium": 9, "high": 6, "critical": 2 },
  "by_sentiment": { "positive": 8, "neutral": 10, "negative": 4 },
  "top_categories": [ { "category": "hallucination", "count": 7 } ],  // ≤10
  "emerging": [ /* cluster có is_emerging|is_spike=true, ≤5 */ ] }
```

### C5/C6 · Trigger đồng bộ (bổ sung được owner duyệt NGAY trong phiên thiết kế — tính trong bản freeze)
- **POST /api/clusters/run** → 200 `{clusters_upserted, assigned_count, unassigned_count, duration_ms}`. Đồng bộ (dataset ≤1500). Rerun idempotent: xoá insights cũ → clusters cũ → tạo mới trong 1 transaction.
- **POST /api/insights/run** → 200 `{insights_generated, duration_ms}`; **409 nếu chưa có cluster**. Cap số cụm mỗi lượt qua env (default 10) để kiềm chế chi phí LLM.

### Migration duy nhất cả giai đoạn
Thêm cột `feedbacks.cluster_id UUID FK→clusters.id NULLABLE + index` (bảng `clusters` không có chỗ lưu membership). Alembic revision thường — các bảng checkpoint LangGraph vẫn nằm ngoài filter như cũ.

## 4. Frontend design

### Init mechanics (plan FE-01)
```bash
# precondition owner: Node ≥20.18.1 (đang 20.18.0 — shadcn CLI yêu cầu cao hơn)
cd frontend   # dời README placeholder trước; CLI từ chối dir có file thì init tên tạm rồi move lên
pnpm dlx shadcn@latest init --preset b4IdeDqtkJ --base radix --template next --pointer
```
Kết quả: Next.js App Router + TS + Tailwind v4 + token vega/olive trong globals.css + lucide. Verify `pnpm dev` boot; commit ngay sau init.

### Cấu trúc app
```text
frontend/src/
├── app/
│   ├── login/page.tsx
│   ├── (app)/layout.tsx          # shell: Sidebar + user menu
│   │   ├── dashboard/            # P1 khung rỗng → P4 đầy đủ chart
│   │   ├── feedbacks/            # list (+filters URL params), [id] detail
│   │   ├── analysis/             # runs: trigger + progress + results
│   │   └── clusters/ insights/ reports/    # P3/P4 mount dần
├── lib/api.ts                    # fetch wrapper: credentials include; chuẩn hoá 401/403/409/422
├── components/ui/*               # shadcn — add ĐÚNG lúc cần, không add-all
└── next.config.ts                # rewrites /api/* → http://127.0.0.1:8000/api/*
```

### Ánh xạ màn hình ↔ shadcn components

| Màn | Components chính | Ghi chú |
|---|---|---|
| Login | Card · Field/Input · Button · Alert | lỗi 401 chung (chống dò email) |
| Shell | Sidebar · DropdownMenu · Separator | role hiển thị cạnh avatar; middleware guard |
| Feedback list | Table + Pagination · Select filter · Badge severity/sentiment · Skeleton · Empty | state trên URL params |
| Feedback detail | Card composition · Tabs · Badge `pii_detected` | raw content chỉ hiện qua toggle explicit |
| Import CSV | Dialog · Progress · Alert kết quả + bảng errors[] | đúng shape `{imported, failed, errors}` |
| Analysis runs | AlertDialog confirm · Progress · polling · Table results | disable trigger khi run running |
| HITL review | Dialog edit (Textarea) · AlertDialog reject · toast sonner | queue = filter pending |
| Clusters/Insights/Reports | Cards grid · Badge emerging/spike · Accordion · Chart + stat tiles | P3/P4 |

Quy ước code theo shadcn skill: `gap-*` không `space-y-*`; form dùng FieldGroup/Field; Empty/Skeleton/Badge thay markup tự chế; semantic colors; icon qua `data-icon`.

## 5. Backend slices

### P2 · HITL production (13-hitl-langgraph.md) — rủi ro nhất, xếp sớm
Batch runner giữ nguyên; runner đánh dấu row đủ điều kiện thành `review_status='pending'`. Graph HITL RIÊNG và NHỎ (mô hình spike S5):

```text
[ prepare_review ] ─► interrupt() ─► [ apply_action ] ─► [ record_correction? ] ─► END
    Postgres checkpoint (4 bảng checkpoint ngoài filter Alembic từ day one)
```
- `POST /api/reviews/{id}` = resume graph bằng `Command(resume={action,…})`.
- Bằng chứng luận văn: kill process giữa interrupt → restart → resume OK (checkpoint thật).
- Stretch (tuỳ chọn): wire few-shot tĩnh "N correction gần nhất" vào `classify_feedback`.

### P3 · Clustering (14-clusters-api.md)
Tái dùng HDBSCAN spike S4 → `services/clustering.py`. Input = embedding đã lưu; row chưa embed bị loại và báo count; noise `-1` không gán cụm. Đặt tên/mô tả cụm bằng LLM trên snippet sanitized đại diện → `llm_call_logs(type=name_cluster)`.

### P4 · Insights + Reports (15, 16)
Mỗi cụm ưu tiên cao → 1 call structured-output (cùng cơ chế Mode A/B classifier) sinh title/summary/suggested_action + evidence_ids là feedback id thật → `llm_call_logs(type=generate_insight)`. Reports/summary thuần SQL theo C4.

## 6. Scale-up seams (đảm bảo cho tương lai, KHÔNG làm trong v1)

| Scale-up sau này | Chạm vào đâu | Xâm lấn |
|---|---|---|
| Thêm màn/chức năng FE | route segment + components; tái theme qua CSS vars preset | Thấp |
| Thêm bước pipeline | service + job mới; PIPELINE_VERSION snapshot sẵn | Thấp |
| Agent MCP | MCP server wrap đúng endpoint FastAPI; contract = tool spec; PII boundary chặn phía server; llm_call_logs = audit | Thấp–TB |
| Consumer thứ 2 (mobile…) | cùng contract; Bearer path song song cookie sẵn sàng | Thấp |
| Dataset >1500 | bật ANN pgvector (decision ghi sẵn đường lùi); thêm pagination clusters/insights | Thấp |
| Runner nặng hơn | BackgroundTasks → worker riêng (arq/systemd, vẫn no-Docker) | TB |
| Realtime | polling → SSE, sửa trong 1 hook | Thấp |

Khai báo KHÔNG scale (chấp nhận có chủ đích): auth đơn giản + role enum cố định; không monorepo (tách `packages/ui` về sau vẫn khả thi, cơ học).

## 7. Testing & DoD

| Lớp | Công cụ | Mức |
|---|---|---|
| Backend mới (13–16) | pytest kế thừa conftest Phase 11 — unit mock LLM, `-m integration` chạm DB thật | đầy đủ |
| FE logic thuần | Vitest cho `lib/api.ts` | tối thiểu |
| FE màn hình | Không Playwright (máy 8GB) — checklist DoD thủ công từng màn + `pnpm build` xanh | thủ công, chụp evidence |

DoD từng pha: checkbox kiểu plan cũ; mỗi pha khép lại = 1 demo point + chụp screenshot/evidence cho chương kết quả luận văn.

## 8. Rủi ro & timeline

| Rủi ro | Mức | Đệm |
|---|---|---|
| Checkpoint LangGraph × Supabase pooler quirk | TB-T | S5 PASS cùng cấu hình; fallback review-không-graph + entry decisions.md, demo bằng S5 |
| Hết tín dụng LLM | TB | cap calls naming/insight, cache kết quả, reports thuần SQL |
| RAM 8GB chạy đồng thời nhiều dev server | TB | quy ước: lúc code chỉ 1 dev server; `pnpm build` định kỳ verify |
| Trễ dồn P5 | T | mục polish đánh dấu `[tuỳ chọn]` sẵn |

```text
T1      P0 freeze contract + roadmap           ┐ song song: UF specs đi trước
T1–2    P1 FE scaffold → feedback screens      ┘ từng pha một bước
T3–4    P2 HITL (BE+FE)
T5      P3 clusters
T6      P4 insights + reports
T7–8    P5 polish + data demo + viết báo cáo   ← đệm
```

Precondition owner (không khẩn cấp): nâng Node ≥20.18.1; ops note treo từ Phase 12 — rotate SECRET_KEY + reset password Supabase trước khi deploy prod.

## 9. Bước tiếp theo

1. Owner review spec này.
2. Gọi writing-plans → phân rã: `delivery-execute-plan.md`, `delivery-contracts.md`, series `UF-*`, `FE-*`, plans `13–16`.
3. Thực thi theo lãnh thổ §2; lệch → decisions.md.
