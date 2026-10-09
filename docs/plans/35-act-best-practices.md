# ACT best-practices implementation plan

> Execute inline with `executing-plans`; no subagents. Owner approved in chat on 2026-10-09.

**Goal:** ground ACT proposals in reviewed evidence and curated industry guidance, with multiple perspectives, alternatives and measurable validation.

**Architecture:** one existing `chat_structured` call sees 18 concise practice cards plus up to 10 product-scoped evidence statements. Backend validates IDs and persists canonical source metadata in an immutable JSONB snapshot. A shared component presents the snapshot in Matrix and Stakeholders.

**Stack:** existing Python 3.12/FastAPI/Pydantic/SQLAlchemy/Alembic and Next.js/shadcn; no added dependencies.

## Constraints

- No Docker, subagents, raw feedback, runtime web search or added LLM calls beyond the existing structured-output fallback chain.
- Keep `MODEL_ACT`, the weighted priority formula, 8 business functions and Gate #3.
- Sources justify an approach; they do not prove product impact or calibrated confidence.
- Preserve user changes and unrelated working-tree changes.

## Tasks

- [x] Write and observe failing grounding and UI tests before implementation.
- [x] Curate 18 cards: Product 3, Discovery 3, Engineering 3, UX 3, Risk 2, Customer Success 2, Finance 2. Each stores principle, applicability, limitations, source section/URL and review date.
- [x] Add nullable `actions.decision_support` with migration 0017; legacy/manual actions remain null.
- [x] Implement `act-v2`, evidence resolution, source/evidence ID validation and proposal validation before mutation. Missing evidence permits only investigation; unmatched guidance requires an explicit source gap.
- [x] Snapshot the original recommendation/rationale, sources, perspectives, alternative, tradeoff, assumptions, success criteria and estimate basis. Keep edited/accepted/rejected actions on regeneration.
- [x] Add shared decision analysis to `/matrix` and `/stakeholders`, with safe links, empty state and original-proposal notice after text edits.
- [x] Update API checklist and dated decision entry.
- [x] Verify DB integration, production build and synthetic walkthrough; record evidence in handoff.

## Public contract

Existing action responses gain nullable `decision_support`. Generation still returns `{actions_created, functions_skipped, generation_error}`. No new routes or auth changes. Model output contains only source/evidence IDs; reference metadata is supplied by the server. Human updates cannot replace the snapshot.

## Verification

- Backend unit suite; integration `test_act_agent.py` and `test_decision_kpis.py` against Supabase with mocked LLM.
- Frontend Vitest, TypeScript, ESLint for touched files and production build.
- Synthetic VI/EN cases: answer quality, latency, correction friction and missing evidence. Review applicability and the finding/hypothesis distinction; do not claim quantitative effectiveness from these examples.
- Migration precedes backend/frontend deployment. For application rollback retain the JSONB column and historical snapshots.

## Live verification findings

- Initial prompt-JSON output confused missing internal data with an external source gap. Added field descriptions, source titles/sections and examples distinguishing these cases.
- The provider rejected the original ACT schema because strict object requirements were missing. A regression test reproduced the failure; ACT schemas now forbid additional properties and require explicit nullable fields in the generated JSON schema while preserving Python defaults.
- Final synthetic walkthrough: all 4 cases passed, 10 actions created, 9 with canonical references and 1 with an explicit library gap. Missing-evidence actions were investigation only. See [evaluation](../act-best-practices-evaluation.md).
- Final verification: 107 backend unit tests, 10 ACT/KPI integration tests and 49 frontend tests passed. TypeScript, touched-file ESLint and production build passed. Migration 0017 applied to the configured development database. Matrix/Stakeholders checked in browser; no production deployment or Git integration requested.
