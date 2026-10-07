# FE-13 — Shell: absolute top navbar + segmented left panel (Home/Chat)

> Owner request 2026-09-15: top navbar per Linear-style reference (logo, breadcrumb,
> search bar Ctrl K, functioning icons, profile; absolute over content) + left panel per
> Prope-style reference: 2 segmented tabs (Home, Chat), collapsed icon-only state,
> frozen bottom items (Settings, Contact us, What's new).
> Decisions confirmed via questions: stage nav inside Home tab; Chat = AI assistant via
> `POST /api/agent/runs`; search = global command palette; collapse = persisted toggle.

## Tasks

1. **T1** `panel-provider.tsx` — collapsed/mobileOpen state, localStorage.
2. **T2** `left-panel.tsx` — segmented control, Home tab (6 screens × LISTEN/UNDERSTAND/ACT),
   Chat tab (understand runs + New chat), frozen footer (Settings/Contact/What's new/avatar).
3. **T3** `top-navbar.tsx` — logo, breadcrumb (product ▸ stage ▸ screen), search trigger,
   Current tasks, What's new, Feedback, profile.
4. **T4** `command-palette.tsx` — Ctrl K: screen commands + reports + feedbacks, keyboard nav.
5. **T5** `settings-dialog.tsx` (PATCH `/api/products/{id}` via new `useUpdateProduct`) +
   `whats-new.tsx` popover.
6. **T6** `app/(app)/chat/page.tsx` — agent-run chat; Gate #2 drafts deep-link to Reports.
7. **T7** Rewrite `(app)/layout.tsx` — fixed panel + fixed navbar, providers kept.
8. **T8** Verify: typecheck/lint/vitest/build + browser QA (palette, collapse, tabs, chat).
9. **T9** Docs: api-checklist FE columns (`PATCH /api/products/{id}` now wired at Settings;
   agent runs also at `/chat`), FE-00-index, handoff.

## Invariants
- No BE changes, no new endpoints. Gate #2 stays explicit in Reports (chat deep-links).
- Evidence Loom tokens; panel width transition 240→56px; tooltips when collapsed.
