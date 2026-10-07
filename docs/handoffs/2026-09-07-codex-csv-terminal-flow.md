# Handoff: Existing terminal extended through CSV and all three gates
- Date: 2026-09-07 01:12 local
- From: codex
- To: any
- Branch / worktree: codex/activity-center / existing checkout (owner requested adapting in-place)
- Milestone: docs/plans/29-interactive-agent-terminal.md, September 7 extension
- Status: done

## Done
- Extended existing `backend/scripts/agent_terminal.py` with `--flow`; legacy default preserved. No duplicate be_terminal.py entry point.
- Added HTTP adapter + sequential wizard; CSV/profile, explicit mapping, all Gate #1 choices, scoped analysis receipts/progress/results/embedding status/similar, UNDERSTAND with all Gate #2 choices, ACT/Gate #3 edits/manual actions, global reports and scoped impact.
- One-command Windows launcher `scripts/start-be-terminal.ps1`: read-only preflight, reuse healthy BE or start independent uvicorn without reload, direct keyboard input, no second NLP runtime in CLI.
- Persist only session UUIDs under ignored storage; resume by ID, explicit cancel, no automatic mutation replay. Human reviewer comes from login.
- Added authenticated product-scoped impact endpoint; legacy service signature remains compatible. Added `FeedbackOut.has_embedding` without exposing vectors.
- Sanitized human question/decision/action text before checkpoint/decision memory; removed raw invalid-date values and exception payloads from import reports.
- Updated README, API checklist, existing plan/index and decisions. Preserved all pre-existing unrelated FE edits.

## Evidence
- Initial unit RED reproduced missing wizard/scope/readiness plus unsanitized graph question; later RED reproduced raw date error echo.
- Full default backend suite: `79 passed, 75 deselected`; four existing sklearn FutureWarnings.
- Final focused: `python -m pytest tests/test_terminal_flow_unit.py tests/test_agent_terminal_unit.py -q`: `25 passed` (includes two tests added after full suite).
- `python -m pytest tests/test_terminal_flow_integration.py -m integration -q`: `1 passed in 148.75s` — actual API, PG, graph/checkpoints and all three persisted gates, only providers mocked; includes partial CSV failure and impact age/scope/idempotency checks.
- Read-only cleanup verification: zero `terminal-test-*`/`terminal-other-*` products and zero synthetic terminal test users remain.
- Launcher `-CheckOnly` succeeded; PowerShell parser reported no errors. Actual first launch reached `Email đăng nhập >`, `/quit` returned exit 0. Second launch reused BE and again accepted `/quit` with exit 0.
- `agent_terminal.py --help` works without NLP initialization; git diff whitespace check clean.

## Not done / gaps
- Did not submit owner CSV/questions or spend real provider credits. Real model quality/provider fallback remains for owner to evaluate interactively.
- No commit/merge created; workspace already contained related uncommitted terminal work plus unrelated FE files.
- Summary/KPI APIs remain global and are labeled accordingly; impact window is real (default 7 days).

## Running service / next steps
1. BE started by launcher is on `127.0.0.1:8000`, launcher PID 11792 (Python worker observed as 7712); process IDs may become stale.
2. Owner runs `.\scripts\start-be-terminal.ps1` from repo root, logs in and supplies CSV. Wizard defaults to asking for every paid action and gate.
3. To stop this BE only when no jobs remain: verify PID ownership, then `taskkill /PID 11792 /T /F` (Windows venv Python uses a launcher plus worker).
4. Existing terminal-only direct-DB mode is still available without `--flow`; prefer new HTTP mode for pre-FE product validation.
