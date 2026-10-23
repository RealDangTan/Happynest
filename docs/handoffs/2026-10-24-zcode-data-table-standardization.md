# Handoff: DataTable standardization — TanStack Table v9 kit + server-side q/sort
- Date: 2026-10-24 ~01:50 local
- From: zcode
- To: any
- Branch / worktree: codex/activity-center (SHARED working tree — parallel sessions still active, see risks)
- Milestone: ad-hoc user request "cải thiện table: sorting, column toggle, filter, search — UI gọn"
- Status: done

## Done
- **Research**: NN/g Data Tables, Pencil & Paper Enterprise Tables, SetProduct/Coyle guides → distilled: search/sort/filter must run on the WHOLE dataset, sticky header, compact icon-driven toolbar, numbered pagination + page size, select-all w/ indeterminate, skeleton/empty/filter-reset states.
- **Audit bugs found & fixed**: vault search filtered only current page (misleading totals); vault header had no select-all; data-graph table tab silently `slice(0,50)`; feedbacks row `cursor-pointer` but only first cell was a link; pagination everywhere was Trước/Sau only.
- **Kit** `frontend/components/data-table/`: `DataTable` (sticky opt, skeleton, empty, row click, rowClassName), `DataTableColumnHeader` (menu asc/desc/clear/hide + aria-sort), `DataTableToolbar` (search + faceted + icon column-toggle + reset-when-filtered), `DataTableFacetedFilter` (multi-select + facet counts + badge), `DataTablePagination` ("a–b trên n", page-size, first/prev/numbers/next/last). Hooks `use-debounced-value`, `use-stored-state`; `lib/table-sorts.ts` (semantic severity rank, server-sort mapping, multiSelect filterFn). i18n `table` namespace vi/en.
- **TanStack v9** via `useLegacyTable` (official v8-compat layer; v9 `useTable` features API undocumented — too risky pre-deadline). Package installed MANUALLY from tarballs into node_modules (+ @tanstack/table-core, react-store, store, use-sync-external-store) because repo has NO lockfile and `npm install` re-resolves the whole tree → hang + npm 11 null bug. `package.json` records `"@tanstack/react-table": "^9.3.1"`. See decisions.md 2026-10-24.
- **Backend** `GET /api/feedbacks`: +`q` (ILIKE on feedback_text+source, whole dataset), +`sort` whitelist `newest|oldest|±source|±severity|±confidence` (severity CASE low<medium<high<critical, confidence cast float, 422 on unknown), `severity`/`sentiment` now accept comma-list (faceted multi-select). `docs/api-checklist.md` row updated same change.
- **Pages rewired**: `/feedbacks` (URL-param manual mode: q/sort/facets/columns/page-size all in URL, row=link); `/vault` (server q+sort, select-all checkbox, new Occurred+Severity sortable columns, kept ALL existing flows: receipt, drawer, bulk delete, imports sidebar, re-enrich banner); `/analysis` results (fetch-all ≤100 + client sort/severity facet/search — removed server paging); `/data-graph` Table tab (full dataset client table, was hidden 50-cap); `/stakeholders` actions (priority sort default desc, search kept, selected-row highlight).
- Left AS-IS deliberately: reports/summary top-categories (2-col aggregate), importer wizard tables, activity-sheet picker (not data-browsing tables).

## Evidence
- FE: `npx tsc --noEmit` → 0 errors. `npx eslint` over all touched files → clean. `npx vitest run` → 71/71. `npx next build` → success.
- BE: `uv run pytest -q` → 174 passed; `uv run pytest -m integration tests/test_feedback_list_filters.py` → 4 passed (2 new: q case-insensitive text+source; sort semantic severity + confidence + 422 bogus). Note: one flaky OOM in tsc and a pytest segfault occurred under memory pressure (8GB box, dev server + parallel session) — both passed on re-run; q-test order assertion fixed with `sorted()` (same-timestamp rows tie-break on random UUID).
- Runtime: logged in via proxy on the parallel session's dev server :3000; all 5 pages HTTP 200 with SSR markers verified (toolbar search "Tìm trong bảng", column-toggle aria-label, faceted filter, aria-sort, select-all aria-label, Occurred/Severity headers); `?sort=severity`/`?q=…&sort=oldest` → 200, `?sort=bogus` → 422. IAB webview could not attach ("browser guest not ready") so no screenshots — SSR + build coverage only.
- Parallel-session interactions: they fixed `Float` cast import in my `_FEEDBACK_SORTS`, swapped analysis sentiment cell to their `SentimentIndicator`, added root TooltipProvider after a live runtime error in my toolbar — all kept.

## Not done / gaps
- Column toggle on vault is per-session (internal state, not persisted); feedbacks persists to `feedbacks.columns.v2` (old key `feedbacks.columns` now unused).
- Vault selection pending/ready counts still computed against current-page rows only (pre-existing behavior, kept).
- FE unit tests for the kit itself not written (no existing component-test infra for these patterns; vitest suite covers lib only).
- Visual screenshot pass blocked by IAB; recommend a quick manual look at /feedbacks + /vault.

## Blocked / risks
- Shared working tree: many uncommitted changes from parallel sessions (sentiment icons, investigation work, google auth…). My commit stages ONLY my file list. Any session running `npm ci/install` will wipe the manually staged tanstack node_modules dirs — re-stage from tarballs or fix npm.
- Dev server 3457 (old smoke) is dead; parallel session runs :3000.

## Next steps
1. Review commit (my files only) — see git trail.
2. Kill leftover `page_*.html`, `dev-3458.*.log` temp files in frontend/ if present.
3. Optional follow-up: persist vault column visibility; unify remaining tables (clusters page list) onto the kit when touched next.
