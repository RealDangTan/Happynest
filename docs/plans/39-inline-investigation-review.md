# Inline investigation review implementation plan

> **For agentic workers:** Use executing-plans INLINE; no subagents.

**Goal:** Ask, follow progress and review a finding in one investigation surface; Reports displays results.
**Architecture:** Reuse one InvestigationCard in Data Graph and Chat. Preserve product-scoped session state, expose short progress with optional diagnostics, and acknowledge background decisions before the graph resumes. Keep synchronous API compatibility for terminal callers.
**Tech Stack:** Existing Next.js/shadcn/TanStack Query, FastAPI, LangGraph/Postgres; no dependencies.
**Spec:** Owner request 2026-10-24 (four UX problems in this chat).

## Constraints
- Preserve current uncommitted checkout; it contains the live implementation under review. No parallel agents.
- PII boundary, per-account product guards and all human approval choices remain binding.
- Never report approval saved until server confirms final outcome. Background acceptance means processing only.
- Preserve graph checkpoint as source of truth; cache must expire and invalidate on decisions.

## Tasks
- [x] 1. Regression tests for repeated analytics steps, evidence retention, follow-up handling and review failure recovery.
- [x] 2. Fix planner guards, budget reservation and background exception binding; retain bounded evidence for reasoning.
- [x] 3. Add optional background decision receipt, duplicate protection, processing/error status and checkpoint cache; HTTP test confirms receipt precedes continuation completion.
- [x] 4. Shared InvestigationCard in Chat/Data Graph, product-scoped session persistence, inline Gate #2 and ACT review, readable evidence and optional diagnostics.
- [x] 5. Reports becomes result view; update API checklist/decisions. Additional owner browser comment: sentiment icons across related views.
- [x] 6. Frontend: 71 tests, typecheck and focused lint pass. Backend: 48 focused tests pass outside Windows sandbox. Live edit/approve, investigate-more, reject and navigation recovery verified. See handoff for full-suite limitations and diagnostic runs.

## Validation commands
`backend/.venv/Scripts/python.exe -m pytest tests/test_understand_planner_stops.py tests/test_understand_synthesizer_guard.py tests/test_investigation_review.py -q`

`npm exec -- vitest run`; `npm exec -- tsc --noEmit`; focused `npm exec -- eslint`.

Browser: start/reopen investigation; draft and evidence render without default IDs; send review once with immediate progress; graph completes and report link opens results; reload/return keeps current session.
