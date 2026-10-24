# LISTEN throughput Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the `executing-plans` skill to implement this plan task-by-task INLINE (no subagents in this repo — limited LLM API credit). Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Reduce LISTEN wall time without changing one-feedback-per-JEV-request classification, confirmed scope, or durable per-item progress.

**Architecture:** Reuse provider HTTP clients. A bounded thread pool computes at most three independent items while one coordinator owns SQLAlchemy sessions and commits each result together with its buffered provider metadata. Cancellation and excessive failures stop submission, drain already-started work, and release remaining claims.

**Tech Stack:** Existing Python 3.12, concurrent.futures, contextvars, httpx/OpenAI SDK, SQLAlchemy, pytest, Supabase. No new dependencies.

**Spec:** Owner request 2026-10-23; AGENTS.md isolation/PII/receipt contract; docs/handoffs/2026-10-23-codex-jev-latency-diagnosis.md.

## Global Constraints
- Raw content never enters prompts, logs, traces, or docs; sanitize legacy rows before submitting work.
- One enrich + one embedding request per item; no extra items beyond confirmed claims, no model/provider substitution.
- Coordinator owns DB sessions; worker threads receive plain snapshots and never share ORM sessions.
- Preserve per-item atomic result/progress persistence, errors/unclaim, resume and cancellation.
- Preserve permanent llm_call_logs; standalone calls still write immediately.
- Reuse this checkout because the running application depends on substantial uncommitted JEV/isolation changes absent from HEAD. No commits or worktree transfer of unrelated WIP.

### Task 1: Reuse provider clients
**Files:** backend/app/services/{jev_client,embedder}.py, backend/app/main.py, backend/tests/test_provider_client_reuse.py.
- [x] Add tests that perform two real httpx MockTransport-backed JEV requests using one client; the second must remain usable, and retry behavior remains covered by existing tests.
- [x] Run `uv run --no-sync pytest tests/test_provider_client_reuse.py -q` and observe failure before implementation.
- [x] Cache clients with guarded initialization; expose lifecycle close functions and call them during lifespan shutdown. Embedding client retains existing model/base_url/key resolution.
- [x] Re-run reuse tests and existing JEV/embedder tests.

### Task 2: Persist provider metadata with the item
**Files:** backend/app/services/{tracing,llm_client,embedder}.py, backend/tests/test_deferred_call_logs.py.
- [x] Add tests exercising real log writers inside nested/thread-isolated capture contexts, including error metadata, feedback/run attribution and immediate writes outside a context.
- [x] Observe failure, then implement a ContextVar capture context yielding metadata rows; coordinator persists captured rows using its transaction. Telemetry and Langfuse invocation retain current behavior.
- [x] Verify successful and failed provider attempts remain represented; context cleanup occurs on exceptions.

### Task 3: Bound computation and reduce runner DB round trips
**Files:** backend/app/jobs/{analysis_runner,analysis_workers}.py, backend/app/core/config.py, .env.example, backend/tests/test_analysis_workers.py, backend/tests/test_enricher_idempotency.py.
**Interfaces:** `process_items(items, process, save, should_stop, *, max_workers)` accepts snapshots, computes in workers, saves on its caller thread, and drains in-flight work when stopped. `ANALYSIS_WORKERS` is validated 1..4, default 3.
- [x] Add real executor tests using threading Events: computation overlaps within the cap; save stays on the coordinator; stop prevents new submissions but saves started results.
- [x] Run failing scheduler tests, implement bounded scheduling, and re-run.
- [x] Replace per-item refresh/pick with a lean pending snapshot; workers capture provider logs and return result/error; coordinator performs guarded feedback updates, atomic counter increments, captured log inserts, and per-item commits.
- [x] Add real PG regression coverage for concurrent completion, cancellation/drain, failures/unclaim, resume, correct log attribution and completed-item skip. Keep provider calls mocked.
- [x] Run existing runner/cost/isolation integration tests and full backend unit suite. No live paid inference is required.

### Task 4: Evidence and delivery
**Files:** docs/decisions.md, docs/api-checklist.md, docs/plans/00-index.md, docs/handoffs/2026-10-23-codex-listen-throughput.md.
- [x] Benchmark the same synthetic item workload with one and three workers, mocked providers, real DB, and permanent metadata logs; report workload and limits, never claim real provider speedup from mocked results.
- [x] Document worker cap, cancellation/drain behavior, benchmark results and rollback setting (`ANALYSIS_WORKERS=1`); sync API checklist execution behavior without schema changes.
- [x] Restart the local backend after tests, verify direct and proxied health, leave append-only handoff, and report measured results.
