# Plan 22 — LISTEN: Schema Intelligence + Gate #1

> Nguồn thiết kế: VoC OS plan §4–14, §18–19, §56 · Migration **0009** · Blocked by: 21.

## Mục tiêu

CSV/thêm-dữ-liệu mới đi qua pipeline: deterministic profiler → LLM semantic mapper → human review (Gate #1) → validation → import. Product Schema registry versioned điều khiển mọi mapping; raw file lưu Supabase Storage.

## Tasks

### Task 1 — Migration 0009 + schema registry
- [ ] `product_schemas` (id, product_id FK, version int, definition JSONB, status draft|active|superseded, created_at). Definition: `{fields: [{key, label, description, type}]}` + system core fields tách hằng số (feedback_text, occurred_at, source, source_record_id — §9, không nằm trong definition).
- [ ] `services/schema_registry.py`: get active schema, create candidate version, activate (supersede cũ), resolution field key → JSONB path `data->>'key'`.

### Task 2 — Deterministic profiler (KHÔNG LLM)
- [ ] `services/profiler.py`: per column → `{name, detected_type (category|numeric|datetime|text|boolean), missing_rate, unique_count, cardinality, sample_values ≤5, min, max, avg_length}` (§7).
- [ ] Chỉ profile đi vào LLM — không bao giờ gửi toàn bộ CSV (§7 + guardrail §69).

### Task 3 — LLM Schema Mapper
- [ ] `services/llm_mapper.py` qua `llm_client.chat_structured` (call_type mới `schema_map` vào enum llm_call_type): input `{existing_schema, incoming_profiles}` → per-field `{source_field, decision: MAP|PROMOTE|SOURCE_META|IGNORE|AMBIGUOUS, target?, confidence, reason, needs_human_review}` (§10–11).
- [ ] Quy tắc trong prompt: promotion test §14 ("còn hợp lý nếu data từ source khác?"), remap imports sau (§13), AMBIGUOUS buộc needs_human_review=true, LLM không tự mutate schema (§11).
- [ ] Mapper KHÔNG ghi DB — chỉ trả proposal; persistence do Gate #1 quyết.

### Task 4 — Import flow + Gate #1 endpoints
- [ ] `POST /api/imports` (multipart, product_id): lưu raw CSV → Supabase Storage (`SUPABASE_STORAGE_BUCKET` env; storage_path lên Import row) → profile → LLM map → Import status `mapping_review` → trả mapping proposal. 409 nếu import đang dở mapping_review.
- [ ] `GET /api/imports/{id}/mapping` — proposal hiện hành.
- [ ] `POST /api/imports/{id}/mapping/decision` (Gate #1): body per-field `{decision: approve|remap|rename|promote|demote|ignore, target_key?}` → PROMOTE approve → candidate schema version (status draft, activate kèm import); parse + validate toàn bộ CSV (validator: kiểu theo schema, required core) → insert feedback rows (`data`, `source_meta` zones) → status `imported`. Errors per-row như CSV cũ.
- [ ] `GET /api/imports` list. Legacy `/api/feedbacks/import-csv` CHUYỂN sang flow này (route cũ bỏ; manual POST giữ, source_meta=rỗng, data={}).
- [ ] Coverage: `services/coverage.py` tính per-field coverage từ `data` JSONB (records_with_field/relevant_records) — expose `GET /api/products/{id}/schema/coverage` (§19).

### Task 5 — Tests + DoD
- [ ] Unit (LLM mock): profiler đúng stats; mapper contract; Gate #1 approve → schema version mới + rows imported; remap CSV thứ hai MAP vào schema hiện có không tạo field mới; AMBIGUOUS chặn auto-import.
- [ ] api-checklist sync cùng commit.

## DoD

- CSV đầu bootstrap Product Schema (bootstrap → human approve → import). CSV thứ hai map vào schema sẵn có. Không ALTER TABLE khi schema đổi (§72 Phase-2 DoD).

## Verify

```bash
uv run pytest && uv run pytest -m integration
uv run alembic upgrade head
# E2E thủ công: upload demo_dataset.csv → review mapping → approve → GET /api/feedbacks thấy data JSONB
```
