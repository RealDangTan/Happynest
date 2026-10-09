# Handoff: ACT best-practices decision support
- Date: 2026-10-09 17:18 Asia/Saigon
- From: codex
- To: any
- Branch / worktree: codex/activity-center / existing normal checkout
- Milestone: docs/plans/35-act-best-practices.md
- Status: done

## Done
- Implemented approved plan inline; no subagents, Docker, dependencies or environment-file changes.
- 18 curated cards / 7 lenses; act-v2 includes up to 10 same-product evidence statements.
- Model supplies IDs; backend validates before mutations and hydrates canonical source metadata.
- Immutable JSONB decision_support snapshots; legacy/manual null; human decisions survive regeneration.
- Shared Matrix/Stakeholders analysis, original-proposal edit notice, safe links and legacy empty state.
- Migration 0017 applied to configured Supabase development DB; API checklist and decisions synced.
- Live walkthrough, evaluation report and reusable synthetic script added.
- Preserved unrelated existing dirty/deleted files. No commit, merge, push or PR performed.

## Evidence
- RED before implementation: grounding 12 failed / 2 passed; UI import failed as expected.
- Strict-schema regression RED (missing additionalProperties=false); GREEN 15 grounding tests.
- Final `uv run --no-sync pytest -p no:cacheprovider -m 'not integration' -q`: 107 passed, 109 deselected, 4 existing sklearn warnings.
- Final `uv run --no-sync pytest -p no:cacheprovider tests/test_act_agent.py tests/test_decision_kpis.py -m integration -q`: 10 passed (201 s).
- Final `pnpm test`: 49 passed; `pnpm typecheck` and direct touched-file ESLint exit 0.
- `pnpm build`: exit 0, 26 routes; existing middleware deprecation warning only.
- `uv run --no-sync alembic current`: 0017 (head).
- Final `python scripts/e2e_act_best_practices.py --live --keep`: 4/4 cases, 10 actions, 9 cited / 1 explicit gap; missing evidence -> investigate.
- Last 4 act-v2 llm_call_logs: gpt-4o-mini, nonzero token usage, error=NULL; strict mode accepted.
- Browser verified evidence, perspectives, canonical links/applicability and alternatives in Matrix and Stakeholders.
- Scoped tracked diff and new-file whitespace checks passed. Three superseded synthetic demo products removed by exact ID/name/description guards; final demo retained.

## Not done / gaps
- No production deployment or Git integration requested. Changes remain uncommitted.
- Small synthetic pilot does not measure effectiveness; targets/alternatives need judgement and one estimate basis claimed unprovided post-implementation ticket reduction (evaluation report).
- Existing useInsights fetches globally; product-filtering that hook was outside this plan.

## Blocked / risks
- No implementation blocker. See decisions 2026-10-09 for strict-schema and shared-DB KPI test-isolation fixes.
- Tests need elevated access to Stanza/Supabase here; use UV_CACHE_DIR under TEMP and STANZA_RESOURCES_DIR=D:\stanza_resources. No secrets in docs.
- Retained demo: ACT best-practices demo e7c021eb (e7c021eb-e5df-42b5-bc7a-a08ecef55e5a), artificial records only.
- Local preview left running: FastAPI :8000 (exec session 49322, restarted with final code), Next production :3000 (session 30308). Browser deliverable opens Matrix correction report; frontend edits need rebuild/restart.

## Next steps
1. Review current diff and evaluation; integrate only task files, preserving unrelated work.
2. Deploy migration before backend/frontend; retain JSONB snapshots during application rollback.
3. Use a larger labelled evaluation set before making claims about persuasive quality or impact.
