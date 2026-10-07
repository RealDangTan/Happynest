# Handoff: Live LLM agent test green — 402 + pooler-drop fix-pack
- Date: 2026-09-24 12:10 local
- From: claude-code
- To: any
- Branch / worktree: codex/activity-center (shared checkout)
- Milestone: agent delivery — live LLM verification (outside phase table)
- Status: done

## Done
- Ran UNDERSTAND agent with real OpenRouter key (`stealth/space-bunny-alpha`) against Happynest product, full loop: planner → tools (aggregate_feedback, compare_periods, semantic_search) → evaluator → synthesize → Gate #2 → approve via real API.
- Fixed 3 issues found by the test (entry `docs/decisions.md` 2026-09-24): `LLM_MAX_TOKENS=8192` (OpenRouter 402 — key can only afford 47789 max_tokens), TCP keepalive on LangGraph checkpointer conn + `pool_pre_ping` on SQLAlchemy engine (Supabase pooler kills idle conns → `the connection is closed` at Gate #2 checkpoint write, 2/2 runs).
- Restarted backend server (was running without --reload) with same args; server left RUNNING on 127.0.0.1:8000.

## Evidence
- Run `d9cf2cb7-0d72-436c-ad1f-c601fecca741`: status=completed, ~12.5 min, insight `724087e3-4b4b-4aec-b37d-ce3019b7ccf1` approved with 5 evidence refs.
- `llm_call_logs`: 26 rows for the run (12 ok / 14 validate-retry — fallback chain, no 402 left).
- Langfuse auth HTTP 200; traces plan/evaluate/synthesize present 04:58–05:01 UTC.
- Package + raw logs: `backend/storage/agent-live/2026-09-24-live-llm-test-SUMMARY.md` (trace SQL + Langfuse filter inside).
- `uv run pytest -m "not integration"`: 81 passed, 87 deselected.

## Not done / gaps
- Owner target "1–2 minutes per run" NOT met: ~12.5 min (slow stealth model, 30–120s/call + prompt-JSON fallback doubles attempts). Provider-side per decisions 2026-09-16; needs owner decision (faster model or fewer iterations/budget).
- OpenRouter specs verified same day via `/auth/key` + `/credits` + `/models` + strict-json probe: model is $0/$0 FREE (context 1M), the 402 was OpenRouter's max_tokens credit-check — NOT a balance problem (account still has ~$5.57). No credit top-up needed. Strict `json_schema` IS supported by this model (handoff 2026-09-02 note obsolete); remaining validate errors are the model omitting required fields, not provider rejection.

## Blocked / risks
- None blocking. Gate #3 override not exercised in this run (insight had no actions generated — evidence-insufficient path).

## Next steps
1. Owner decides on latency: switch `LLM_MODEL` to a faster provider/model vs. accept ~12 min runs.
2. Re-run this test after any model change: `uv run python scripts/debug_real_llm_runs.py --runs 1` (from backend/, server up).
3. Consider Supabase dashboard: raise pooler idle timeout if keepalives ever stop being enough.
