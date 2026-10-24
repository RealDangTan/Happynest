# Handoff: Run backend and frontend locally
- Date: 2026-10-23 21:58 local (Asia/Saigon)
- From: codex
- To: any
- Branch / worktree: codex/activity-center (existing checkout)
- Milestone: Owner request to run the repository; no active implementation plan
- Status: done

## Done
- Claimed local startup only; preserved all existing uncommitted work.
- Reused existing Next.js server on port 3000 (PID 29452).
- Started backend in its own terminal: `uv run --no-sync uvicorn app.main:app --reload` from `backend/` (reloader PID 9212; exec session 22397).
- Backend startup loaded Vietnamese and English Stanza processors.

## Evidence
- Fresh HTTP checks: `/landing` on port 3000 and `/docs` on port 8000 returned 200.
- Direct `/api/health` on port 8000 and proxied `/api/health` on port 3000 returned 200, `status=ok`, `db=ok`, `pii_mode=full`.
- Checked git status/log and latest October 23 handoffs before startup. No test-suite claims were relied upon; no application code changed or tests run.

## Not done / gaps
- Did not run paid AI workflows or mutate application data through requests.
- No migration or user seeding was necessary for these startup checks.

## Blocked / risks
- Sandbox could not inspect host listeners, access localhost, or persist uv interpreter cache; startup and HTTP verification succeeded with approved execution outside sandbox.
- Initial duplicate frontend launch exited after identifying the existing server; existing frontend was retained.
- Existing docs/README.md shared-workspace prose differs from current AGENTS.md per-account contract; outside this startup request.

## Next steps
1. Open http://127.0.0.1:3000/landing and log in.
2. API docs: http://127.0.0.1:8000/docs.
3. Stop the backend with Ctrl+C in its terminal when finished; frontend predates this session.
