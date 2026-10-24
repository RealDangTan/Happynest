# Handoff: Mở khóa flow end-to-end UNDERSTAND — Gate #2 hiển thị + investigation điều tra thật
- Date: 2026-10-23 (buổi chiều)
- From: zcode
- To: any
- Branch / worktree: codex/activity-center
- Milestone: delivery — agent module; kế tiếp handoff `2026-10-23-zcode-understand-loop-guard.md` (cùng ngày, sửa recursion/loop)
- Status: done

## Done
User report: "chưa từng có đoạn chat nào end to end thành công". DB thật cho thấy 3 lớp bug chồng nhau, đã sửa hết:

1. **Run kẹt `running` vĩnh viễn ở Gate #2 → chat không bao giờ hiện thẻ duyệt (BLOCKER chính).**
   Graph đậu interrupt chờ human nhưng không ai cập nhật AnalysisRun (apply_decision chỉ chạy SAU khi human quyết) → `GET /api/agent/runs/{id}` mãi trả `running` → chat-thread RunCard và ActivityTrace `/data-graph` kéo "Investigating…" vô tận; nhánh render thẻ duyệt (`pending`) không bao giờ đạt.
   Fix: route tính **status hiệu lực `pending_approval`** khi run DB `running` + interrupt payload tồn tại (không cần migration; FE đã sẵn sàng xử lý chuỗi này ở 3 chỗ: chat badge, data-graph, reports). `backend/app/api/routes/agent.py`.

2. **Planner synthesize ngay iteration 0 — không điều tra.** MODEL_UNDERSTAND=mistral-small-24b trả `synthesize` ngay cả khi evidence rỗng → insight "không điều tra". Fix ở `backend/understand_agent/nodes.py`: guard deterministic — chưa có evidence thì synthesize bị thay bằng opener tool (`aggregate_feedback` group_by=field đầu của schema; schema trống → `get_schema`); đồng thời đổi `MODEL_UNDERSTAND=` (rỗng → inherit `LLM_MODEL`=qwen3-30b-a3b) trong `backend/.env`.

3. **Synthesizer persist insight rác khi 0 evidence.** DB có insight title echo nguyên system prompt ("Tổng hợp evidence-grounded insight cho người quyết định") với confidence 1.0 — whitelist evidence rỗng vẫn được persist. Fix: whitelist rỗng + không còn evidence khả dụng → `_limited_insight` ("Không đủ bằng chứng…", conf 0.3); prompt synthesize cấm lặp instructions.

4. **BUG CRASH thật (phát hiện khi E2E với model mạnh): planner trả `action='tool'` nhưng tool=None → dispatch INSERT evidence `source_tool=NULL` vi phạm NOT NULL → graph crash.** Model trước đây không bao giờ chọn tool nên chưa nổ. Fix 2 tầng: planner tự phục hồi (tool không hợp lệ + chưa có evidence → opener; đã có evidence → synthesize), và `dispatch` dùng `safe_tool` (tool không hợp lệ → `tool_name or "unknown"`) nên evidence luôn ghi được, lỗi nằm trong observation cho planner vòng sau.

## Evidence
- `uv run pytest -q` → **153 passed** (16 test mới: planner stops 10, synthesizer guard 3, ...). 1 flake đã biết: `test_presidio_service` Stanza init OSError khi chạy full-suite — chạy riêng PASS, không liên quan.
- `uv run pytest tests/test_understand_agent.py -m integration` → 2 passed + 1 passed khi chạy riêng (batch error do flake stanza network; flow Gate #2 approve OK).
- **E2E THẬT** (script gọi `runner.submit_or_start` trên product `1a81ac14…`, 32 feedback demo, model qwen3-30b): ~3s → evidence=1 (opener aggregate chạy), interrupt Gate #2 đậu, insight title là phát hiện cụ thể conf=0.6, KHÔNG còn echo prompt.

## Not done / gaps
- 2 insight rác thời mistral (`9488aa88`, `d102ab09`, status=pending) còn nằm trong Reports của owner — nên reject/delete tay, không xóa hộ.
- 1 run crash giữa chừng khi debug (`1aa60094…`) sẽ được `mark_stale_running_failed` heal lúc boot sau 30 phút.
- `MODEL_ACT` vẫn mistral-small — chưa kiểm lại chất lượng ACT trên model đó.
- FE chưa có nút duyệt ngay trong chat (hiện draft + "Review in Reports" → duyệt ở `/reports?run=`) — chấp nhận được cho thesis.

## Blocked / risks
- **Server đang chạy phải RESTART** để nhận `.env` (MODEL_UNDERSTAND) — `uvicorn --reload` chỉ reload code, không reload .env.

## Next steps
1. Restart uvicorn → test 1 câu hỏi trong chat: trace chạy tool → card chuyển "needs review" với draft → Review in Reports → approve → completed.
2. Nếu muốn duyệt ngay trong chat: thêm G2 bar vào RunCard (dùng sẵn `useAgentDecision`).
3. Chạy `uv run pytest -m integration` đầy đủ khi mạng ổn định (stanza update-check gây flake: cân nhắc `download_method=DownloadMethod.REUSE_RESOURCES`).
