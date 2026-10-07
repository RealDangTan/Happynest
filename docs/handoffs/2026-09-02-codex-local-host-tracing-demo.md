# Handoff: Local hosting ready, live traced agent demo awaiting approval

- Date: 2026-09-02 02:04 local
- From: codex
- To: any
- Branch / worktree: `codex/activity-center` / shared checkout
- Milestone: Local hosting + VoC OS terminal demo + tracing verification
- Status: blocked

## Done

- Verified VoC OS agent code exists: LISTEN → UNDERSTAND LangGraph → Gate #2 → ACT → Gate #3.
- Confirmed local services are already listening: frontend `:3000`, backend `:8000`.
- Confirmed dual tracing config is enabled: Langfuse credentials present plus permanent metadata-only `llm_call_logs`.
- Verified Supabase migration head and selected existing classified demo scope without exposing feedback text.
- Preserved all pre-existing modified/untracked frontend prototype work.

## Evidence

- `GET /api/health` → `status=ok`, `db=ok`, `pii_mode=full`.
- `GET http://127.0.0.1:3000/landing` → HTTP 200.
- `python -m alembic current` outside sandbox → `0015 (head)`.
- Backend unit: `56 passed, 74 deselected`.
- Committed frontend tests only: `22 passed`; untracked FE-11 prototype test remains intentionally RED (artifact not built yet).
- Supabase metadata: Happynest has 689 feedback, 19 classified, 371 existing `llm_call_logs`; zero insights/actions before this demo.

## Not done / gaps

- No live UNDERSTAND/ACT run was created; no new LLM/Langfuse payload or insight/action was persisted.
- Public VPS deploy is unavailable: `infra/setup_vps.sh` is still a placeholder and no VPS credentials/domain are configured.
- Frontend has no Gate #2/#3 controls yet; terminal/API is the current demo surface.

## Blocked / risks

- Live demo requires explicit owner approval to send sanitized feedback-derived aggregates to the configured LLM and Langfuse, and to persist demo insight/action rows in Supabase.
- Full frontend test command includes the unrelated untracked FE-11 RED test; do not “fix” it as part of hosting.

## Next steps

1. Obtain explicit approval for the external LLM + Langfuse payload and persistent demo rows.
2. Run one Happynest UNDERSTAND investigation, inspect Gate #2, approve, then generate ACT actions.
3. Verify run-correlated `plan/evaluate/synthesize` metadata rows plus recent `act_generate` in `llm_call_logs` and Langfuse auth/ingestion.
4. Leave services running and report local URLs, run ID, insight ID, trace counts, and any provider fallback.
