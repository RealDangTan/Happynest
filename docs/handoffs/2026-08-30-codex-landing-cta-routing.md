# Handoff: Landing CTA routing verification
- Date: 2026-08-30 15:19 local
- From: codex
- To: any
- Branch / worktree: main
- Milestone: FE-09 landing browser annotations follow-up
- Status: done

## Done
- Investigated browser annotations requesting `/login` routing for navbar “Open the nest” and hero “Start listening”.
- Confirmed source already contains `href="/login"` for both CTAs (`motion.tsx` navbar and `page.tsx` hero).
- Reloaded the annotated in-app browser tab, which replaced the stale pre-FE-09 bundle shown in the screenshots.
- Click-tested both CTAs; each navigated to `http://127.0.0.1:3000/login`.
- Returned the browser to the refreshed `/landing` page for owner review.

## Evidence
- Live DOM after reload: `openNestHref=/login`, `startListeningHref=/login`.
- Browser navigation: both destinations exactly `http://127.0.0.1:3000/login`.
- `pnpm test` → 4 files, 19 tests passed.
- `pnpm typecheck` → exit 0.

## Not done / gaps
- No production-code change was necessary; the mismatch was stale browser state.

## Blocked / risks
- None.

## Next steps
1. Continue reviewing the refreshed landing tab; hard-refresh if an older annotated screenshot reappears.
