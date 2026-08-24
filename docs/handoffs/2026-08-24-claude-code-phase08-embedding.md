# Handoff: Phase 08 done — embedder + pgvector similarity endpoint, tests green
- Date: 2026-08-24 22:40 local
- From: claude-code
- To: any
- Branch / worktree: main (repo root, per user's standing instruction — no worktree)
- Milestone: docs/plans/08-embedder-pgvector-similarity.md
- Status: done

## Done
- `app/services/embedder.py`: `embed_texts` (batch ≤2048, sort-by-index giữ thứ tự, validate dim → `EmbeddingDimError`), `embed_one`, `store_embedding` (set đồng thời embedding+model+dim). Tenacity `wait_exponential(1,2,30)/stop_after_attempt(4)`, `reraise=True`. Mỗi attempt (kể cả lỗi) ghi 1 row `llm_call_logs` qua `tracing.write_llm_call_log` bằng session ngắn hạn riêng — log fail không giết flow.
- `app/api/routes/feedback.py`: `GET /api/feedbacks/{id}/similar?k=5` — exact scan cosine (`1 - (embedding <=> CAST(:vec AS vector))`), comment lý do không ANN (≤1500 rows), guard k∈[1..50] via Query, 404/409 rõ ràng, snippet sanitized ~200 ký tự. Mount vào main.py.
- Test infra lần đầu: marker `integration` đăng ký trong pyproject + `addopts = -m 'not integration'` (CLI `-m integration` ghi đè last-wins).
- Tests: unit 6 case (FakeOpenAI — split/order/dim/log/store_embedding/log-fail-resilient); integration 5 case trên Supabase thật (vector tay đơn vị, rank B>C>E>D đúng cosine 0.99/0/−0.707/−1, self-excluded, store_embedding assert 3 cột trên DB, 409/404/422).

## Evidence
- `uv run pytest` → **33 passed, 5 deselected** (unit; gồm cả suite phase 04/07 của phiên kia — verify incoming claims theo protocol).
- `uv run pytest -m integration` → **5 passed** (WAN ~30s).
- Smoke thật provider: `embed_texts(2 câu fake)` → dims=[1536,1536], cosine giữa 2 câu = 0.40 (sane); wall-clock 10.5s vs row log cuối 6159ms → **tenacity retry ăn 1 lần fail thật rồi thành công**. `SELECT llm_call_logs WHERE call_type='embed'` có row model=text-embedding-3-small prompt_tokens=23 (bằng chứng DoD mục 6 vĩnh viễn).
- DoD "không ANN index": `pg_indexes WHERE tablename='feedbacks'` → chỉ `pk_feedbacks`. Leftover test rows = 0 (cleanup fixture chạy sạch).

## Not done / gaps
- `/similar` CHƯA có guard role — deps auth đã sẵn sàng (phase 04); phase 05 wire auth cho cả router feedback khi mở rộng CRUD.
- Retry test không viết (timing flaky) — cấu hình nằm lộ trong embedder.py, đã chứng minh bằng smoke thật ở trên.

## Blocked / risks
- ⚠️ **Sự cố quy trình:** hai phiên claude-code chạy SONG SONG trong cùng working tree (phiên kia làm 04+07, tôi làm 08) — vi phạm handoff rule 4 (phải dùng worktree riêng). Owner xác nhận phiên kia dừng trước khi tôi tiếp tục. Hệ quả: commit `0df1e4b` của phiên kia sweep luôn file phase-08 đang dở của tôi (embedder/tracing scaffold/routes feedback pre-fix) kèm entry decisions.md của tôi; các fix tiếp theo (import `to_db`→serialize tay vì pgvector 0.5 không có `pgvector.utils`, mount main.py, markers pytest, tests) nằm ở commit `feat(embedding)` này — lịch sử tách hai lớp nhưng trung thực, message commit kia đã ghi chú rõ nguồn.
- SECRET_KEY trong .env chỉ 28 bytes (<32 khuyến nghị RFC 7518 cho HS256) — warning từ PyJWT trong lúc test auth. Nên regenerate 32+ bytes trước deploy.

## Next steps
1. Phase 05 (ingestion): mở rộng `routes/feedback.py` hiện có (đừng viết lại — đọc docstring scaffold đầu file), thêm CRUD + wire `require_role("pm","operations")`.
2. Phase 06 (Presidio): lifespan singleton tại main.py dòng neo sẵn.
3. Phase 09 sẽ gọi `store_embedding(session, feedback, vec)` sau classify — đừng gán cột embedding tay.
