# Navbar Activity Center & Budgeted Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the `executing-plans` skill to implement this plan task-by-task INLINE (no subagents in this repo — limited LLM API credit).

**Goal:** Make CSV import and feedback analysis explicit, resumable, scoped, and visible from a navbar Activity Sheet without adding an `/imports` page.

**Architecture:** Upload/profile is deterministic and free; mapping and analysis are separate paid gates. Backend jobs persist lifecycle state, while a shared frontend activity provider drives the navbar Sheet now and a floating mascot later.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic/PostgreSQL, Next.js 16, TanStack Query, shadcn/ui radix-vega, Vitest, pytest.

**Spec:** Owner-approved plan in the 2026-08-30 Codex task (“Navbar Activity Center & Budgeted Import Analysis”).

## Global Constraints

- No Docker and no new dependency.
- Raw feedback never crosses the sanitize boundary; only sanitized samples/text enter prompts or API previews.
- Analysis run maximum is 100 feedback; true batch chunk size is 10.
- No LLM work starts automatically after upload or import.
- No `/imports` page; the navbar Activity Sheet is the only import queue entry point.
- Implement inline with TDD and update `docs/api-checklist.md` in the same change as API contracts.

---

### Task 1: Persist controlled import and analysis lifecycle

- [x] Add failing model/schema/migration contract tests for import profile states, scoped runs, cancellation metadata, and migration `0015` after existing `0014`.
- [x] Implement enum/column/schema/config changes and run the focused tests green.

### Task 2: Split upload, paid mapping, review, and cancel APIs

- [x] Add failing route/service tests proving upload performs no LLM call, previews contain sanitized samples, mapping is explicit/idempotent, list filters work, and cancel safely removes raw storage.
- [x] Implement the split lifecycle, polling responses, structured conflicts, and feedback `import_id`/`analysis_state` filters.
- [x] Run focused import tests green.

### Task 3: Add scoped and budgeted analysis jobs

- [x] Add failing tests for preview/create scope validation, cap 100, count confirmation, batch chunks, failure release, and cooperative cancel.
- [x] Implement selected and true-batch runners, run listing/progress/cancel, and deterministic cost preview.
- [x] Run focused runner/API tests green.

### Task 4: Build shared Activity Center data/UI

- [x] Add shadcn `checkbox` and `toggle-group` only.
- [x] Add failing Vitest contracts for activity derivation, query-param navigation, upload handoff, and cost preview helpers.
- [x] Implement ActivityProvider, navbar capsule, segmented Sheet queue/detail, resumable mapping review, import polling, selection/batch controls, cost receipt, and run cancellation.
- [x] Remove the unsafe global analysis trigger while preserving results monitoring.
- [x] Run frontend tests, typecheck, and visual/browser QA.

### Task 5: Documentation and final verification

- [x] Sync API checklist, decisions, environment example, root/FE indexes, and handoff evidence.
- [x] Run backend unit/integration tests, Alembic upgrade, frontend tests/typecheck/lint/build, and verify no `/imports` route exists.
