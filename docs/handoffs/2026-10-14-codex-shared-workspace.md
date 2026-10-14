# Handoff: Shared authenticated workspace
- Date: 2026-10-14 22:52 Asia/Saigon
- From: codex
- To: any
- Branch / worktree: codex/activity-center, existing shared checkout
- Milestone: docs/plans/37-shared-workspace.md
- Status: done (uncommitted)

## Done
- All authenticated accounts share products/data and all CRUD/HITL actions.
- User response is `{id, email}`; JWT uses sub/iat/exp. Cookie/Bearer authenticates identity; reviewer_id records decisions.
- Product/import filters select business data. PII boundary, cost confirmation, HITL gates and delete confirmations remain.
- Database schema is revision 0019; existing business data retained.
- Fixed delete_product NameError by assigning the loaded product and narrowed wizardImport.data for TypeScript compilation.
- Updated seed/terminal helpers, account fixtures and current frontend controls.
- Test fixtures use dedicated test-primary/test-secondary emails, preserving demo passwords.
- No commits, staging/reset, dependencies, Docker, subagents or unrelated cleanup.

## Evidence
- `uv run pytest tests/test_shared_access.py -q`: 7 passed.
- `uv run pytest -q`: 124 passed, 107 deselected, 4 existing sklearn FutureWarnings, exit 0.
- `uv run pytest -m integration tests/test_product_access.py -q`: 1 passed; two accounts register/login/list/read/schema/update/name-conflict/delete the same workspace; test data cleaned.
- Alembic SQL generated successfully; database current = 0019 (head).
- `pnpm test`: 50 passed / 11 files. Typecheck and production build: exit 0, 32 routes.
- Scoped FE lint: exit 0. Runtime OpenAPI UserOut exposes id/email.

## Not done / gaps
- Full integration suite and browser visual acceptance were not run.
- Full lint retains the Importer effect error and 2 activity-provider warnings.

## Blocked / risks
- Existing unrelated staged/unstaged work remains in the shared checkout.

## Next steps
1. Review scoped changes and commit with Assisted-by: codex if requested.
2. Address the existing Importer effect error as a separate UI task.
3. Other environments: apply migrations and restart the updated backend.
