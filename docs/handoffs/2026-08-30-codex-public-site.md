# Handoff: Happynest public site and full-viewport landing
- Date: 2026-08-30 15:16 local
- From: codex
- To: any
- Branch / worktree: main (owner-requested edits on existing uncommitted landing)
- Milestone: `docs/plans/FE-09-public-site.md`
- Status: done

## Done
- Applied all four browser annotations: desktop hero title 42px, full-viewport `/assets/landing-hero.webm` at 0.5x, `/assets/hero-video-mask.svg` bottom mask, white asset logo, Lora wordmark.
- Extended `/landing` with source intelligence, evidence anatomy, three human gates, team outcomes, honest system proof, and Q&A sections.
- Removed invented pilot/customer claims and replaced them with repository-backed architecture facts and research-prototype wording.
- Added typed marketing content plus shared shell for `/product`, `/company`, `/blog`, `/docs`, `/qna`, and `/legal`.
- Updated middleware so anonymous visitors can access all public pages while app routes remain guarded.

## Evidence
- TDD RED: focused test failed on missing `marketing-content` module, then on the old placeholder hero and missing section IDs.
- `pnpm test` → 4 files, 19 tests passed.
- `pnpm typecheck` → exit 0; `pnpm lint` → exit 0.
- `pnpm build` → exit 0; all 19 static/dynamic routes generated, including six new public routes.
- Browser desktop: 42px h1, Lora brand, video playing at 0.5, SVG mask resolved, no console errors or horizontal overflow.
- Browser responsive: mobile h1 36px, hero fills the viewport, no horizontal overflow. Reduced-motion emulation pauses/hides video and forces reveals visible.
- Browser route sweep: all six public pages loaded with 4–5 substantive sections and no horizontal overflow.

## Not done / gaps
- No commits were created. Existing unrelated backend and workspace changes were preserved.
- The repo still emits Next.js's existing `middleware.ts` deprecation warning; migration to `proxy.ts` was outside FE-09.

## Blocked / risks
- `next/font` needs network access on a cold production build; final build succeeded with access enabled.

## Next steps
1. Owner visually review the live `/landing` tab and tune copy/video crop if desired.
2. Commit FE-09 paths separately from unrelated backend/import work.
