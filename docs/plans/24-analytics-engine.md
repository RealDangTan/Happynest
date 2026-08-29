# Plan 24 — Analytics Engine: 9 MVP Tools + Query Compiler

> Nguồn thiết kế: VoC OS plan §29–37, §69 · Không migration · Blocked by: 22 (schema registry), 23 (ai_analysis).
>
> **Lệch thực thi 2026-08-28:** tool thứ 9 `search_similar_cases` cần bảng `insights` (embedding) mà plan 25 mới tạo → đăng ký tool này ở phase 25; tại đây 8/9 tool. Tool KHÔNG expose HTTP (đúng plan) — checklist API không đổi.

## Mục tiêu

Lớp tool deterministic cho agent: LLM chỉ gửi semantic tool request; query compiler validate theo Product Schema rồi mới chạm DB; kết quả compact + kèm coverage. LLM không bao giờ thấy toàn bộ dataset, không bao giờ viết SQL (§29, guardrail §68).

## Tasks

### Task 1 — Query compiler + khung tool
- [x] `app/analytics/query_compiler.py`: resolve field key → JSONB path; validate filter/group_by/dimensions chống active product schema; từ chối field lạ (ValueError → observation, không crash).
- [x] `app/analytics/registry.py`: pattern `ToolSpec{name, description (EN cho router), input_model, output_model}` + `EXECUTORS` — kế thừa pattern từ code stripped 17–18 (git history là tham khảo).

### Task 2 — 9 tools (mỗi tool 1 file `app/analytics/tools/`)
- [x] `get_schema(product_id)` → dimensions + coverage (§31).
- [x] `profile_field(product_id, field)` → coverage, distinct, top_values ≤5 (§32).
- [x] `aggregate_feedback(filters, group_by, metric)` → GROUP BY JSONB + metric count|avg_severity (§33).
- [x] `compare_periods(filters, current, previous)` → counts + change_pct (§34); window literals `last_7_days|last_30_days|previous_7_days|…`.
- [x] `segment_feedback(issue, dimensions)` → per-dimension coverage + top + share (§35).
- [x] `semantic_search(query, filters, k)` → pgvector cosine kNN trên feedback_text embedding, k ≤ MAX_RAW_FEEDBACK_PER_TOOL (§36).
- [x] `representative_feedback(issue/filters, n)` → diverse sampling (khác user/source/ngôn ngữ — heuristics: source xen kẽ, similarity dedup threshold) (§37).
- [x] `inspect_cluster(cluster_id)` → metrics + sample ids (kế thừa `get_cluster_metrics`).
- [x] `search_similar_cases(query_text/insight_id)` → kNN insights (kế thừa precedent retrieval pattern 17).
- [x] Hằng số guard: `MAX_ITERATIONS=8` reserved cho phase 25; `MAX_RAW_FEEDBACK_PER_TOOL=30`, `MAX_TOTAL_VERBATIMS=80` vào `core/config.py` (§40).

### Task 3 — Coverage luôn đi kèm
- [x] Mọi tool trả aggregate theo dimension đều kèm coverage của dimension đó (§19 — agent phải dùng coverage khi đánh giá evidence).

### Task 4 — Tests + DoD
- [x] Unit per tool trên DB seed (integration): output shape, guard >30 rows, coverage present, field lạ bị từ chối.
- [x] Không expose HTTP — chỉ registry nội bộ cho phase 25 (assert qua test import).

## DoD

- Agent có thể hỏi mọi câu phân tích §26 mà không có SQL trực tiếp; mọi query validate theo schema; coverage đi kèm kết quả (§72 Phase-4 DoD).

## Verify

```bash
uv run pytest && uv run pytest -m integration
```
