# Plan 32 — Enrichment v3 (LLM backend) + UNCATEGORIZED

> Nguồn: spec Listen 2026-10-07 §3–§6 · Blocked by: 30, 31.

## Mục tiêu

`Feedback ──▶ ENRICH ENGINE ──▶ topics(closed-set) + sentiment + emotion + intent + severity ──▶ confidence check ──▶ OK | UNCATEGORIZED`. GPT KHÔNG nằm trong per-record runtime.

## Tasks

- [x] Task 1 — `schemas/enrichment.py` (mới): `EnrichmentOut` + strict JSON schema phẳng + drift guard (khuôn `Classification`): `topics[{id,probability}] ≤3`, `emotions[{label,probability}] ≤3`, `sentiment`, `intent`, `severity`, `safety_issue`, `ai_issue`, `confidence`, `rationale`.
- [x] Task 2 — `services/enricher.py` (mới, khuôn classifier): `enrich_feedback()` + `enrich_batch()`; prompt nhét taxonomy **slug list (chỉ active)**; `model=llm_model_for("enrich")`, `call_type=enrich`, `PROMPT_VERSION="v1"`. Post-process: max prob < `ENRICH_TOPIC_CONFIDENCE_FLOOR` hoặc rỗng → `uncategorized=true, topics=[]`; `emotions` rỗng → `["neutral"]`; snapshot `taxonomy_version`.
- [x] Task 3 — `analysis_runner.py`: `PIPELINE_VERSION="v3"`; `_enrichment_json` ghi shape v3 (topics = slug strings + `topic_scores/emotion_scores/topic_confidence/uncategorized`); **BỎ `accumulate_emerging`**.
- [x] Task 4 — Strip clean-rewrite: xoá `services/classifier.py`; rewrite `test_classifier_*` → `test_enricher_*` (threshold, uncategorized, batch coverage, idempotency).
- [x] Task 5 — Sweep consumers (topics vẫn string → không vỡ): `analytics/query_compiler.py`, `analytics/tools.py`, `services/clustering.py`, `taxonomy_service.merge_theme`, FE/vault PATCH — chỉ kiểm chứng.
- [x] Task 6 — `POST /api/analysis/re-enrich-uncategorized {product_id}` (routes/analysis.py): clear `ai_analysis` + `analysis_run_id` cho rows `uncategorized=true`, trả count; user bấm Run analysis như thường. api-checklist sync.

## DoD

pytest unit + integration (mock LLM) xanh; suite idempotency phiên bản enricher PASS; e2e happytest cũ không vỡ; dataset mới có đủ `emotions/intent/uncategorized/taxonomy_version`.
