# Handoff: Vault không chạy lại được sau taxonomy update (JSONB null bug) + vault perf
- Date: 2026-10-23 19:05 local
- From: zcode
- To: any
- Branch / worktree: codex/activity-center (working tree, CHƯA commit)
- Milestone: delivery — vault/analysis loop (plan 32 taxonomy evolution) + FE-12 vault
- Status: done

## Done
- Root cause "0 pending in this scope / không chạy lại được": `reset_uncategorized` ghi `ai_analysis=None` qua `update().values()` → psycopg3+JSONB serialize thành JSON `'null'`, KHÔNG phải SQL NULL → mọi filter `ai_analysis IS NULL` (pending count, `select_eligible_feedback`, runner `_pick_next`) không khớp. FE hiển thị Pending (null falsy) trong khi backend thấy NOT NULL — 30/32 row product TEST2 dính.
- Fix write-path: `analysis_service.reset_uncategorized` dùng `sqlalchemy.null()`. Data repair 1 lần trên DB dev: 30 row JSON-null → SQL NULL (verify pending 0→30, preview eligible=30).
- Perf vault (đo trước/sau): defer cột `embedding` ở list endpoints; gộp count+page bằng `count() OVER()`; `select_eligible_feedback` lean (id, feedback_text) + create claim bằng bulk UPDATE; pool 2+2→5+5 + recycle 1800; FE poll runs 6s→30s. GET /api/feedbacks ~2.8s→~1.6s; 8 request song song 6.0s→3.3s.
- UX vòng lặp: `GET /api/feedbacks` thêm `analysis_state=uncategorized`; vault có banner "Mở khoá để phân tích lại" (gọi re-enrich tại vault) khi 0 pending + còn UNCATEGORIZED; nút "Analyze pending items" bật được ở All imports khi có pending.
- Backend đang chạy nền (task zcode, KHÔNG --reload) trên 127.0.0.1:8000 với code mới — tiến trình cũ của owner (PID 11220, không --reload nên không tự nạp code) đã bị stop để thay. Owner có thể stop task này và chạy lại `uv run uvicorn app.main:app --reload` trong terminal riêng như thói quen.

## Evidence
- `uv run pytest -q` → 145 passed (full unit, sau mọi thay đổi).
- `uv run pytest -m integration tests/test_ingest.py tests/test_crud_management.py tests/test_topic_recommendation.py tests/test_feedback_list_filters.py` → 25+2 passed (topic-recommend re-run sau fix: 6 passed).
- Test mới `tests/test_feedback_list_filters.py`: partition filter + regression reset ghi SQL NULL.
- API thật (token owner TEST2): pending count 30, uncategorized 2, preview `eligible_count=30`.
- FE: `npx tsc --noEmit` sạch, `npx eslint app/(app)/vault/page.tsx` sạch.
- Entry chi tiết: docs/decisions.md 2026-10-23 (JSONB null + perf); checklist đã sync.

## Not done / gaps
- Không commit (theo thói quen owner tự commit); các file đổi: backend (analysis_service, analysis.py, feedback.py, models/feedback.py, db/session.py, tests mới), frontend vault page, docs (api-checklist, decisions, handoff này).
- Chưa verify thị giác trên browser thật (user đang login TEST2 sẽ thấy ngay: 30 pending, nút Analyze bật).
- Latency floor còn ~1.5s/request do RTT ~280ms/query tới Supabase ap-southeast-2 — muốn hạ tiếp phải gộp query auth (get_current_user + owned_product_ids) hoặc đổi region (locked stack).

## Blocked / risks
- Quirk ghi lại trong decisions.md: trên stack này, gán tường minh `None` cho cột JSONB (ORM insert hoặc update().values()) → JSON `'null'`; muốn SQL NULL phải omitted-key hoặc `null()`. Test seed mới đã neo.
- `has_embedding` giờ đọc `__dict__` — list endpoint trả False cho mọi row (defer); detail vẫn đúng. FE không dùng flag này ở list.

## Next steps
1. Reload `/vault` (backend đã chạy code mới): TEST2 → "30 pending in this scope", bấm Analyze → receipt 30 items → Start.
2. Sau run: nếu còn UNCATEGORIZED và muốn re-label theo taxonomy mới → banner "Mở khoá để phân tích lại" ngay trên vault.
3. (Follow-up nhỏ) gộp query auth 1 RTT/request nếu vẫn thấy chậm; xem xét pool_size khi nhiều user thật.

## Addendum (cùng ngày, sau entry trên) — UX pass trên vault
- Owner yêu cầu "update đi cho ux tốt hơn". Đã làm (chỉ FE, không đổi API):
  - Filter Topic của vault bỏ 4 giá trị hardcode tiếng Anh ("Performance/Accuracy/...") — giờ load từ `/api/taxonomies?product_id=` (slug làm value, name làm label).
  - Cột Topic + drawer hiển thị name tiếng Việt qua `topicLabeler` (slug giữ trong `title` để truy evidence — cùng pattern `/data-graph`).
  - Filter "Analysis state" thêm giá trị UNCATEGORIZED (khớp `analysis_state=uncategorized` backend đã thêm ở entry trên).
  - Run xong tự invalidate `["feedbacks"]` + toast — bỏ bước bấm "Refresh results" thủ công; nút thay bằng "Đóng thẻ tiến trình".
  - Toast ở `/taxonomy` sau khi mở khoá đã trỏ đúng tên nút "Analyze pending items" (trước nói "Run analysis" — không tồn tại).
- Evidence: `npx tsc --noEmit` sạch, eslint 3 file sạch. api-checklist đã sync dòng `/api/taxonomies`.

