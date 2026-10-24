# Handoff: LISTEN v5 throughput optimization
- Date: 2026-10-23 23:25 local (Asia/Saigon)
- From: codex
- To: any
- Branch / worktree: codex/activity-center (existing checkout, uncommitted)
- Milestone: docs/plans/38-listen-throughput.md; owned optimization requested by owner
- Status: done

## Done
- Reused checkout because JEV/isolation dependencies are uncommitted WIP absent from HEAD; preserved unrelated work. No commits/merges.
- JEV httpx and embedding OpenAI clients reuse connection pools with locked initialization and lifespan cleanup. Locked Langfuse initialization and propagated trace context into workers.
- Runner v5: lean sanitized snapshots; default `ANALYSIS_WORKERS=3` (validated 1–4); bounded I/O pool, no worker ORM sessions; coordinator commits each guarded result + attempt logs + atomic progress increment together.
- Native process guard prevents overlapping invocations of the same run. Completed/cancelled runs skip providers. Crash preserves unfinished claims for resume.
- Cancel / >50% failure stops submissions and drains started requests, then unclaims unstarted rows. Item errors and embedding crashes retain attempt metadata.
- Synced API checklist execution/cancel behavior, env example, plan board, and dated decision. No package/schema/provider/model changes.

## Evidence
- RED: 8 new client/capture/scheduler tests initially failed; real-PG concurrency test failed against original sequential runner. Trace-context/exporter race tests also observed RED before fixes.
- Final default suite (run alone after benchmark cleanup): `uv run --no-sync pytest -q` → 163 passed, 133 deselected, 4 existing sklearn FutureWarnings.
- `pytest -m integration tests/test_listen_throughput_integration.py -q -x` → 3 passed (parallel completion/logs, cancel/drain, failure/unclaim).
- `pytest -m integration tests/test_enricher_idempotency.py tests/test_phase28_integration.py tests/test_product_isolation.py -q` → 4 passed, 8 deselected (isolation tests are unit and passed in default suite).
- Added crash/resume integration test run separately → 1 passed. Selected integration total: 8 passed.
- Controlled baseline v4 vs v5: 6 synthetic rows, 1 s enrich + 1 s embed per item, real Supabase, one pass: 38.881→15.323 s (2.54x), 41→23 SQL statements, 19→7 commits. No paid provider requests.
- Evidence including runner hashes: docs/evidence/listen-throughput-2026-10-23.json. Local harness/original runner remain under ignored tmp/.
- Benchmark/fixture records cleaned by their exact identifiers; removed 23 own synthetic rows left by an early phase28 assertion failure.
- Restarted backend with `uv run --no-sync uvicorn app.main:app --reload`, exec session 47872, reloader PID 4956. Direct + proxied health: HTTP 200, status/db ok, PII full, engine jev; `/register` HTTP 200.
- Lightweight runtime settings check confirmed `ANALYSIS_WORKERS=3`; final backend health remained ok/full.

## Not done / gaps
- No live provider throughput benchmark; do not extrapolate synthetic 2.54x into an API SLA. HTTP reuse benefit was regression-tested, not timed against live providers.
- Initial default-suite run overlapped benchmark writes and one global report-delta assertion failed. Code inspection confirmed that test reads shared DB; final isolated run passed all 163. Some nominal unit tests access real PG.
- No full integration-suite run; selected persistence/cancellation/resume regressions and full default suite cover this change.
- An extra diagnostic interpreter importing the entire runner/NLP stack hit an OpenBLAS allocation error under concurrent local memory load. Avoided duplicating NLP imports; lightweight settings check succeeded and running backend health stayed healthy.

## Blocked / risks
- Captured metadata is in RAM until per-item commit; a process kill can lose in-flight attempt metadata. Committed logs remain durable; non-runner calls still log immediately.
- Stop can finish up to the configured worker cap already started; request budget/scope stays one enrich+embed per claimed item.
- Duplicate-run guard is process-local, matching current native single-process setup; no distributed worker claim protocol introduced.
- Other local edits (e.g. tests/test_auth_google.py) triggered the dev reloader during startup; they were not changed by this task.

## Next steps
1. Run analysis from the existing UI; compare a new v5 run with old v4 durations, accounting for provider/network variation.
2. Set `ANALYSIS_WORKERS=1` in backend/.env and restart if sequential execution is preferred; HTTP reuse/log batching remain active.
