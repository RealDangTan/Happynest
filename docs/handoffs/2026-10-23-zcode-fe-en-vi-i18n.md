# Handoff: FE EN/VI i18n layer — dead language switch is now live
- Date: 2026-10-23 ~23:30 local
- From: zcode
- To: any
- Branch / worktree: codex/activity-center (SHARED working tree — see risks)
- Milestone: Delivery phase — frontend polish (no plan file; ad-hoc user request "làm cho chức năng dịch en/vi hoạt động")
- Status: done

## Done
- `frontend/lib/i18n.ts` (new): zero-dependency i18n core. Module store + `useSyncExternalStore` (hydration-safe: SSR/hydration always "vi", localStorage read re-checks after mount), `useAppLang()`, `useT()`, `setAppLang()` (writes localStorage `happynest.lang` + `document.documentElement.lang`). Dictionary: `vi` is source of truth, `en: Dictionary` type-checked for structural completeness; interpolated entries are functions (`deleteTitle(name)`, `toastDeleted(total)`).
- Deleted `frontend/hooks/use-language.ts` (old per-component useState copy — toggles didn't sync in-session); consumers migrated to the shared store.
- `lib/navigation.ts`: STAGES/UTILITY_SCREENS/findStage now carry stable keys (`NavItemKey`/`UtilityKey`), display text resolved via `t.nav.*` by consumers.
- `lib/labels.ts`: `SEVERITY_LABEL`/`SENTIMENT_LABEL` → `Record<AppLang, …>`; `priorityLabel(p, lang)`.
- `lib/auth-errors.ts`: `mapAuthError(error, lang)`; `lib/google-auth.ts`: `googleErrorAlert(code, lang)`; `useGoogleErrorParam` rewritten with `useSyncExternalStore` (fixes react-hooks/set-state-in-effect lint error).
- Translated + reactive: left-panel, top-navbar (product dropdown + 3 dialogs + toasts), profile-panel, command-palette (labels/groups re-filter per language), settings page, help page (full copy incl. FAQs), login + register (client validation stored as discriminant, translated at render) + LangToggle added to auth screens.
- `components/lang-toggle.tsx` (new): shared VI/EN toggle used by profile popover, settings, auth screens.
- `components/providers.tsx`: `HtmlLangSync` keeps `<html lang>` in sync; `app/layout.tsx` default `lang="en"` → `"vi"` (mismatch fix).
- Data pages consume lang-aware labels: analysis, feedbacks list + detail, clusters (priorityLabel), reports/summary SentimentBars, severity-bars (aria label via `t.charts.*`).
- help FAQ #3 (workspace sharing) updated to match the 2026-10-22 per-account isolation contract (old text still claimed shared workspaces).

## Evidence
- `npx tsc --noEmit` → only pre-existing error left is `lib/taxonomy.test.ts` (parallel session's in-flight name_vi work; my files: 0 errors).
- `npx vitest run lib/labels.test.ts lib/auth-errors.test.ts` → 15/15 pass. Full suite: 55/57, only taxonomy.test.ts (2) fails — not mine.
- `npx eslint` over all 22 touched files → clean.
- Browser E2E (in-app browser vs `next dev -p 3457`): SSR renders VI + `lang="vi"`; profile popover EN click → sidebar/breadcrumb/popover switch to English instantly (no reload); `localStorage.happynest.lang="en"`, `html lang="en"`; EN persists after reload; /settings renders English headings. Screenshot verified, no layout breakage.

## Not done / gaps
- Page BODIES of the 6-screen journey (importer, vault, taxonomy, matrix, reports, stakeholders, dashboard, onboarding, contact, profile, workspace settings, chat dock, activity, whats-new) remain hardcoded VI/EN mix — dictionary + mechanism are in place; translating them is mechanical follow-up.
- `docs/api-checklist.md` untouched (no API change).

## Blocked / risks
- **Shared working tree violation in progress:** a parallel session (codex, Google OAuth + taxonomy name_vi work) edited login/register/lib/taxonomy UNDER this session mid-run; I re-read files before each edit and layered on top of their uncommitted state. Handoff rule 4 says use worktrees — flag for the owner.
- During browser verification an external actor (user or parallel session) repeatedly interacted with the same visible in-app browser pane (opened Chat dock, toggled language). Not a code bug — no code path writes `happynest.lang` besides `setAppLang`.

## Next steps
1. Commit this work (my files only) with `Assisted-by: zcode` — coordinate with the parallel session's uncommitted google-auth/taxonomy changes sitting in the same tree.
2. Translate remaining page bodies incrementally: add a namespace per page to `lib/i18n.ts` (`Dictionary` type enforces EN completeness), swap literals for `t.<ns>.*`.
3. If a page needs shared vocab (e.g. status words), prefer extending `lib/labels.ts` pattern (`Record<AppLang, …>`) over one-off ternaries.
4. Kill the smoke dev server when done: it runs as `npx next dev -p 3457` in `frontend/`.
