# Handoff: Listen AI re-spec — series 30–34 (taxonomy GPT + enricher v3 + model routing)
- Date: 2026-10-07 ~20:00 local
- From: claude-code
- To: any
- Branch / worktree: codex/activity-center (main working tree)
- Milestone: docs/plans/30–34 (series "Listen AI re-spec", 00-index §7)
- Status: done (S7 run + 34B jev_client CHỜ owner: JEV_API_KEY / verdict)

## Done
- **Preservation checkpoint `1b37a2a`:** toàn bộ work in-flight của các session trước được commit labeled trước khi đụng tới (trừ `.commandcode`, dev logs, `frontend/public/assets/@DO_NOT_TOUCH/`). **PII catch:** CSV khảo sát luận văn (`docs/thesis/*Form Responses*.csv` — 36 email thật + cột tên) BỊ STAGED lúc đầu → unstage + gitignore rule mới trong `.gitignore`.
- **Plan 30 `2c02847` — model routing .env:** 8 `MODEL_<USE_CASE>` (schema_map/enrich/taxonomy_generate/topic_recommend/cluster_name/insight/understand/act) → fallback `LLM_MODEL`, resolve TẬP TRUNG trong `chat_structured` qua `call_type` (caller không đổi); `ENRICH_ENGINE=llm|jev` + `JEV_*` + `ENRICH_TOPIC_CONFIDENCE_FLOOR=0.60`; `/api/health` expose `models` map + `enrich_engine`. Block mới đã append vào `.env.example` + `backend/.env` (giá trị rỗng — owner tự điền).
- **Plan 31 `736ac23` — migration 0016 + GPT taxonomy:** `taxonomies.slug` (unique per product, bất biến khi rename), `products.taxonomy_version`, 3 llm_call_type mới; `POST /api/taxonomies/generate` (pm-only, chỉ sample ĐÃ sanitize) + `POST /api/taxonomies/apply` (idempotent, bump version, decision log); enums `Emotion`/`Intent`.
- **Plan 32 `ea9b389` — enricher v3:** topics CHỈ từ Active Taxonomy slug + probability, dưới floor → UNCATEGORIZED giữ lại; emotions multi-label (rỗng → neutral); `ai_analysis` shape v3 (topics vẫn STRING nên analytics/clustering/FE không vỡ); BỎ classifier.py + auto-emerging per-record; `POST /api/analysis/re-enrich-uncategorized`. Fix 2 bug: runner `failed_count` bị `db.refresh` discard mỗi vòng lặp (commit bookkeeping ngay); proposal apply gán `parent_id` trước flush (id tường minh).
- **Plan 33 `168b3b4` — Spike S7 WRITTEN, chưa chạy:** vendor pinned firsthand (docs.typesafe.ai/api: `POST /v1/systemone`, noul/choice/score, backoff 429/529); `scripts/spikes/s7_jev_parity.py` per-topic Noul sweep {0.5,0.6,0.7} + fixture VI/EN 16 record ground-truth tay; không key → exit 2, KHÔNG tự bịa verdict.
- **Plan 34 `86d5e22` — recommend + re-enrich loop + e2e:** `POST /api/taxonomies/recommend` (pm-only, pool rỗng không tốn LLM) + `/recommend/apply` (tái dùng apply_proposal); `backend/scripts/e2e_listen_flow.py` (LLM THẬT, human-triggered, `--fresh`).

## Evidence
- `uv run pytest -m "not integration"` → **90 passed** (full unit, gồm 8 test routing mới + 9 enricher unit).
- Integration mới chạy xanh: test_taxonomy_generation (11), test_enricher_idempotency (2), test_topic_recommendation (5), test_phase28_integration, terminal_flow.
- `uv run alembic upgrade head` → `0016 (head)` trên Supabase dev.
- `GET /api/health` (sau restart, PID mới) → `status: ok`, `models` map đủ 8 use case, `enrich_engine: llm`.
- Fix luôn 1 test cũ failed TRƯỚC series (reports top-cATEGORIES: LIMIT 10 bị demo data dìm — monkeypatch limit trong test, intent aggregation giữ nguyên).

## Incident (disclose)
- Trong lúc rewrite `test_enricher_idempotency`, 1 lượt test đã gọi NHẦM LLM thật (path `mode="selected"` chưa mock) — toàn bộ request 404 `No endpoints found for stealth/space-bunny-alpha` (model chết), KHÔNG có generation thành công nào; đã mock đủ 2 đường và ghi lại đây.

## ⚠️ Blocking / risks
1. **`LLM_MODEL=stealth/space-bunny-alpha` ĐÃ CHẾT** (404 — xác nhận qua probe thật trong incident trên). Enrich/generate sẽ fail tới khi owner đổi model. Giờ đổi chỉ cần sửa `.env`: `LLM_MODEL=<model>` hoặc per use case `MODEL_ENRICH=...` → restart → xem `/api/health` `models`.
2. **S7 chưa chạy** (chờ `JEV_API_KEY`, env đã chờ sẵn). Sau khi có key: `uv run python ../scripts/spikes/s7_jev_parity.py` (từ `backend/`) → kết quả tự lưu `scripts/spikes/results/` → entry decisions. PASS mới làm 34B (`jev_client` + dispatch theo `ENRICH_ENGINE=jev`).
3. Chưa có UI taxonomy (owner đã chốt backend-first) — review qua API/curl; FE series riêng (khi làm NHỚ load FE skill).

## Next steps
1. Owner: sửa `LLM_MODEL`/`MODEL_*` trong `backend/.env` (model còn sống) → restart → `curl /api/health` kiểm tra `models`.
2. Owner: tạo key typesafe.ai → điền `JEV_API_KEY` → chạy S7 → tick plan 33 Task 4 + entry decisions.
3. Demo flow: `uv run python scripts/e2e_listen_flow.py --fresh` (từ backend/, LLM thật).
4. FE-14 series: màn Generate/Review taxonomy + uncategorized dashboard (load frontend-design skill trước).
5. Dọn `docs/.agent-server.log` tracked-deleted còn treo trong working tree (không thuộc series này).

## Where to check (cho owner)
- Health map: `curl http://127.0.0.1:8000/api/health` → nhìn `models`, `enrich_engine`.
- Trace per use case: `SELECT call_type, model, COUNT(*) FROM llm_call_logs GROUP BY 1,2 ORDER BY 2;`
- API thử tay: `POST /api/taxonomies/generate {"product_id": "...", "sample_size": 20}` → `POST /api/taxonomies/apply` → tạo analysis run như thường → `POST /api/taxonomies/recommend` → `/recommend/apply` → `POST /api/analysis/re-enrich-uncategorized`.
- Backend đang chạy nền (task `s0zreocv`, PID 30072) — stop bằng kill task khi xong.
