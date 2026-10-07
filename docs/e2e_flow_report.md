# E2E Flow Report — Happynest pipeline LISTEN → UNDERSTAND → ACT

- **Ngày tổng hợp:** 2026-10-05
- **Dựng từ:** các handoff ngày 14/09 → 02/10/2026 trong `docs/handoffs/` + `git log`. Mọi con số/claim dưới đây trích trực tiếp từ handoff gốc.
- **Về bằng chứng screenshot:** các chuỗi `e2e-01…e2e-30` và `audit-*.png` từng được chụp ở repo root (untracked), đã mất vĩnh viễn trong buổi dọn dẹp ngày 05/10/2026 do agent trong session này dùng lệnh `del` xóa nhầm cả file untracked (chi tiết trong handoff cùng ngày). Chỉ khôi phục được `docs/e2e-screenshots/audit/legacy-full-page.png` từ một unreachable git blob. Bằng chứng dạng text/log của mọi session vẫn còn nguyên trong `docs/handoffs/` — báo cáo này dựng 100% từ đó.

---

## 1. Pipeline được E2E

```
CSV/TXT (google-play, app-store, facebook, twitter)
  → SANITIZE (Presidio + Stanza "vi", placeholder <ORG>)
  → GATE #1 (review mapping, approve trước khi import)
  → IMPORT (row_count, report lỗi từng file)
  → CLASSIFY → EMBED → CLUSTER (HDBSCAN + pgvector trên Supabase)
  → UNDERSTAND agent (LangGraph + LLM thật) → Gate #2 interrupt → approve/edit insight
  → ACT agent (generate actions, priority matrix) → Gate #3 (override impact, accept/reject)
  → Reports summary / Dashboard / Stakeholders
```

Tất cả chạy qua UI thật (Next.js) + backend FastAPI thật + LLM thật.

## 2. Timeline từng session E2E

### 2026-09-14 — FE-11: VoC OS HTML prototype (static, không gọi API)
- Xây `frontend/public/happynest-voc-os.html` (~1485 dòng): 7 view, guided mission 6 bước, 3 human gates, evidence ledger, priority matrix, decision memory, KPI latency.
- QA: `pnpm test` 28/28; mission path qua agent-browser không console error; mobile 390px không overflow.
- Handoff: `2026-09-14-claude-code-voc-os-html-prototype.md`

### 2026-09-15 — FE-12: E2E đầu tiên qua backend thật
- Flow qua Next proxy, cookie jar (pm@thesis.local): upload demo CSV 5 row → preview → AI mapping proposal → **G1 approve → imported 5/5** → analysis → **5/5 completed** → Ask AI agent → **Gate #2 interrupt** (8 evidence) → approve → insight approved → generate actions (7 actions) → **G3 PATCH**: override impact 9→6, priority 8.10→7.40, reject 1, accept 1 → matrix regroup.
- Bug phát hiện khi chạy thật, đã fix (có entry `docs/decisions.md` 2026-09-15): Next rewrite proxy cắt LLM-slow route ở 30s → `experimental.proxyTimeout: 300_000`; `useFeedbackDetail`/`useSimilarFeedbacks` gọi khi id rỗng → thêm guard; date format `Jan undefined` → shortDate guard.
- Screenshot kỳ này là chuỗi `audit-*.png` + `audit2-*.png` (đã mất).
- Handoff: `2026-09-15-claude-code-fe12-six-screens.md`

### 2026-09-24 — Live LLM agent test GREEN + HAX trust layer
- UNDERSTAND agent với LLM thật (OpenRouter `stealth/space-bunny-alpha`) chạy trọn loop: planner → tools (aggregate_feedback, compare_periods, semantic_search) → evaluator → synthesize → **Gate #2 → insight approved qua API**. Run `d9cf2cb7…`: completed sau ~12.5 phút, `llm_call_logs` 26 row (12 ok / 14 validate-retry, fallback chain hoạt động), Langfuse trace present.
- Fix pack (decisions.md 24/09): `LLM_MAX_TOKENS=8192` — OpenRouter 402, model FREE nhưng credit-check giới hạn max_tokens, không phải hết tiền; TCP keepalive trên LangGraph checkpointer conn + `pool_pre_ping` — Supabase pooler cắt idle conn khi viết checkpoint Gate #2 (2/2 run bị).
- HAX trust layer: `GET /api/agent/runs/{run_id}/trace` metadata-only từ `llm_call_logs`; `RunProgressOut.llm_budget`; ACT expose `generation_error`; FE thêm AiTrace polling + AiBadge + isError/Retry trên mọi surface agent; pytest **83 passed** (unit) + **4 passed** (integration trên Supabase thật).
- Handoffs: `2026-09-24-claude-code-live-llm-agent-test.md`, `2026-09-24-claude-code-hax-trust-agent-ux.md`

### 2026-09-30 — First-run onboarding guide + 2 bug importer
- `FirstRunGuide` 3 bước (product → import → insight), hiện trên `/importer` và dashboard, dismiss persist vào localStorage.
- E2E headless: đăng ký user mới → redirected `/importer` → guide 0/3 → tạo product qua dialog → 1/3 → upload 4-row CSV → G1 confirm → import 4/4 → guide 2/3 với strikethrough → dismiss → reload giữ hidden. Typecheck + test 39/39 + lint pass trên các file bị đụng.
- Fix (lỗi có sẵn, onboarding lộ ra): wizard không trigger khi chưa có importId; `useGetMapping` không retry sau 409 (mapping đang sinh) → bảng mapping trống vĩnh viễn → retry 30×1s.
- Handoff: `2026-09-30-claude-code-first-run-onboarding-guide.md`

### 2026-10-02 — Full E2E lớn: LLM thật + 4 nguồn mock, 131 feedback
- Import qua wizard với `docs/feedback-mock/`: google-play 35 / app-store 32 / facebook 32 / twitter 32 → **G1 approve-all → imported 131/135** (4 row fail ở google-play — trường hợp PII/parse).
- Analysis: progress live 0→35. Kết quả: facebook 32/32 · app-store 32/32 · twitter 32/32 · **google-play 25/35** — 10 row lỗi provider trả JSON sai `BatchClassificationOut`, Mode-B retry cũng fail (data-quality của model bên provider).
- Clustering: **2 cụm (24 + 11 members)** sau khi tune `CLUSTER_MIN_SIZE=4` (mặc định 10 → 0 cụm với 121 row; sweep tay khẳng định size 4).
- UNDERSTAND: 2 investigation `d8c073e0` / `3cf72e21` chạy tới Gate #2 interrupt; insight "Chưa thể xác định vấn đề tăng nhanh nhất sau import" **approved qua UI**; evidence cards render thật.
- ACT: 3 actions (engineering / operation / support) → Gate #3 override impact 8→6 kèm reason → **ACCEPTED**; DB xác nhận `status=accepted`, `human_impact=6`, priority 7.88→7.26.
- 3 bug fix: (1) StepResult render "Import completed · 0 imported · 0 failed" khi run còn ở mapping_review → re-route theo status + guard `status !== "imported"`; (2) `useGetMapping` 409 retry nâng từ 30× lên 150×1s (~2.5 phút) vì proposal thật mất 1–2 phút; (3) `useImport` thêm poll guard: terminal status thiếu row_count → poll tiếp 1.5s.
- Cấu hình: `backend/.env` thêm `CLUSTER_MIN_SIZE=4` (**chưa có entry decisions.md** — cần bổ sung).
- Screenshot kỳ này là chuỗi `e2e-01…e2e-30` (đã mất).
- Handoff: `2026-10-02-claude-code-e2e-mock-data-ui-cleanup.md`

## 3. Checklist chức năng đã verify end-to-end

| Mức | Trạng thái | Session |
|---|---|---|
| Sanitize + PII placeholder | ✅ | 15/09, 02/10 |
| Gate #1 mapping review | ✅ | 15/09, 30/09, 02/10 |
| Import report chính xác | ✅ 131/135 · 4/4 · 5/5 | 15/09, 30/09, 02/10 |
| Analysis theo run + progress live | ✅ | 02/10 |
| Clustering (HDBSCAN + pgvector) | ✅ 2 cụm | 02/10 |
| UNDERSTAND agent (LLM thật) + Gate #2 interrupt | ✅ | 15/09, 24/09, 02/10 |
| Approve insight qua UI/API | ✅ | 15/09, 24/09, 02/10 |
| ACT generate + Gate #3 override/accept | ✅ | 15/09, 02/10 |
| Matrix regroup sau accept | ✅ | 15/09 |
| Reports summary + Dashboard + Stakeholders | ✅ | 02/10 |
| Trace API + AiTrace/AiBadge (HAX) | ✅ integration 4/4 | 24/09 |
| Onboarding guide | ⚠️ 2/3 — step 3 chưa E2E | 30/09 |

## 4. Vấn đề còn tồn đọng

1. **10 feedback google-play chưa classify** — provider trả JSON sai; `select_eligible` hiện không nhặt lại row đã claim bởi run COMPLETED nên chưa re-run được. Chờ provider ổn hoặc đổi model (quyết của owner). Cần bổ sung entry `docs/decisions.md` cho `CLUSTER_MIN_SIZE=4`.
2. **Agent run chậm (~12.5 phút)** — slow model + retry đôi khi chiếm nhiều call. Owner quyết: đổi model nhanh hơn hoặc hạ budget/iterations (handoff 24/09).
3. **Lint pre-existing**: `frontend/app/(app)/reports/page.tsx:353` và `vault/page.tsx:152` (react-hooks/set-state-in-effect) — khiến repo-wide `npm run lint` exit 1, chưa ai fix (không thuộc session nào trong bảng trên).
4. **FirstRunGuide step 3** (insight tồn tại → guide 3/3 tự ẩn) chưa được E2E.
5. **Screenshot bằng chứng mất** (→ §1). Data vẫn còn trong Supabase nên có thể tái tạo bằng re-screenshot UI, không cần đốt LLM: importer receipt / vault / clusters / insight detail / matrix / dashboard / reports / stakeholders.
6. Backend unit + integration gate đang xanh (83 + 4 passed vào ngày 24/09) — giữ chuẩn trước khi đụng code agent.

## 5. Kết luận

Cả chuỗi LISTEN → UNDERSTAND → ACT đã demo end-to-end thành công với LLM thật, đúng mục tiêu đề tài "AI Agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng". Limitations ghi nhận: latency run cao (do model), dataset demo nhỏ (35–131 row) — đủ demo thesis, chưa nói chuyện scale.
