# Handoff: HAX trust layer — trace API + silent-error sweep toàn app
- Date: 2026-09-24 11:15 local
- From: claude-code
- To: any
- Branch / worktree: codex/activity-center (shared checkout)
- Milestone: HAX Toolkit trust plan (owner-approved; plan file
  `~/.commandcode/plans/hax-trust-agent-ux.md`)
- Status: done

## Done
Áp Microsoft HAX Toolkit cho mọi surface agent/LLM (user yêu cầu: hiện tại
agent chạy không có feedback nào, kể cả lỗi):

- **Backend (3 thay đổi):**
  - `GET /api/agent/runs/{run_id}/trace` — metadata-only trace từ `llm_call_logs`
    (call_type, ok/error, latency, tokens, model, error[:200]; KHÔNG prompt/response —
    đúng PII boundary plan 29), 404.
  - `RunProgressOut` thêm `llm_budget` (từ `UNDERSTAND_LLM_BUDGET_PER_RUN`).
  - ACT generate KHÔNG nuốt lỗi nữa: `act_agent.generate_actions` trả
    `(created, skipped, generation_error)`; response thêm `generation_error`.
    Đã cập nhật 3 call site (routes/actions.py, agent_terminal.py, 2 e2e scripts).
- **FE shared:** `lib/types.ts` (AgentTraceRow/AgentTraceResponse, llm_budget,
  generation_error), `hooks/use-agent.ts` → `useAgentTrace` (poll 2s),
  components mới `components/ai/ai-trace.tsx` + `components/ai/ai-badge.tsx`.
- **Agent surfaces:** chat-thread RunCard (isError alert + Check again, failed →
  Retry cùng question, live AiTrace, calls used/budget, capability note G1);
  start-fail giờ giữ `ApiError.message` thật + Retry (trước đây discard); data-graph
  ActivityTrace (isError + Retry + AiTrace); reports (sửa bug Reject không mở dialog
  reason — G10; isError branch cho runQuery; generation_error Alert; AiBadge trên
  report header).
- **Sweep toàn trang:** matrix + stakeholders (isError branch thay empty-state lừa,
  Retry, AiBadge), dashboard (`summary.isError ? null` → Alert + Retry),
  importer StepPreview (`preview.isError` → Alert), importer StepResult +
  activity-sheet ImportDetail: bỏ fake `Progress 70%/35%` → spinner + status text,
  insights page (AiBadge). Grep `Progress value={35|70}` = 0 kết quả.

## Evidence
- `uv run pytest -m "not integration"`: **83 passed** (2 test unit mới: ACT
  generation_error, llm_budget schema).
- `uv run pytest tests/test_agent_trace_api.py -m integration`: **4 passed**
  (metadata-only shape + truncate 200, 404, 401, llm_budget) trên Supabase thật.
- `npx tsc --noEmit` + `npm run build`: pass (25 routes).
- `npm run lint`: 2 errors + warnings ĐỀU pre-existing (reports:352, vault:154
  set-state-in-effect; import thừa cũ) — không do thay đổi này.
- E2E thật trên temp server :8001 (đã tắt): login pm test → GET trace của run
  `d9cf2cb7-0d72-436c-ad1f-c601fecca741` (handoff 2026-09-24) → **26 items
  (12 ok / 14 error)** khớp đúng số llm_call_logs trong handoff; keys metadata-only;
  error bị truncate 200 ký tự. Lưu ý shell Windows không expand `$(cat)`.

## Not done / gaps
- Copy HAX states mới bằng tiếng Anh (owner chốt) nhưng vài trang thuần VN
  (dashboard Alert, activity-sheet spinner text) giữ tiếng Việt để khớp trang —
  owner có thể muốn chuẩn hóa sau.
- AiTrace poll 2s (không SSE) — chấp nhận theo kiến trúc hiện tại (no streaming
  anywhere backend). Nếu sau này thêm SSE, dùng lại shape AgentTraceRow.
- Trace endpoint chưa có index riêng trên `llm_call_logs.analysis_run_id` — query
  test trả <1s với data hiện tại; xem lại nếu bảng phình to.
- Lint pre-existing (reports/vault set-state-in-effect, import thừa) chưa fix —
  ngoài scope.

## Blocked / risks
- None. Backend server cũ trên :8000 chưa restart — cần restart để expose
  endpoint trace (owner chạy `uvicorn` riêng theo Hard Rule 6).

## Next steps
1. Restart backend dev server (:8000) để FE dev thấy trace endpoint.
2. Chạy 1 agent run thật trên FE: xem AiTrace trong chat + data-graph, Retry ở
   failed run, Reject-with-reason ở /reports.
3. Nếu muốn: thêm duration hint trung bình theo lịch sử run (HAX G3 sâu hơn).
