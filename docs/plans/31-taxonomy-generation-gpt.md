# Plan 31 — Migration 0016 + GPT Taxonomy Generation (MVP 1)

> Nguồn: spec Listen 2026-10-07 §2 · Blocked by: 30 (cần `llm_model_for`).

## Mục tiêu

`sample feedback (đã sanitize) + context ──GPT──▶ proposal tree ──human apply──▶ Active Taxonomy v1`. Proposal STATELESS (không đụng DB tới khi apply).

## Tasks

- [x] Task 1 — Migration `0016_listen_taxonomy_enrich`: `ALTER TYPE llm_call_type ADD VALUE 'enrich'/'taxonomy_generate'/'topic_recommend'`; `products.taxonomy_version INT NOT NULL DEFAULT 1`; `taxonomies.slug VARCHAR(200) NULL` + `UNIQUE(product_id, slug)`.
- [x] Task 2 — Models: `Product.taxonomy_version`, `Taxonomy.slug`; `models/enums.py` thêm `Emotion` (frustration, anger, disappointment, confusion, anxiety, satisfaction, delight, neutral) + `Intent` (bug_report, feature_request, question, complaint, praise, other) — validation-only như Sentiment.
- [x] Task 3 — `taxonomy_service.ensure_slugs()` idempotent (root = `slugify(name)`, con = `cha.ten`; slug BẤT BIẾN khi rename) + gọi tại generate/apply/enrich.
- [x] Task 4 — Schemas: `TaxonomyGenerateIn {product_id, sample_size=30, context{product_type?, use_case?, persona?}}`; `TaxonomyProposalOut` (tree 2–3 levels, strict schema, guard drift); `TaxonomyApplyIn {tree}`.
- [x] Task 5 — `taxonomy_service.generate_proposal()`: sample = `feedback_text` đã sanitize (mới nhất, cap sample_size); prompt v1; `chat_structured(..., model=llm_model_for("taxonomy_generate"), call_type=taxonomy_generate)`.
- [x] Task 6 — Routes `taxonomies.py`: `POST /api/taxonomies/generate` (pm-only) · `POST /api/taxonomies/apply` → tạo node canonical/active (skip slug trùng — idempotent), bump `taxonomy_version`, `log_decision`.
- [x] Task 7 — Tests RED (mock chat_structured): proposal shape, apply idempotent, version bump, role guard. api-checklist sync CÙNG commit.

## DoD

curl generate → apply → `GET /api/taxonomies` thấy tree + slug; `llm_call_logs` có `taxonomy_generate`; suite xanh.
