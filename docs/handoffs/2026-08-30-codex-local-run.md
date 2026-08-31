# Handoff: Local development services started
- Date: 2026-08-30 00:21 local
- From: codex
- To: any
- Branch / worktree: main
- Milestone: Local run / environment verification
- Status: done

## Done
- Started the Next.js development server for the frontend.
- Started the FastAPI development server for the backend using its existing virtual environment.
- Allowed the backend process to access its configured external services; full Stanza Vietnamese/English PII models and the Postgres checkpoint saver initialized successfully.

## Evidence
- `curl.exe --fail --silent --show-error http://127.0.0.1:8000/api/health` → HTTP 200 with `status: ok`, `db: ok`, `pii_mode: full`.
- `curl.exe --fail --silent --show-error --output NUL --write-out "frontend_status=%{http_code}" http://127.0.0.1:3000/landing` → `frontend_status=200`.
- Frontend: `http://127.0.0.1:3000/landing`; backend: `http://127.0.0.1:8000/docs`.

## Not done / gaps
- No code or configuration changes were made for this run. The worktree already contained unrelated modified and untracked files; they were preserved.

## Blocked / risks
- None for startup. The backend's initial model load can take roughly a minute.

## Next steps
1. Use the frontend at port 3000 and Swagger API documentation at port 8000.
2. Stop the two development-server processes when they are no longer needed.
