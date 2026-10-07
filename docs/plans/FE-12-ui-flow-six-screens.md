# FE-12 — Six-screen UI flow per design review 2026-09-15

> **Spec:** `docs/design/2026-09-15-ui-flow/01-user-flow-ascii.md` (authoritative interaction
> spec) + `02-visual-brief.md` (Evidence Loom visual direction, English UI copy).
> **Goal:** rebuild the authenticated FE into the six-screen LISTEN/UNDERSTAND/ACT journey and
> wire every screen to the existing BE surface (all endpoints already production per
> `docs/api-checklist.md`). No BE changes.

## Screens → BE mapping

| Screen | Route | BE used |
|---|---|---|
| S01 Importer + L01–L04 wizard | `/importer` | POST/GET `/api/imports`, preview, mapping proposal/decision (Gate #1), cancel |
| S02 Feedback Vault + L05 receipt + D01 detail | `/vault` | GET `/api/feedbacks?import_id=&analysis_state=`, similar, analysis preview/run/cancel/results |
| S03 Data Graph + Ask AI + activity trace | `/data-graph` | GET `/api/feedbacks` (client aggregation), POST/GET `/api/agent/runs` |
| S04 Reports + evidence + G2 | `/reports` | GET `/api/insights`, GET `/api/agent/runs/{id}` (pending_approval), POST decision (Gate #2), POST actions/generate |
| S05 Priority Matrix + D02 drawer | `/matrix` | GET `/api/insights/{id}/actions` (+ server matrix), PATCH `/api/actions/{id}` (Gate #3), POST add action |
| S06 Stakeholders | `/stakeholders` | same actions data, grouped by department (BusinessFunction) |
| Shell: product switcher + Current tasks | `(app)/layout.tsx` | GET/POST `/api/products`, existing ActivityProvider (imports + runs + agent runs) |

## Design tokens (brief, exact)

- Pine Ink `#14251D` — sidebar, primary, main text · Field Paper `#F1F3E9` — workspace bg
- Chalk `#FCFCF8` — cards/drawers · Lichen `#91A873` — selected nav/accepted · Pollen `#DBAC3B`
  — review badges · Signal Blue `#3F738B` — evidence links/selected data · red only errors
- Type: Segoe UI/Aptos sans UI; Palatino serif report titles + findings; mono for IDs/timestamps.
- Signature: small mono Signal-Blue evidence-ID chips (F-xx / E-xx / R-xx) connecting
  chart → report → action.

## Tasks (TDD where logic is pure)

1. **T1 tokens** — `globals.css` light theme to the palette above; layout font vars (serif
   heading `--font-heading`, mono `--font-mono`). Build green.
2. **T2 lib** — types: AgentRun, AgentStatusOut, ActionsListOut, ActionOut, BusinessFunction;
   hooks `use-agent.ts`, `use-actions.ts`; pure helpers `lib/departments.ts`, `lib/graph.ts`
   (topics/trends/word-cloud aggregation from feedback list), `lib/matrix.ts` (quadrant split
   ≥5 impact / ≤5 effort — mirrors BE §50). Vitest for pure helpers first (RED→GREEN).
3. **T3 shell** — `(app)/layout.tsx`: grouped sidebar (LISTEN: Importer, Feedback Vault;
   UNDERSTAND: Data Graph, Reports; ACT: Priority Matrix, Stakeholders), header product
   dropdown + create product, Current tasks button reusing ActivityProvider, account menu.
   English copy throughout the six screens.
4. **T4 Importer** — S01 grid (get started, 4 disabled source tiles, recent imports) + wizard
   steps File/Preview/Mapping/Result with G1 confirm; back preserves choices; progress
   resumable via Current tasks.
5. **T5 Vault** — files rail (imports), filters (date/topic/sentiment/analysis state), selection
   + pending/ready rules, analysis receipt (usage counts, no invented currency), progress
   poll, D01 drawer with similar feedback + referenced reports.
6. **T6 Data Graph** — dataset scope checkboxes + apply, tabs Word cloud/Trends/Topics/Table,
   click word → matching feedback, Ask AI → agent run → status trace → open report.
7. **T7 Reports** — list (insights + pending-approval runs as Needs review), report body
   (finding/hypothesis/limitations sections), evidence panel, G2 actions, Generate actions for
   approved.
8. **T8 Matrix** — report selector, 2×2 matrix (server matrix + local preview after score
   edit), D02 drawer (AI estimate vs your decision, override reason, Reject/Save edits/Accept),
   Add manual action.
9. **T9 Stakeholders** — department rail, action table by status, WHAT panel, links to report
   and matrix.
10. **T10 verify** — typecheck, eslint, vitest, `pnpm build`; live verify with BE: login →
    import CSV → Gate #1 → analyze → Ask AI → Gate #2 → generate → Gate #3 → Stakeholders.

## Invariants honored

- Three explicit gates: G1 mapping confirm, G2 finding approve, G3 accept action; Save edits ≠
  Accept; AI estimates stay visible after overrides.
- No raw feedback/PII anywhere; sanitized `feedback_text` only.
- No invented dollar amounts — usage shown as counts/tokens ("Estimate available before starting").
- Old pages (`/dashboard`, `/feedbacks`, `/analysis`, `/clusters`, `/insights`, `/reports` v1)
  keep their routes but leave the nav; six-screen nav replaces them.
