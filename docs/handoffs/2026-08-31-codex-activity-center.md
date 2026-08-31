# Handoff: Navbar Activity Center & Budgeted Import Analysis

- Date: 2026-08-31 local
- From: codex
- To: any
- Branch / worktree: `codex/activity-center` / shared checkout
- Milestone: Backend phase 28 + FE-10
- Status: done

## Done

- Split CSV upload/profile from the explicit paid mapping proposal; added sanitized preview, queue filters, retry/reclaim, background import polling, and safe cancel.
- Added import-scoped selected/batch analysis preview and creation, 100-item cap, chunk size 10, exact claim, true batch calls, failure release, and cooperative cancellation.
- Added shared `ActivityProvider`, navbar capsule, URL-addressable Activity Sheet queue/import/run details, paid-action receipts, mapping review, item/batch selection, progress, stop controls, and detailed-results link.
- Removed the global analysis trigger and did not add an `/imports` route/sidebar item or mascot UI.
- Added migration `0015`, env defaults, API checklist/decision/index updates, and root README quick operating notes.

## Evidence

- Alembic: `0015 (head)` on Supabase dev.
- Backend unit: `56 passed, 74 deselected`.
- Backend integration: `74 passed, 56 deselected`; provider AI mocked.
- Phase 28 integration: upload did not call mapper; sanitized preview/cancel passed; batch 23 produced classify/embed chunks `[10, 10, 3]`.
- Frontend: Vitest `22 passed`; `tsc --noEmit` clean; ESLint clean.
- Frontend production build: 19/19 static pages generated successfully (rerun after final UI changes recorded in task output).
- Browser QA at `/feedbacks`: navbar activity capsule, queue Sheet, `?activity=queue`, resumable import detail, Back behavior, and zero browser console warnings/errors verified.
- No live LLM or embedding credit was used during verification.

## Not done / gaps

- Floating mascot remains intentionally out of scope; it should consume the existing `ActivityProvider` instead of polling again.
- No commit was created because the shared worktree already contained many unrelated user/agent edits, including overlapping README/docs files and untracked baseline migration `0014`.

## Blocked / risks

- Existing legacy analysis runs may remain in the database; Activity Center intentionally ignores runs without the new `import_id + mode` contract.
- Import profile sanitization uses the full Stanza/Presidio stack and is intentionally slower than plain CSV parsing.

## Next steps

1. Review/stage only phase 28 and FE-10 files before committing; preserve unrelated landing/public-site work.
2. Use the navbar **Hoạt động** capsule for import review and scoped analysis; `/analysis?run=<id>` remains the detailed results view.
3. When adding the mascot, read activity state from `ActivityProvider`; do not add another imports/runs poller.
