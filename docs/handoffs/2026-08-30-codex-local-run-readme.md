# Handoff: Local services verified and README startup shortcut
- Date: 2026-08-30 16:37 local
- From: codex
- To: any
- Branch / worktree: main
- Milestone: Local run / developer documentation
- Status: done

## Done
- Confirmed the existing frontend and backend development services are both running.
- Added a concise two-terminal backend + frontend startup section to the root README.

## Evidence
- `Invoke-WebRequest http://127.0.0.1:3000/landing` → HTTP 200.
- `Invoke-RestMethod http://127.0.0.1:8000/api/health` → `status=ok`, `db=ok`, `pii_mode=full`.

## Not done / gaps
- No source, configuration, dependency, or database changes were made.

## Blocked / risks
- The working tree already contains many unrelated changes and untracked files; all were preserved.

## Next steps
1. Use `http://127.0.0.1:3000/landing` for the frontend and `http://127.0.0.1:8000/docs` for API documentation.
2. Run the commands in the new README section after a future restart.
