# Handoff: Chặn vòng lặp plan→evaluate vô tận của UNDERSTAND agent
- Date: 2026-10-23
- From: zcode
- To: any
- Branch / worktree: codex/activity-center
- Milestone: delivery — agent module (plans 17–20 / pha P6), bugfix theo user report
- Status: done

## Done
- Root-cause report user "agent chatbot lặp step plan/evaluate vô tận, chả ra gì" (trang /data-graph, card Ask about this data):
  1. LangGraph default `recursion_limit=25` — graph `load_context + 3 node/vòng × MAX_ITERATIONS(=8) + synthesizer + persist` = 27 bước tệ nhất → `GraphRecursionError` CHẠM NGƯỠNG đúng ở planner vòng cuối, trước khi kịp force-synthesize → run failed, không insight.
  2. Stop conditions (iteration/budget) chỉ override SAU khi đã gọi LLM plan → lãng phí 1 call + 1 lượt chờ mỗi vòng.
  3. Evaluator xác nhận `sufficient_evidence=true` nhưng planner LLM vẫn được chọn tool mãi (chỉ mang tính gợi ý trong prompt).
  4. Planner chọn lại đúng tool+params bước vừa chạy → evidence lặp, không tiến triển.
- `backend/understand_agent/nodes.py`:
  - `planner` kiểm tra stop conditions TRƯỚC khi gọi LLM, thoả điều kiện nào → synthesize NGAY không tốn plan call: iteration >= `UNDERSTAND_MAX_ITERATIONS`; budget `llm_call_logs` dùng hết; `_consecutive_sufficient(evaluations) >= _SUFFICIENT_ROUNDS_TO_STOP` (=2).
  - Sau LLM call: planner chọn lại đúng tool+params bước vừa chạy (so `_action_sig` với `tool_history[-1].sig`) → override synthesize.
  - `dispatch` ghi `sig` (canonical tool+params) vào `tool_history`.
  - Bỏ field `force` chết trong payload; prompt thêm rule "KHÔNG chọn lại tool+params vừa chạy".
- `backend/understand_agent/runner.py`: `_thread_config` set `recursion_limit = max(3*MAX_ITERATIONS + 10, 25)` (áp cho cả start lẫn resume Gate #2); message run failed nêu rõ loại lỗi (FE hiển thị thẳng `run.error`).
- FE `frontend/app/(app)/data-graph/page.tsx`: dòng "Investigating" hiện counter bounded từ field `progress` có sẵn của `GET /api/agent/runs/{id}`: `step {iteration}/{max_iterations} · LLM {llm_calls_used}/{llm_budget}`.

## Evidence
- `uv run pytest tests/test_understand_planner_stops.py -q` → 8 passed (file mới: test_understand_planner_stops.py).
- `uv run pytest -q` (unit, integration deselected) → 145 passed.
- `npx tsc --noEmit` trong `frontend/` → sạch.

## Not done / gaps
- Không chạy suite `-m integration` (cần Supabase thật reachable) — test integration UNDERSTAND dùng fake planner (tool 1 vòng rồi synthesize) nên không chạm các nhánh force mới.
- Không đổi default `UNDERSTAND_MAX_ITERATIONS=8` / `UNDERSTAND_LLM_BUDGET_PER_RUN=18` — vẫn hợp lý sau khi stop điều kiện dừng sớm; nếu vẫn thấy chậm có thể hạ còn 5–6.

## Blocked / risks
- Không có blocker. Lưu ý: run "running" cũ (trước fix) kẹt vì GraphRecursionError đã được `mark_stale_running_failed` heal lúc boot; FE đang có nút "Retry with the same question" cho run failed.

## Next steps
1. Test tay trên /data-graph: hỏi 1 câu, xem trace dừng sớm khi evaluator đủ bằng chứng 2 lần liên tiếp; FE hiện "step x/8 · LLM n/18".
2. Nếu muốn dừng gắt hơn/buông lỏng hơn: chỉnh `_SUFFICIENT_ROUNDS_TO_STOP` (nodes.py) hoặc hạ `UNDERSTAND_MAX_ITERATIONS` trong settings.
3. Chạy `uv run pytest -m integration` khi Supabase active để xác nhận flow Gate #2 không regression.
