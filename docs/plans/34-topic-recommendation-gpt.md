# Plan 34 — Topic Recommendation (MVP 3) + JEV wiring khi S7 PASS

> Nguồn: spec Listen 2026-10-07 §4 · Blocked by: 32 (34B: + 33 PASS).

## Mục tiêu

`uncategorized pool ──GPT (định kỳ)──▶ recommended topics ──human apply──▶ TAXONOMY v2 → re-enrich`. Human là người duy nhất mutate taxonomy.

## Tasks

- [x] Task 1 — `taxonomy_service.recommend_topics()`: pool = `uncategorized=true` HOẶC `topic_confidence < floor` (mới nhất, cap 100) → GPT (`model=llm_model_for("topic_recommend")`, `call_type=topic_recommend`) → proposals STATELESS `[{name, parent_slug?, evidence_count, examples ≤3 sanitized}]`.
- [x] Task 2 — Routes `taxonomies.py`: `POST /api/taxonomies/recommend` (pm-only) · `POST /api/taxonomies/recommend/apply` → tạo canonical/active + bump version + `log_decision` + trả count re-enrichable. api-checklist sync.
- [ ] Task 3 — **34B (chỉ nếu S7 PASS):** `services/jev_client.py` (httpx → `JEV_API_BASE` `/v1/systemone`, tracing `llm_call_logs`/Langfuse, model ghi `jev-...`); enricher dispatch theo `ENRICH_ENGINE`; lỗi Jev = item-level error (KHÔNG silent-fallback).
- [x] Task 4 — e2e: `backend/scripts/e2e_listen_flow.py` (idempotent, khuôn e2e_happytest): generate → apply → import → enrich → uncategorized → recommend → apply → re-enrich → dataset cuối khớp shape §7 spec.
- [ ] Task 5 — Docs sweep cuối: tick series 30–34 trong `00-index.md`, handoff cuối phiên kèm evidence + SQL check.

## DoD

Flow tròn qua script; `llm_call_logs` có đủ 3 call_type mới; handoff có "where to check" (UI route + SQL + Langfuse filter).
