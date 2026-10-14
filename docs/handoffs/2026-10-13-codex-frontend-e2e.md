# Handoff: Frontend E2E with 32 synthetic App Store reviews
- Date: 2026-10-13 10:24 Asia/Saigon
- From: codex
- To: any
- Branch / worktree: codex/activity-center, shared checkout
- Milestone: ad-hoc UI verification; active board has no open implementation plan
- Status: done (selected LISTEN → UNDERSTAND → ACT flow; defects remain)

## Done
- Owned UI verification only; preserved pre-existing/concurrent application changes. No application code edits or commits.
- Located the supplied fixtures at `docs/feedback-mock/`, not `docs/mock-data/`; selected `app-store-reviews.csv` (32 rows, 2026-08-02–2026-09-02).
- Seed logins rejected their documented defaults. User explicitly authorized creating a new account; registered through UI and created `HappyBot E2E · 13-10-2026` through onboarding. No existing accounts were reseeded.
- Product: `c4f14bbd-a23b-4a8e-8136-d535fb61def5`.
- G1: reviewed sanitized preview; changed `id → source_record_id`, `title → review_title`, `rating → app_store_rating`; retained `content → feedback_text`. Import `da7175b1-f519-4d02-85eb-8afc4f42dc3a`: 32 imported, 0 failed.
- Taxonomy: generated 25 proposed nodes, deselected one duplicate Technical Issues child, applied 24 nodes; taxonomy v2.
- Analysis `57fb7126-7dc1-41f2-8fe5-ba32c3c3b32f`: completed 32/32, 0 failures; all 32 embeddings have 1536 dimensions.
- Data Graph: checked Trends, Topics, and topic filtering; UI showed 3 login-related feedbacks. Real providers were used throughout.
- First investigation `31bc138e-6928-404b-aa2b-996990e95bfb`: tried Investigate more, then rejected insight `50208119-019b-402f-9718-80c23ace6704` with a reason because its evidence came from an unrelated existing cluster.
- Second investigation `4ee2ff86-78ab-453b-8a42-372e1b7771b1`: explicitly requested direct semantic retrieval rather than stored clusters; approved insight `b1d9cd7c-87f0-4d28-b206-b878cf995a4e` through G2. Its statement is conservative, confidence 0.50, and limitations remain visible.
- Approved evidence contains 10 retrieved feedback IDs; read-only DB assertions confirmed all 10 belong to the new product.
- ACT generated 2 actions: Engineering and Support. G3 accepted Engineering action `37f0a562-2883-48f1-b096-a60e832d171a`, changed impact 8 → 6, and saved the rationale; final priority 7.0. Support action remains proposed.
- Reopened the accepted action in Matrix; verified accepted status, impact 6, and source evidence in Stakeholders.

## Evidence
- Started native services: `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`; `pnpm dev --hostname 127.0.0.1`. Health: DB ok, PII full.
- Browser actions used Codex in-app browser via cua_repl; no API/script substitution for import, analysis, G1/G2/G3, or action generation.
- [16 real UI screenshots](../e2e-screenshots/2026-10-13/) cover preview, reviewed mapping, receipts, analysis, G2, G3, and Stakeholders.
- [verification.json](../e2e-screenshots/2026-10-13/verification.json): fresh ORM assertions exit 0, verifying import, classification, vectors, owned evidence, approval, impact override, and accepted action persistence.
- Decision memory: schema_mapping 1, taxonomy 24, insight 3 (investigate_more/reject/approve), action 1. All three run rows completed.
- Initial metadata probe had an unused incorrect model import; removed it and reran successfully. No application suite/typecheck/lint claim is made for this session.

## Not done / gaps
- No clustering rebuild: its UI warns that it deletes existing insights/clusters globally. Existing demo data was preserved.
- No application fixes, cleanup, commits, external tickets, or deployments. Test account/workspace and demo results retained for review.

## Blocked / risks
- Confirmed cluster evidence gap: `understand_agent/nodes.py::load_context` loads global clusters; `app/analytics/tools.py::inspect_cluster` does not use product_id to scope membership/metrics. First draft was rejected, never used for ACT.
- G2 navigation defect: pending interrupt payload is returned while status remains running; Data Graph/Chat test status == pending_approval, so the trace keeps saying Investigating and lacks Open report. Reports allowed the real decisions to proceed.
- Data Graph creation sends product_id/question only, despite the displayed fixed import scope. This demo used one import in one new product, so verified approved evidence stayed within that scope.
- GPT structured JSON schemas repeatedly returned 400; prompt-JSON fallback worked. Aggregate calls in the second investigation returned empty objects repeatedly; conservative final insight used direct semantic evidence.
- Concurrent frontend edits during this session caused reloads and lost transient Data Graph state; backend runs persisted and were recovered through Reports/Chat history.
- See the 2026-10-13 decision entry; this selected successful flow does not establish complete module acceptance.

## Next steps
1. Verify cluster context and tool queries respect the selected product/import with regression coverage.
2. Reconcile pending interrupt payload with the frontend review-ready state; persist/forward import scope for investigations.
3. Investigate empty aggregate tool responses and the UNDERSTAND strict-schema fallback overhead; retain the explicit uncertainty in reports.
4. Continue review at `/stakeholders?report=b1d9cd7c-87f0-4d28-b206-b878cf995a4e` in the existing signed-in test tab.
