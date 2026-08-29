# Handoff: Voc OS rewrite series 21–27 đóng trọn bộ BE
- Date: 2026-08-29 (thực thi 2026-08-28→29)
- From: claude-code
- To: any
- Branch / worktree: main
- Milestone: docs/plans/21-27-voc-os-index.md (series 21–27) — 7/7 phase ✅
- Status: done

## Done
- **Re-plan 2026-08-28** (decisions.md entry cùng ngày): kiến trúc VoC OS
  (LISTEN → UNDERSTAND → ACT) theo `docs/VoC Agent Operating System — Technical
  Implementation Plan.md`; series 17–20 SUPERSEDED; owner chốt: fresh reshape,
  products-only (không workspaces), strip & rewrite agent, backend first.
- Plan files 21–27 tạo + tick đầy đủ; 00-index §5 SUPERSEDED + §6 series mới.
- **P21 (fef11e4):** migration 0008 DESTRUCTIVE — drop feedbacks phẳng +
  human_reviews/correction_examples/action_drafts/impact_checks/sources/
  insights/insight_reviews; tạo products, imports, `feedback` JSONB zones
  (data/source_meta/ai_analysis, occurred_at, feedback_text). Strip
  happynest_agent/hitl_graph/review/sources/impact/insight cũ. Checkpointer
  plumbing tách sang `services/graph_runtime.py`.
- **P22 (eafb019):** migration 0009 product_schemas versioned + LLM mapper
  (call_type schema_map) + deterministic profiler + Gate #1
  (`POST /api/imports` → `GET mapping` → `POST mapping/decision`) + coverage
  endpoint. Raw CSV lưu DISK (IMPORT_STORAGE_DIR — decisions entry: chưa có
  Supabase Storage creds). Route cũ import-csv BỎ.
- **P23 (188ab30):** migration 0010 taxonomies (canonical/emerging) + classifier
  v2 taxonomy-aware (PROMPT_VERSION v2, pipeline analysis_version
  classifier-v2-taxonomy) + emerging-theme accumulate + governance endpoints
  (approve/merge/reject).
- **P24 (6318fdb):** `app/analytics/` query compiler + 8 tools (tool 9
  search_similar_cases dời P25 — cần bảng insights). Không HTTP surface.
- **P25 (b8227a1):** migration 0011 evidence + insights (finding vs hypothesis)
  + insight_reviews (enum insight_review_action) + llm_call_type
  plan/evaluate/synthesize. Package `understand_agent/`: graph §60
  (load_context → planner → dispatch → evidence → evaluator → synthesizer →
  interrupt Gate #2 → apply_decision; investigate_more loop về planner).
  Routes /api/agent/runs + status + decision + GET /api/insights.
- **P26 (a3716fe):** migration 0012 business_function + actions (human_*
  columns). ACT: 1 call LLM gộp routing+generate+estimate (lệch ghi trong plan
  26), priority 100% deterministic §49 (weights env), matrix §50, Gate #3
  override giữ agent value nguyên (§52).
- **P27 (3f40911):** migration 0013 decision_logs + impact_checks; hooks ở cả
  4 gate; impact_service đo trước/sau theo affected_context containment +
  CLI `scripts/run_impact_checks.py`; build_kpis 3-latency + evaluation 3 gate
  (agreement, matrix displacement, evidence grounding); E2E script
  `scripts/e2e_voc_flow.py` viết xong.

## Evidence
- `uv run pytest -m "not integration"` → **43 passed**
- `uv run pytest -m integration` → **72 passed**
- `uv run alembic upgrade head` → 0013 head, chain 0001–0013 sạch trên Supabase
- UNDERSTAND E2E với LLM mock chạy thật trên Supabase checkpointer:
  test_understand_agent.py 3/3 (interrupt → approve/edit/investigate_more/
  reject, edit re-sanitize PII, evidence whitelist thay id bịa)
- Commit chain: 95c59dd (preserve plan-20 KPI) → 9e61cff (docs) → fef11e4 →
  9097b39 → eafb019 → 188ab30 → 6318fdb → b8227a1 → a3716fe → 3f40911

## Not done / gaps
- E2E live-LLM (`scripts/e2e_voc_flow.py`) CHƯA CHẠY — tốn LLM thật
  (mapping + classify 650 row + synthesize); dành cho buổi demo (quy tắc
  tín dụng §1). Chạy: `uv run python scripts/e2e_voc_flow.py`.
- FE CHƯA NỐI surface mới: màn feedback/analysis/reports đọc shape cũ sẽ lỗi
  (🔶 trong api-checklist); review/corrections/sources/insights cũ đã biến mất
  khỏi BE. FE rewrite (IA §63 tài liệu nguồn) = series mới.
- README quickstart chưa cập nhật flow LISTEN→UNDERSTAND→ACT (việc nhỏ, kèm
  FE series).
- 108 row test rác từ phiên bản fixture cũ đã dọn tay (script scratchpad);
  các fixture hiện dùng dedicated product nên không lặp lại.

## Blocked / risks
- Supabase Storage chưa có credentials → raw import lưu disk local
  (IMPORT_STORAGE_DIR, decisions 2026-08-28); đổi storage sau cần di chuyển file.
- HDBSCAN trên data test tự-seed hoạt động; data demo cũ đã bị migration 0008
  wipe — demo CSV cần import lại qua LISTEN trước buổi demo.

## Next steps
1. Chạy `uv run python scripts/e2e_voc_flow.py` với demo_dataset.csv khi sẵn
   sàng tiêu LLM → chụp evidence cho luận văn.
2. Viết FE rewrite series (IA §63: Sources/Schema/Feedback/Understand/Act,
   product switcher ở profile) nối 32 endpoint trong api-checklist.
3. README quickstart + đề cương luận văn khớp kiến trúc mới (3 HITL gate).
4. Anti-pause Supabase weekly (≥1 query/tuần) như thường lệ.
