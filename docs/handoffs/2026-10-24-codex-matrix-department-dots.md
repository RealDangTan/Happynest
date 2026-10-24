# Handoff: Compact department-colored priority matrix
- Date: 2026-10-24 local (Asia/Saigon)
- From: codex
- To: any
- Branch / worktree: codex/activity-center; existing checkout
- Milestone: User revision of readable matrix labels
- Status: done

## Done
- Owns this UI revision; follows up 2026-10-24-codex-readable-matrix-labels.md.
- Replaced large recommendation chips with 12px department-colored dots and 24px click/drag targets.
- Full recommendation, department, status and scores remain in hover/focus tooltips and accessible names; click opens the drawer.
- Added a compact, wrapping legend below the chart showing departments in the current filtered results.
- Added stable semantic department color tokens for light/dark themes in globals.css.
- Rejected actions use hollow dots of their department color.
- Removed wide-label position clamping; restored the original point coordinates.
- No API changes or new dependencies; preserved other dirty work.

## Evidence
- `npm run typecheck`: exit 0.
- `npm exec -- eslint "app/(app)/matrix/page.tsx"`: exit 0.
- `npm test -- lib/matrix.test.ts`: 4/4 passed, exit 0 (TEMP/TMP set to ignored .next/test-tmp).
- `git diff --check` on matrix page and globals.css: exit 0, line-ending warnings only.

## Not done / gaps
- No live browser visual verification in this revision.
- No new tests for this presentation-only change; existing matrix tests were run.

## Blocked / risks
- Coincident points retain existing overlap behavior; no layout displacement added.

## Next steps
- Review the refreshed matrix in the running app. No commit created.
