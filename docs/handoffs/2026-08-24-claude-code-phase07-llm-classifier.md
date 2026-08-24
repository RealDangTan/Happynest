# Handoff: Phase 07 done — LLM client fallback chain + classifier v1 + tracing 2 lớp
- Date: 2026-08-24 ~22:30 local
- From: claude-code (phiên thực thi phase 07)
- To: any
- Branch / worktree: main (repo root, per user's standing instruction — no worktree)
- Milestone: docs/plans/07-llm-client-classifier.md
- Status: done

## Done
- `app/services/llm_client.py`: `chat_structured(system, user, schema)` — chuỗi fallback khóa đúng plan §3.3: Mode A `json_schema` strict → Mode B prompt-JSON + strip fence + Pydantic validate → retry ĐÚNG 1 lần kèm text lỗi → `LLMStructureError`. Sau MỖI attempt (kể cả lỗi): đo latency, lấy usage, ghi llm_call_logs + Langfuse; module state `_structured_output_mode` cho health. Assert/docstring hợp đồng PII: chỉ nhận text đã sanitize.
- `app/schemas/taxonomy.py`: Classification (7 field, có safety_issue) re-export enum từ models/enums.py (nguồn duy nhất); `strict_classification_schema()` phẳng kiểu S2 (không $ref) + guard import-time chống drift schema↔model.
- `app/services/classifier.py`: PROMPT_VERSION="v1", system prompt VI rubric severity 4 mức; `classify_feedback(sanitized_text, few_shot=None)`; `compute_requires_human_review` đủ 5 nhánh (critical / safety / pii / conf<0.60 / high+critical với conf<0.75).
- `app/services/tracing.py`: MỞ RỘNG scaffold của phiên phase 08 giữ nguyên contract writer (`write_llm_call_log` không commit trong hàm, trả row); thêm Langfuse v3 singleton lazy + `trace_llm_call` (never raise) + kill-switch `LANGFUSE_TRACING_ENABLED=false`/thiếu key = no-op + `flush()` neo lifespan shutdown.
- Migration 0004 + model Feedback: cột `safety_issue BOOLEAN default false` (lệch §6 có chủ đích) — decisions.md entry riêng.
- `/api/health` mở rộng: db (SELECT 1), structured_output_mode, llm_model, embedding_model.
- Tests `tests/test_classifier_unit.py`: 15 case mock hoàn toàn (fallback chain từng nhánh, HITL 7 case, row sqlite in-memory, kill-switch). Autouse fixture chặn cả Langfuse thật lẫn SessionLocal thật.

## Evidence
- `uv run pytest tests/test_classifier_unit.py` = **15 passed**, chạy sau fix 0.12s.
- Smoke thật §5 (sau khi sửa `.env` thiếu `/v1`, xem risks): mode=json_schema, severity=high, ai_issue=inaccuracy, confidence=0.95, rationale tiếng Việt ✓ đúng kỳ vọng.
- Supabase `llm_call_logs`: row thành công (latency 7487ms, 381+122 tokens, error=NULL) + các row lỗi 404 trước-fix được ghi đủ metadata ✓.
- `/api/health` qua TestClient: `{"status":"ok","db":"ok","structured_output_mode":null,"llm_model":"gemini-3-flash","embedding_model":"text-embedding-3-small"}`.
- Sau pytest: count llm_call_logs KHÔNG đổi → fixture chống pollution hoạt động.

## Not done / gaps
- Inspect trace trên dashboard Langfuse EU là bước THỦ CÔNG của người dùng (agent không vào được dashboard). Traces đã đẩy async không warning ⇒ khả năng cao đã có; kiểm tra input có CHỈ sanitized text.
- Prompt v1 chưa đánh giá trên sample thật nhiều — kém thì ra v2 theo plan §6, đừng sửa v1.

## Blocked / risks
- ⚠️ `.env` (cả root lẫn backend/) bị revert về URL thiếu `/v1` + EMBEDDING_BASE_URL dạng full-endpoint — agent đã sửa lại cả 2 file theo tiền lệ S2 (decisions.md 2026-08-24). Nếu copy `.env` từ root lần nữa sẽ lặp lại 404. Nguồn đáng tin hiện là `backend/.env`.
- ⚠️ Test pollution đã xảy ra và được xử lý: một số unit test đầu tiên ghi rác vào `llm_call_logs` Supabase dev (SessionLocal mặc định). Đã xóa sạch theo chữ ký fake (latency=0 + usage 12/34 hoặc RuntimeError giả): 48→3 row, còn lại đúng bằng chứng thật. Fixture `no_real_db` ngăn tái diễn.
- File code phase 07 bị phiên auth sweep vào commit `0df1e4b` (feat(services)) trước khi kịp commit riêng — history không tách được sạch, đã ghi chú trong bảng index thay vì rewrite shared history.

## Next steps
1. Người dùng: mở Langfuse dashboard EU xác nhận trace generation `classify:Classification` xuất hiện + input chỉ sanitized.
2. Phase 05 (ingestion) giờ đã đủ blocker (03+04): routes feedback POST/CSV — nhớ wire router `feedback` (stub /similar đang chờ trong routes/feedback.py).
3. Phase 06 Presidio: đóng gói recognizer set S1 từ scripts/spikes (4 custom + builtin), neo analyzer singleton tại lifespan comment sẵn.
4. Khi classify hàng loạt (phase 09): tái dùng `session_factory` kwarg của chat_structured để batch ghi log gọn hơn.
