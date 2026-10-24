# Handoff: Explain current ACT routing and weighted priority
- Date: 2026-10-24 local
- From: codex
- To: any
- Branch / worktree: current shared checkout; inspection only
- Milestone: User question about current ACT behavior (no implementation plan)
- Status: done

## Done
- Inspected current ACT service, grounding, curated practices, API guards, schemas and frontend matrix/stakeholder priority labels.
- Confirmed per-function relevance threshold is separate from per-action priority.
- Confirmed human score overrides recompute priority while preserving original agent estimates.

## Evidence
- Read AGENTS.md, docs/README.md, active board and recent handoffs; inspected git log/status.
- Executed backend/.venv/Scripts/python.exe against current settings and actual priority_score function: weights impact=.4, urgency=.3, confidence=.2, effort=.1; relevance threshold=.5.
- Example impact=8, effort=3, urgency=9, confidence=.8 returned 8.2 (exit 0).
- No LLM calls, DB writes, API mutations or integration test runs.

## Not done / gaps
- Did not verify running server's cached settings or live model quality; explanation describes current source and settings loaded in a fresh process.

## Blocked / risks
- Existing worktree contains extensive unrelated changes; left untouched.
- docs/README.md and active board retain old shared-workspace descriptions, conflicting with AGENTS.md per-account contract; docs/handoffs/README.md is deleted in existing worktree. No ACT conclusions depend on those stale statements.

## Next steps
- None for this explanation. No production code changed.
