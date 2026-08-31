# Handoff: CSV mapping button read-only inspection
- Date: 2026-08-30 17:10 local
- From: codex
- To: any
- Branch / worktree: main
- Milestone: Feedback CSV import diagnostic
- Status: done

## Done
- Inspected the CSV mapping button, its frontend request flow, import endpoint, and current service logs without changing code or data.

## Evidence
- `GET /api/health` returned `status=ok`, `db=ok`, `pii_mode=full`.
- Frontend `startUpload()` returns with toast `Hãy chọn file CSV.` when no file is selected; the annotated dialog showed “No file chosen”, so it makes no backend request.
- Backend log records `POST /api/imports` → `409 Conflict`; route source explains this is returned when the selected product already has an import in `mapping_review` status.

## Not done / gaps
- No change was requested or made. The pending import was not inspected or modified.

## Blocked / risks
- The current UX does not visibly expose an existing pending mapping review from this initial dialog; a user can encounter the 409 after choosing a file.

## Next steps
1. Select a CSV before pressing the button; this will invoke the backend and open Gate #1 on success.
2. If it displays the 409 message, complete or otherwise resolve the existing mapping-review import before starting another for the same product.
