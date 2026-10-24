# Handoff: Start local backend and frontend
- Date: 2026-10-24 08:14 local (Asia/Saigon)
- From: codex
- To: any
- Branch / worktree: codex/activity-center; existing checkout
- Milestone: Owner request to run the repository
- Status: done

## Done
- Claimed local startup; checked AGENTS, docs, active board, recent handoffs and git status/log.
- Verified no server was listening on 3000/8000 before starting.
- Started backend alone with `uv run --no-sync uvicorn app.main:app --reload` from backend; exec session 76044, reloader PID 24128.
- Started frontend with `pnpm dev` from frontend; exec session 80302. Both servers remain running.
- pnpm automatically synchronized the previously stale lockfile with the existing package.json dependency @tanstack/react-table 9.3.1 and installed its dependencies. No package.json or application source edits.
- Queued the login page in the Codex browser panel.

## Evidence
- Fresh HTTP checks: http://127.0.0.1:3000/login and http://127.0.0.1:8000/docs returned 200.
- Direct and frontend-proxied /api/health returned 200, status=ok, db=ok, pii_mode=full.
- Startup loaded both Vietnamese and English Stanza processors successfully.

## Not done / gaps
- No tests, paid AI calls, migrations, seeding or login attempts were needed.
- Existing extensive user changes preserved; no commit made.

## Blocked / risks
- Sandbox blocks local sockets; server startup and HTTP checks used approved execution outside sandbox.
- docs/README.md retains shared-workspace prose inconsistent with AGENTS.md account isolation contract; outside startup scope.

## Next steps
1. Open http://127.0.0.1:3000/login and sign in.
2. API docs: http://127.0.0.1:8000/docs.
3. Use Ctrl+C in each server session when finished; reuse these servers while running.
