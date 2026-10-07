# Handoff: Live synthetic agent test with dual tracing

- Date: 2026-09-02 02:13 local
- From: codex
- To: any
- Branch / worktree: `codex/activity-center` / shared checkout
- Milestone: VoC OS agent live terminal test
- Status: review-requested

## Done

- Ran the real UNDERSTAND LangGraph twice on isolated `understand-test-product` with synthetic context; no Happynest feedback was sent externally.
- Exercised planner → synthesize → Gate #2 → ACT on run `d8afcd9a-0b2e-4223-87e4-9919f7b66893`.
- Exercised planner → `get_schema` tool ×3 → evidence → evaluator → synthesize → Gate #2 on run `803e42f3-b020-4585-b855-0c2af59c75e7`.
- Approved both synthetic insights through the real HITL resume path.
- Verified Langfuse authentication and permanent Postgres trace metadata.

## Evidence

- Run 1 insight `77a510d6-812c-4272-a5dc-0293aee5e96b`: approved; empty-data conclusion; ACT created 0 and skipped all 8 functions.
- Run 1: 5 run-correlated traces plus 2 `act_generate` traces; strict JSON failed and prompt-JSON fallback succeeded.
- Run 2 insight `34443a86-adbd-42bf-a2e4-462461ba8c89`: approved; 3 evidence refs/rows.
- Run 2: 16 traces = 8 strict-mode provider failures + 8 successful prompt-JSON calls (`plan`, `evaluate`, `synthesize`).
- Final fresh check: backend `ok`, DB `ok`, PII `full`, frontend HTTP 200, Langfuse auth `true`.
- Preflight earlier in session: Alembic `0015 (head)`; backend `56 passed`; committed frontend tests `22 passed`.

## Not done / gaps

- Real Happynest data was intentionally not used; this test validates orchestration and tracing with synthetic/empty data.
- No source code or endpoint was changed.
- ACT correctly emitted no actions for the no-evidence synthetic insight, so Gate #3 override was not exercised.

## Blocked / risks

- Lifecycle bug found: after Gate #2 approval, both `AnalysisRun` rows remain `status=running` and `completed_at=NULL` while their insights are `approved`.
- Configured model/provider rejects strict structured output (`INVALID_REQUEST_BODY`); fallback works but doubles attempts/latency and records expected failed traces.
- UI still lacks Gate #2/#3 controls; current agent demo surface is API/terminal.

## Next steps

1. Fix UNDERSTAND lifecycle completion in `apply_decision`/runner with a regression test; update Activity/status expectations.
2. Consider provider capability configuration to skip unsupported strict JSON mode and reduce duplicate failed calls.
3. Add a seeded synthetic fixture with non-empty classified feedback to exercise successful ACT actions and Gate #3.
4. Only run against Happynest data after explicit approval for its sanitized derived payload to the configured LLM/Langfuse.
