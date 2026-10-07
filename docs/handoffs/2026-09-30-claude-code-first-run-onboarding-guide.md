# Handoff: First-run onboarding guide + 2 importer bug fixes (FE)
- Date: 2026-09-30 11:50 local
- From: claude-code
- To: any
- Branch / worktree: codex/activity-center (main working tree, uncommitted)
- Milestone: ad-hoc FE task (onboarding for first-time users); plan at ~/.commandcode/plans/first-run-onboarding-guide.md
- Status: done (uncommitted)

## Done
- NEW `frontend/components/onboarding/first-run-guide.tsx` — `FirstRunGuide({ onStartImport? })`: real-data setup checklist (product created → CSV imported → first insight exists). Shown on `/importer` (default landing) and dashboard while workspace has no insights; dismiss persists to localStorage key `happynest.first-run-guide.dismissed`. Reuses `useProduct`/`useImports`/`useInsights` — no backend change, no api-checklist update needed.
- Mounted in `frontend/app/(app)/importer/page.tsx` (guide's Import CSV button opens the wizard via `setPhase("file")`) and `frontend/app/(app)/dashboard/page.tsx`.
- FIX 1 (pre-existing bug exposed by onboarding): importer wizard never opened for fresh imports — render condition required `importId` which is only set after upload. Now: `effectivePhase !== "idle" && (effectivePhase === "file" || importId)`.
- FIX 2 (pre-existing bug exposed by onboarding): `useGetMapping` cached the 409 (mapping still generating) and never retried → mapping table stayed empty, confirm button disabled forever. Now retries 409 up to 30× at 1s (`frontend/hooks/use-imports.ts`).

## Evidence
- `npm run typecheck` — pass; `npm test` — 39/39 pass; eslint clean on all 4 touched files.
- Full E2E in agent-browser (headless): registered `onboard-test@happynest.dev` → redirected `/importer` → guide "0/3" → created product "Demo AI" via dialog → "1/3" → uploaded 4-row CSV → preview → mapping proposal (1 LLM call) → G1 confirm → "Import completed 4 imported / 0 failed" → guide "2/3" with strikethrough on steps 1–2 → dismiss → reload → guide stays hidden.
- Screenshot verified visually (guide tokens match shell: lichen/signal, mono eyebrows).
- Note: two PRE-EXISTING eslint errors remain in files I did not touch: `app/(app)/reports/page.tsx:352` and `app/(app)/vault/page.tsx:154` (react-hooks/set-state-in-effect). They make repo-wide `npm run lint` exit 1.

## Not done / gaps
- Step 3 ("Run your first analysis" → insight exists → guide auto-hides with 3/3 footer) not E2E-tested — requires a full UNDERSTAND agent LLM run; credit intentionally not spent. Condition is a simple `insights.length > 0`.
- All work is UNCOMMITTED on codex/activity-center (branch had lots of prior uncommitted work — did not commit to avoid mixing).

## Next steps
1. Commit FE onboarding + the two importer fixes (separate commit(s), `Assisted-by: claude-code`).
2. Optionally fix the two pre-existing set-state-in-effect lint errors (reports/vault pages).
3. E2E test step 3 once an analysis run is affordable: register → import → run analysis → guide should hit 3/3 then disappear on next visit.
