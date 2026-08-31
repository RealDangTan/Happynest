# Handoff: CSV encoding upload diagnosis

- Date: 2026-08-31 15:36 local
- From: codex
- To: any
- Branch / worktree: `codex/activity-center` / shared checkout
- Milestone: Phase 28 follow-up diagnosis
- Status: done

## Done

- Read-only inspection of the reported UTF-8 decode error.
- Traced it to `POST /api/imports`: deterministic profiling decodes uploads as `utf-8-sig` before persistence.
- Confirmed the failing request returned HTTP 422; mapping/LLM was not invoked.

## Evidence

- Backend terminal: `POST /api/imports HTTP/1.1` returned `422 Unprocessable Entity`.
- `profile_csv_for_import()` calls `profile_csv_bytes(raw)` and `raw.decode("utf-8-sig")`; `stage_import()` saves the raw file only after profiling succeeds.

## Not done / gaps

- The rejected upload is not retained, so its actual source encoding could not be inspected.
- No code was changed; likely source encodings include Excel ANSI/Windows-1258 or Windows-1252.

## Blocked / risks

- Supporting legacy encodings safely requires an explicit product decision and tests; silent fallback can decode text incorrectly.

## Next steps

1. Re-export the source file as **CSV UTF-8 (Comma delimited)** and retry.
2. If desired, add encoding detection/selection plus a friendly validation message in a separate bugfix.
