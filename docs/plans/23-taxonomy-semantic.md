# Plan 23 — Taxonomy + Semantic Preprocessing Reshape

> Nguồn thiết kế: VoC OS plan §20–22 · Migration **0010** · Blocked by: 21 (song song 22 được).

## Mục tiêu

Phân loại ngữ nghĩa ghi vào `ai_analysis` JSONB theo taxonomy product-scoped; chủ đề mới đi hàng đợi emerging theme chờ human review; taxonomy canonical KHÔNG BAO GIỜ tự mutate (§21).

## Tasks

### Task 1 — Migration 0010
- [ ] `taxonomies` (id, product_id FK, parent_id FK self nullable, name, description, kind canonical|emerging, status active|pending_review|merged|rejected, evidence_count int, first_seen, last_seen, created_at). Unique (product_id, parent_id, name).
- [ ] Seed taxonomy mặc định cho product (AI Quality/Search/Account… theo §20 hoặc generic 5 nhánh) — data migration.

### Task 2 — Classifier reshape
- [ ] `classifier.py` output mới: topics[] (taxonomy node names), sentiment, severity, problem_type, analysis_version — ghi thẳng `ai_analysis` JSONB (bỏ cột flat categories/ai_issue/sentiment/severity/confidence đã drop ở 0008).
- [ ] Flow §21: match taxonomy hiện có (canonical + emerging active) → classify; không match → emerging theme candidate (accumulate evidence_count, first/last_seen) — classification row vẫn có topics=[candidate name].
- [ ] Bỏ few-shot correction loop (`correction_examples` đã drop) — classifier prompt v2.

### Task 3 — Taxonomy governance endpoints
- [ ] `GET /api/taxonomies?product_id=` (tree), `GET /api/taxonomies/review?product_id=` (emerging pending + evidence count), `POST /api/taxonomies/review/{id}` body `{action: approve|merge|reject, merge_into_id?}` (§21 flow — human duyệt).
- [ ] approve → kind=canonical/status active; merge → gộp evidence_count + feedback ai_analysis topics update; reject → status rejected.

### Task 4 — Runner + clustering thích ứng
- [ ] `analysis_runner.py` idempotent giữ nguyên pattern, ghi ai_analysis; filter list feedback theo topic giờ query JSONB containment.
- [ ] `clustering.py` đọc feedback_text embedding (không đổi logic); cluster naming giữ; cluster không đổi shape (sống sót từ phase 14).
- [ ] api-checklist sync.

### Task 5 — Tests + DoD
- [ ] Unit: classifier ghi ai_analysis đúng shape; emerging accumulate; merge/reject flows; guard jsonb_typeof khi query topics (pattern decisions 2026-08-26).
- [ ] DoD §72 Phase-3: feedback search semantically OK; group recurring issues OK; mọi kết quả semantic traceable về feedback gốc.

## Verify

```bash
uv run pytest && uv run pytest -m integration
uv run alembic upgrade head
```
