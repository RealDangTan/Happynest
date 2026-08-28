# Plan 21 — Voc Core Reshape: products, imports, feedback JSONB

> Nguồn thiết kế: VoC OS plan §1, §9, §15–18, §54–55 · Migration **0008 DESTRUCTIVE** · Blocked by: head 0007.

## Mục tiêu

Đổi nền dữ liệu từ bảng `feedbacks` phẳng sang mô hình product-scoped với JSONB zones, đồng thời strip toàn bộ code thuộc thiết kế cũ (feedback-level HITL, agent graph 17–19, sources registry, insights cũ).

## Tasks

### Task 1 — Migration 0008 (destructive)
- [ ] `products` (id, name unique, description, created_at) + seed 1 product mặc định (data migration).
- [ ] `imports` (id, product_id FK, source_type, storage_path, mapping_version, schema_version, status, row_count, error, created_at).
- [ ] DROP `feedbacks` CASCADE; recreate `feedback`: `id, product_id FK, import_id FK nullable, source TEXT, source_record_id TEXT, occurred_at timestamptz NOT NULL, imported_at, raw_content TEXT NOT NULL (PII boundary), feedback_text TEXT (sanitized), data JSONB, source_meta JSONB, ai_analysis JSONB, embedding Vector(1536) + embedding_model/dim, cluster_id FK nullable, created_at`. Index: product_id, cluster_id, embedding kNN scan giữ nguyên pattern (no ANN).
- [ ] DROP: `human_reviews`, `correction_examples`, `action_drafts`, `impact_checks`, `sources`, `insights`, `insight_reviews`. `llm_call_logs` bỏ FK feedback_id (drop constraint, giữ cột nullable) — log lịch sử sống sót.
- [ ] Review CASCADE trước khi chạy trên Supabase; checkpoint tables vẫn excluded `env.py`.

### Task 2 — Models + schemas
- [ ] `app/models/product.py`, `app/models/import_.py` (Import), rewrite `feedback.py`; xoá models chết; `enums.py`: bỏ enum không còn dùng, thêm `import_status` (pending/mapping_review/imported/failed) — giữ review_status nếu clusters/reports còn cần? → ĐÃ QUYẾT: bỏ review-level HITL nên không cần review_status trên feedback.
- [ ] `app/schemas/product.py`, `import_.py`, rewrite `feedback.py` (FeedbackOut: product_id, import_id, source, source_record_id, occurred_at, feedback_text, data, source_meta, ai_analysis).

### Task 3 — Strip code chết
- [ ] Xoá: `backend/happynest_agent/`, `services/hitl_graph.py`, `services/impact.py`, `services/insight.py`, `routes/review.py`, `routes/sources.py`, `routes/agent.py`, models/schemas tương ứng; main.py bỏ router tương ứng; test chết xoá.
- [ ] `analysis_runner.py`: chỉ classify→embed theo shape mới (ai_analysis JSONB tạm ghi flat keys: sentiment/severity/… — reshape cuối ở phase 23); bỏ `compute_requires_human_review`, review_status logic.
- [ ] `services/reports.py`: build_summary viết lại SQL theo cột mới (ai_analysis JSONB — pattern CASE-guard decisions 2026-08-26); build_kpis TẠM disable (404 stub) — dựng lại phase 27.
- [ ] Routes feedback: giữ `/api/feedbacks` flat paths + thêm `products` routes: `GET/POST /api/products`, `PATCH /api/products/{id}`; ingest (manual + CSV) tạo Import row và gắn import_id.

### Task 4 — Tests + DoD
- [ ] Unit + integration test: ingest manual/CSV ghi đúng JSONB shape; list/detail/similar hoạt động; reports summary xanh trên cột mới.
- [ ] `uv run pytest` xanh · `uv run alembic upgrade head` trên Supabase OK · `/api/health` xanh.

## DoD

- User tạo Product, import CSV → rows mới-shape có `data`/`source_meta` JSONB, `occurred_at`, gắn import.
- Không còn route/model/tham chiếu tới thiết kế cũ (grep `happynest_agent|hitl_graph|review_status|action_draft|human_review` = 0 hit trong `backend/app`).

## Verify

```bash
uv run pytest
uv run pytest -m integration
uv run alembic upgrade head
uv run uvicorn app.main:app  # /api/health + Swagger smoke
```
