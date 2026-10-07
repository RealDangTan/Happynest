# Handoff: FE-12 six-screen UI rebuild complete + live-verified through all 3 gates
- Date: 2026-09-15 21:45 local
- From: claude-code
- To: any
- Branch / worktree: codex/activity-center / existing checkout
- Milestone: docs/plans/FE-12-ui-flow-six-screens.md
- Status: done

## Done
- Rebuilt the authenticated FE into the six-screen journey per `docs/design/2026-09-15-ui-flow/01-user-flow-ascii.md`:
  - S01 `/importer` + L01–L04 wizard (File → Preview → Mapping G1 → Result), 4 disabled source tiles, recent imports, continue-mapping.
  - S02 `/vault` + L05 analysis receipt/progress + D01 detail drawer (similar feedback, explore-topic link).
  - S03 `/data-graph` (datasets scope, Word cloud/Trends/Topics/Table, click word → matched feedback, Ask AI → agent run, activity trace, scope-fixed snapshot).
  - S04 `/reports` (insights list + pending-approval run drafts, serif report body with finding/hypothesis-unconfirmed/limitations/evidence E-xx chips, G2 bar approve/edit/reject/investigate-more, Generate actions, review-history rail). Old C4 summary preserved at `/reports/summary`.
  - S05 `/matrix` (2×2 by effort/impact mirroring BE §50, D02 drawer with AI estimate vs your decision + override reason + Reject/Save edits/Accept, drag-to-preview scores, Add-and-accept manual action, discard-changes guard).
  - S06 `/stakeholders` (department rail with counts, status filter, WHAT panel, open report/show in matrix, selected-proposed stays visible under Accepted filter).
- Shell: LISTEN/UNDERSTAND/ACT sidebar, header product switcher + create-product dialog + per-product last-screen restore, Current tasks button, English copy. Evidence Loom tokens in `globals.css` (Pine Ink/Field Paper/Chalk/Lichen/Pollen/Signal Blue; light theme forced). Root + middleware redirect now → `/importer`.
- New lib/hooks: `use-agent.ts`, `use-actions.ts`, `use-product.tsx`, `lib/departments.ts`, `lib/graph.ts`, `lib/matrix.ts`, extended `use-feedbacks` (import_id/analysis_state), types for agent/actions. Fixed pre-existing lint errors (react-hooks v6 rules) across old pages; added `app/global-error.tsx` (prod error page now shows the message).

## Evidence
- `pnpm typecheck` clean · `pnpm lint` 0 errors (11 pre-existing-style warnings) · `pnpm test` 39/39 (11 new: matrix/graph/departments) · `pnpm build` green (25 routes).
- Live E2E through Next proxy (cookies-e2e.txt, pm@thesis.local): upload demo CSV → preview → AI mapping proposal → **G1 approve → imported 5/5** → analysis receipt → run → **5/5 completed** → Ask AI agent run (a1da7b84) → **Gate #2 interrupt** (8 evidence, 4 options) → approve → insight 1711c9b9 approved → **generate actions 200** (7 actions; functions_skipped FINANCE) → **G3 PATCH**: override impact 9→6 (human_impact saved, agent value kept, priority recomputed 8.10→7.40), reject 1, explicit accept 1 → matrix regrouped (6 quick wins/1 strategic).
- Browser QA (agent-browser): signed in, screenshot each of S01–S06 rendering correctly in the Evidence Loom light theme; data live from BE.
- Found + fixed live: Next rewrite proxy killed LLM-slow routes at 30s with bare 500 → `experimental.proxyTimeout: 300_000` (decisions.md 2026-09-15); `useFeedbackDetail/useSimilarFeedbacks` fired with empty id (`/api/feedbacks//similar` double-slash wedge) → `enabled` guards; `Jan undefined` in scope line → shortDate guard.

## Not done / gaps
- No git commit created (workspace carries other agents' uncommitted work; per handoff protocol, owner commits).
- Drag-drop on Matrix sets draft scores only (numeric inputs are the accessible path); walkthroughs #2–#9 from the spec spot-checked, not exhaustively scripted.
- Supabase had a transient hang mid-session (~20:00–21:10) — all verification completed after recovery; unrelated to FE.
- `app/global-error.tsx` is new — if the user prefers the bare default page, delete it.

## Blocked / risks
- None open. proxyTimeout documented in decisions.md.

## Next steps
1. Owner: commit FE-12 files (frontend/**, docs/plans/FE-12*, docs/api-checklist.md, docs/decisions.md, FE-00-index, this handoff) — conventional commit e.g. `feat(fe): six-screen UI flow rebuild (FE-12)` + `Assisted-by: claude-code`.
2. Optional polish: Vietnamese/English copy audit of the Activity Sheet (still Vietnamese in places), old pages (`/dashboard`, `/feedbacks`, `/analysis`, `/clusters`, `/insights`) are off-nav but still routed.
3. Servers left running for immediate use: uvicorn :8000 (detached, logs backend/server.{out,err}.log) and `pnpm start` :3000 (logs frontend/server.{out,err}.log).
