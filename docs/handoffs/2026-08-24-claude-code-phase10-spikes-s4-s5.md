# Handoff: Phase 10 done — spike S4 (HDBSCAN toy) PASS + S5 (LangGraph interrupt/resume) PASS
- Date: 2026-08-24 ~23:15 local
- From: claude-code (phiên thực thi phase 10)
- To: any
- Branch / worktree: main (repo root, per user's standing instruction — no worktree)
- Milestone: docs/plans/10-spikes-late-s4-s5.md
- Status: done

## Done
- `scripts/spikes/s4_hdbscan_toy.py`: 200 vector 1536-d (3 cụm seed=42 + 20 noise), HDBSCAN cosine sweep min_cluster_size {5,10,15}, đo thời gian, JSON evidence.
- `scripts/spikes/s5_langgraph_interrupt.py`: graph A→B(side effect INSERT `_spike_side_effects`)→C, `interrupt_before=["b"]`, AsyncPostgresSaver nối thẳng Supabase; 2 phase chạy bằng 2 TIẾN TRÌNH riêng (`--phase start` / `--phase resume`); resume PASS tự drop bảng toy.
- decisions.md: điền dòng S4/S5 bảng Spike outcomes (**6/6 dòng có kết quả**) + entry dated 3 quirks (scikit-learn ad-hoc 1.9.0; SelectorEventLoop cho psycopg async trên Windows; saver.conn = AsyncConnection đơn với dict_row).
- plans ticked: 10-spikes-late-s4-s5.md ✅ + 00-index row 10 + checklist.

## Evidence
- **S4 PASS**: cả 3 cấu hình tìm đúng 3 cụm; noise 7.5–8.5% (ground truth 10%); fit 0.018–0.108s/config; tổng **0.165s ≪ 5s**. sklearn 1.9.0 qua `uv run --with scikit-learn` (không pin production).
- **S5 PASS**: start dừng đúng TRƯỚC node b (`next=['b']`, side effect 0); process thoát hẳn; tiến trình MỚI resume `ainvoke(None)` → steps a,b,c đủ; side effect đúng **1 lần** (0→1, không nhân đôi). Resume ~9s (WAN).
- setup() tạo đúng 4 bảng checkpoint khớp `LANGGRAPH_CHECKPOINT_TABLES` trong env.py — report field `alembic_filter_matches_reality: true` ở CẢ 2 phase.
- Sau đo: information_schema trống bảng `_spike_*`/`checkpoint%` (cleanup verify tay bằng psycopg); alembic không bị ảnh hưởng (script chỉ tạo/drop ngoài metadata).
- JSON evidence lưu `scripts/spikes/results/` (gitignored): s4_hdbscan_toy_result.json, s5_langgraph_start_result.json, s5_langgraph_resume_result.json.

## Not done / gaps
- Không có production clustering/graph code lọt `backend/app/` — đúng scope spike-only (tiêu chí nghiệm thu #3).

## Blocked / risks
- ⚠️ Phiên song song đang làm Phase 05 DỞ trên cùng tree lúc tôi commit (untracked: `backend/app/schemas/feedback.py`, `services/ingest_service.py`, `scripts/import_csv.py`, `tests/fixtures/`, `tests/test_ingest.py`; modified `routes/feedback.py`). Commit của tôi CHỈ gồm 6 file docs + 2 spike scripts — không chạm vùng kia. Ai commit sau phải add tường minh theo path.
- S5 resume mất ~9s do mỗi checkpoint write đi WAN tới Supabase — phase HITL production cần tính đến latency này trong UX (progress feedback), không phải bug.

## Next steps
1. Phase 05 (ingestion) đang dở bởi phiên khác — đợi hoàn tất, đừng đụng file backend/tests + routes/feedback.
2. Phase 06 Presidio sau đó; phase 09 analysis runner là consumer chính của kết quả S4/S5 (clustering lib chốt lúc đó; HITL graph dùng AsyncPostgresSaver + SelectorEventLoop pattern đã ghi decisions).
3. Khi dựng graph production: nhớ `loop_factory=SelectorEventLoop` cho asyncio.run trên Windows + `saver.conn.cursor()` trả dict_row.
