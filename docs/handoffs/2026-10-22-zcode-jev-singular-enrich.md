# Handoff: Enrich singular — JEV System One native, bỏ batch chat (runner v4)
- Date: 2026-10-22 23:xx local (session tối)
- From: zcode
- To: any
- Branch / worktree: codex/activity-center (KHÔNG commit — working tree dùng chung)
- Milestone: Delivery — LISTEN pipeline v4 (owner directive 2026-10-22)
- Status: done

## Done
- `backend/app/services/jev_client.py` (MỚI): System One native per-item — `POST {LLM_BASE_URL|JEV_API_BASE}/systemone`, model `JEV_MODEL` (jev-latest), questions map Noul/Choice/Score theo docs TypeSafe + phương pháp S7 (thêm `safety` noul + `ai_issue` choice so với bộ S7); retry 429/529 backoff; trace 2 lớp (Langfuse + `llm_call_logs`, `prompt_version=jev-v1`); `confidence` = min xác suất lựa chọn (KHÔNG gồm safety noul); KHÔNG silent-fallback về engine llm.
- `enricher.py`: dispatch theo `ENRICH_ENGINE` (`llm` chat | `jev` systemone); `active_prompt_version()`; XÓA `enrich_feedback_batch`.
- `analysis_runner.py`: v4 singular — xóa `_pick_chunk`/`_process_chunk`; `PIPELINE_VERSION="v4"`; mọi run chạy per-item (commit từng item, resume/idempotency giữ nguyên).
- `schemas/enrichment.py`: xóa `BatchEnrichmentItem/Out`, `strict_batch_enrichment_schema`; `llm_client._schema_for` bỏ nhánh batch.
- `routes/analysis.py`: run snapshot `llm_model=JEV_MODEL` + `prompt_version=active_prompt_version()` khi engine jev; `chunk_size=1`.
- `analysis_service.build_cost_receipt`: singular — 1 enrich + 1 embed call mỗi item.
- `main.py`: `/api/health` thêm `enrich_model_active` (jev → JEV_MODEL).
- FE `activity-sheet.tsx`: bỏ copy "Mode batch · chunk 10" → "Phân loại từng mục (JEV per-item)"; row run "toàn bộ import / feedback đã chọn".
- `.env` (chưa commit, dev): `ENRICH_ENGINE=jev`; `.env.example` cập nhật comment.
- Docs: decisions.md entry 2026-10-22 (supersede quyết định 2026-10-09 "không mở 34B" theo chỉ đạo owner); api-checklist rows analysis (preview/runs/cancel) đồng bộ.

## Evidence
- `uv run pytest -q` → **137 passed** (gồm 10 test mới `test_jev_client_unit.py` + dispatch/prompt-version tests).
- `uv run pytest -m integration` → **107 passed** (36 phút, real PG; gồm idempotency/phase28/terminal_flow đã viết lại singular).
- Smoke thật 4 call System One từ app path: `llm_call_logs` 4 row `enrich | jev-latest | latency 1301–1546ms | error=NULL`; wall-clock ~2.4–2.5s/call steady (cold-start call đầu ~12s — Langfuse + pooler). Chất lượng 3 câu VI teencode: topics/sentiment/severity/emotions hợp lý, confidence 0.37–0.85.
- Backend restarted (`ENRICH_ENGINE=jev`): `/api/health` ok, db ok.

## Not done / gaps
- **<1s/lệnh chưa đạt**: API ~1.3–1.5s + ~1s write trace (Langfuse/DB) → ~2.4s wall steady. Phần dưới 1s là latency provider — nếu owner cần nhanh hơn: cân nhắc worker song song nhẹ (asyncio/threads) cho per-item calls, hoặc hạ多久 trace sync. CHƯA làm (ngoài chỉ đạo).
- S7 quality FAIL (fixture mơ hồ) vẫn là bằng chứng đứng — chưa re-benchmark trên taxonomy thật; floor UNCATEGORIZED + HITL confidence là lớp chịu lỗi.
- `ANALYSIS_BATCH_SIZE` settings còn nhưng không còn consumer; cột `analysis_runs.chunk_size` luôn ghi 1 (không migrate).
- FE chưa đụng logic — chỉ copy. `docs/api-checklist.md` đã sync.

## Blocked / risks
- Không. Lưu ý: session zcode chiều/tối cùng ngày từng thấy 7 unit test đỏ do jev_client WIP — phần việc đó đã hoàn tất trong session này; unit + integration đều xanh.

## Next steps
1. Owner chạy 1 analysis run nhỏ trên UI (http://localhost:3000 → vault → Analyze) để cảm nhận tốc độ per-item thật.
2. Nếu cần <1s cảm nhận: mở follow-up parallelize per-item enrich (giữ commit per-item + idempotency).
3. Re-benchmark JEV trên taxonomy thật khi có budget credit (đóng câu chuyện S7 FAIL).
