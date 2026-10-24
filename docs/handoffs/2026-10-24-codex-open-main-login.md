# Handoff: Restore local login UI; waiting for valid credentials
- Date: 2026-10-24 local (Asia/Saigon)
- From: codex
- To: any
- Branch / worktree: codex/activity-center; existing checkout
- Milestone: User requested browser navigation into the main screen
- Status: in-progress

## Done
- Used current in-app browser tab, switched register to login and submitted existing form values without reading the password.
- Added localhost/127.0.0.1 to Next.js allowedDevOrigins after dev logs reported blocked loopback HMR. Automatic Next restart restored handlers; language toggle verified and returned to VI.
- Started backend alone with `uv run --no-sync uvicorn app.main:app --reload` (approved execution; exec session 16108, reloader PID 36732).
- Backend initially failed importing feedback route: another concurrent editor fixed func.case; this session fixed both confidence casts to SQLAlchemy Float.
- App now serves auth requests; existing browser form credentials return 401 and the visible UI reports incorrect email/password.
- Asked user to enter correct credentials directly on the page; never requested password in chat.
- Appended dated decisions for loopback origins and SQL cast correction.

## Evidence
- `npm exec -- eslint next.config.ts`: exit 0.
- Backend .venv Python imported app.main and compiled every feedback sort against PostgreSQL dialect: exit 0, OK.
- Backend telemetry: POST /api/auth/token 401; visible matching error, no proxy failure.
- Browser screenshot saved under tmp/login-status-2026-10-24.png; tab marked deliverable.

## Not done / gaps
- Main screen not reached: valid credentials required. User input request is pending.
- No authentication bypass, account creation, password change, paid AI calls or DB mutations performed.

## Blocked / risks
- Startup reports Stanza Vietnamese NER model load failure; service continues with its existing fallback. Did not alter PII configuration.
- Browser automation generated an existing theme-provider event.key TypeError in dev issue badge; not changed in this task.
- Shared worktree changed concurrently (feedback route); preserve others' edits. No commits made.

## Next steps
1. After user enters valid credentials, submit login and verify main/importer page visibly renders.
2. Keep backend session running for user; do not launch a duplicate on port 8000.
