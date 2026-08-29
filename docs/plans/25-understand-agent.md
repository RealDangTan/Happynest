# Plan 25 — UNDERSTAND Agent (strip & rewrite) + Gate #2

> Nguồn thiết kế: VoC OS plan §23–43, §60 · Migration **0011** · Blocked by: 24.

## Mục tiêu

Graph LangGraph điều tra evidence-grounded: load_context → planner → tool loop (record evidence → evaluate) → synthesizer → HITL interrupt (Gate #2) → save insight. Insight model mới tách finding vs hypothesis (§41).

## Tasks

### Task 1 — Migration 0011
- [x] `evidence` (id, run_id FK analysis_runs, product_id FK, type, statement TEXT, payload JSONB, coverage float nullable, source_tool, created_at).
- [x] `insights` (mới): id, product_id FK, run_id FK nullable, title, finding TEXT, finding_confidence float, hypothesis JSONB nullable ({statement, confidence}), affected_context JSONB, impact JSONB (list), limitations JSONB (list), evidence JSONB (list evidence_id), status pending|approved|edited|rejected|investigating, created_at.
- [x] `insight_reviews` (id, insight_id FK CASCADE, original_value JSONB, edited_value JSONB, action enum approve|edit|investigate_more|reject, reason, reviewer_id FK users, created_at) — tái sử dụng pattern cũ. Enum `insight_review_action` mới (cũ dùng chung review_action — bỏ).
- [x] `llm_call_type` ADD VALUE 'plan','evaluate','synthesize' (route/critic cũ đã bị DROP cùng 0007? — kiểm tra: enum values cũ còn sót thì ALTER TYPE ADD, không DROP VALUE).

### Task 2 — Package `backend/understand_agent/`
- [x] `state.py`: UnderstandState theo §25 (product_id, question, trigger_type, product_context, schema, taxonomy, available_dimensions, investigation_plan, hypotheses, evidence, contradictions, coverage_warnings, tool_history, iteration, finding_confidence, hypothesis_confidence, draft_insight, human_review).
- [x] `graph.py` theo §60: load_context (deterministic: product + schema + coverage + taxonomy + clusters + historical insights) → planner_node (LLM, call_type=plan) → router → dispatch (9 tools registry phase 24) → record_evidence (INSERT evidence row mỗi tool response) → evidence_evaluator (LLM call_type=evaluate — supports/contradictions/new_questions/next_action §39) → decide {plan again | synthesize | limited} → insight_synthesizer (LLM call_type=synthesize) → interrupt (Gate #2) → save_insight. limited-insight path khi không đủ evidence (§60 generate_limited_insight).
- [x] Budget: kế thừa pattern cap qua llm_call_logs + `AGENT_MAX_STEPS` đổi tên `UNDERSTAND_MAX_STEPS=8` iterations, LLM budget config riêng. Stop conditions §40 (evidence sufficient / no tools / confidence flat / max iterations).
- [x] Whitelist evidence: synthesizer chỉ được trích evidence_id có thật trong state; insight phải reference evidence — guardrail §68.
- [x] finding vs hypothesis: confidence tách riêng, synthesis prompt cấm trình bày hypothesis như root cause xác nhận (§41).

### Task 3 — Runner + routes (Gate #2)
- [x] `jobs/understand_runner.py`: trigger 2 loại (§26) — user question + system signal (spike/emerging từ clusters); background-thread + SelectorEventLoop (quirk S5, decisions 26/08); `analysis_runs.pipeline_version='understand-v1'`.
- [x] `POST /api/agent/runs` {product_id, question?} → 200 {run_id}; `GET /api/agent/runs/{id}` (interrupt payload: finding, evidence refs, affected_context, hypothesis, confidence, limitations); `POST /api/agent/runs/{id}/decision` {action: approve|edit|investigate_more|reject, edited_*?} — investigate_more resume graph về planner; approve/edit → save_insight status; reviewer_id từ token.
- [x] Checkpointer AsyncPostgresSaver + ensure-tables pattern từ code stripped (tham khảo git history 1f66198).
- [x] `GET /api/insights` shape mới (evidence refs expand từ bảng evidence).

### Task 4 — Tests + DoD
- [x] Unit graph (LLM mock): ≥2 tool calls trong 1 investigation; evidence rows ghi; limited insight khi thiếu evidence; interrupt/resume approve/edit/reject + investigate_more; edit path re-sanitize text qua presidio trước persist; budget cứng.
- [x] DoD §72 Phase-5: investigate user question nhiều bước, evidence traceable, nhận diện thiếu evidence, human approve/edit/reject.

## Verify

```bash
uv run pytest && uv run pytest -m integration
uv run alembic upgrade head
```
