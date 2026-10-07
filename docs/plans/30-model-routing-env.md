# Plan 30 — Model routing qua .env (per use case)

> Nguồn: spec Listen 2026-10-07 + decisions cùng ngày · Blocked by: — · Owner muốn đổi model cho từng use case bằng cách sửa `.env`, không vào OpenRouter pick tay.

## Mục tiêu

Mọi LLM call đều resolve model theo chuỗi `MODEL_<USE_CASE>` → `LLM_MODEL`. Kèm khối env cho engine enrich (`llm|jev`) + Jev creds + threshold.

## Tasks

- [ ] Task 1 — `app/core/config.py`: fields `MODEL_SCHEMA_MAP / MODEL_ENRICH / MODEL_TAXONOMY_GENERATE / MODEL_TOPIC_RECOMMEND / MODEL_CLUSTER_NAME / MODEL_INSIGHT / MODEL_UNDERSTAND / MODEL_ACT` (default rỗng) + `ENRICH_ENGINE` (validate `llm|jev`) + `JEV_API_BASE/JEV_API_KEY/JEV_MODEL="jev-latest"` + `ENRICH_TOPIC_CONFIDENCE_FLOOR=0.60`; helper `llm_model_for(use_case)`.
- [ ] Task 2 — `services/llm_client.py`: `chat_structured(..., model: str | None = None)`; `_api_call` dùng override; trace/`llm_call_logs` ghi đúng model đã dùng.
- [ ] Task 3 — Wire caller: schema mapper (`schema_map`), cluster namer (`name_cluster`), insight (`generate_insight`), understand graph 3 node (`MODEL_UNDERSTAND`), act (`act_generate`), classifier/enricher (`MODEL_ENRICH`).
- [ ] Task 4 — Health endpoint: map model đã resolve per use case (owner tự kiểm chứng routing).
- [ ] Task 5 — `.env.example` + `backend/.env`: thêm block ROUTING/ENGINE/threshold (giá trị rỗng, owner tự điền).
- [ ] Task 6 — Tests (RED trước): resolution chain (override → fallback), health payload chứa map.

## DoD

`uv run pytest -m "not integration"` xanh; set `MODEL_ENRICH` khác `LLM_MODEL` → restart → `/api/health` phản ánh đúng; SQL check: `SELECT call_type, model, COUNT(*) FROM llm_call_logs GROUP BY 1,2`.
