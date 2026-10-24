# Handoff: Inline investigation/HITL, reliable evidence guards and sentiment icons
- Date: 2026-10-24 01:47 local (Asia/Saigon)
- From: codex
- To: any
- Branch / worktree: codex/activity-center, existing live checkout
- Milestone: docs/plans/39-inline-investigation-review.md + owner browser sentiment comment
- Status: done

## Done
- Shared `components/ai/investigation-card.tsx` in Data Graph and Chat: readable progress, finding/evidence, inline approve/edit/reject/investigate-more; original draft prefilled, disabled controls while saving, errors preserve form.
- `investigation-actions.tsx`: generate and review ACT actions inline after finding approval; accept/reject and override recommendation/scores use existing guarded APIs. Reports retains result/CRUD views and links back to investigation; removed Gate #2 and generation controls there.
- Product-scoped tab-session persistence (`use-investigation-session`): Data Graph run/question/scope/view, Chat entries/draft/history. Opening Chat no longer clears thread. Report loading/error states distinguish pending fetch from empty data.
- Technical trace is opt-in, bounded to eight calls with scroll; default views hide UUIDs/tool JSON. Evidence summaries have translated keys and expandable full text.
- API: optional `POST /agent/runs/{id}/decision?background=true` → 202 processing, own daemon worker, duplicate protection and retryable failures; GET exposes processing status. Existing sync callers remain compatible. 3-second checkpoint read cache, invalidated on review.
- Planner detects non-adjacent repeated canonical tool inputs, stops on sufficient evidence, reserves synthesis budget; follow-up feedback enters planning; full bounded evidence survives reasoning. Fixed unbound exception in background crash cleanup.
- Live investigation exposed global cluster context: scope suggestions to own homogeneous clusters; inspect_cluster rejects foreign/no-member clusters and scopes metrics, hides global summaries/trends for mixed-product clusters.
- Failed/empty tool payloads no longer support findings; try unfiltered product samples once, otherwise produce limited finding without LLM. Sample-only absence claims become limited findings; sampled conclusions carry scope limitation/confidence cap.
- Shared SentimentIndicator: distinct colored icons for positive/negative/neutral/mixed and very-positive/very-negative aliases, localized hover/accessible labels, distinct unclassified fallback. Data Graph, feedback list/detail, analysis and Vault detail wired; classifier labels unchanged. Added root TooltipProvider after browser revealed missing provider in concurrent DataTable work.
- API checklist, dated decisions and active board synchronized. No commit, dependency install or auth bypass.

## Evidence
- FE `npm exec -- vitest run`: 14 files, 71 tests passed. Final `tsc --noEmit` and focused ESLint over changed investigation/sentiment files exited 0.
- BE `python -m pytest --noconftest tests/test_understand_planner_stops.py tests/test_understand_synthesizer_guard.py tests/test_investigation_review.py tests/test_act_grounding.py tests/test_phase28_contracts_unit.py -q --tb=short`: 48 passed (28.49s), approved outside sandbox.
- HTTP regression blocks continuation on an Event and confirms 202 returns before it finishes. Tests cover duplicate decision rejection, retry after failure, authenticated reviewer attribution and cache invalidation.
- Live browser on demo TEST2: create run, follow progress, inline approve; investigate-more + reject; final run edit/approve → completed. Navigating Reports → Data Graph restored run/question/table view. Reports no longer presents Gate #2.
- Final live run `6bcd6150-42b9-4910-a90a-af955befb495`: edited/approved as test report; evidence corresponds to actual sanitized demo feedback. No paid ACT generation during verification.
- Screenshots: tmp/inline-review-preview-2026-10-24.png and tmp/sentiment-icons-preview-2026-10-24.png (cropped only for QA presentation).

## Not done / gaps
- Full backend suite was attempted in sandbox, hit environment/socket errors and was stopped; no full-suite-pass claim. Focused HTTP tests initially hung in Windows socketpair before application entry (faulthandler verified); outside-sandbox run passed. One shell also reported OOM; avoid parallel heavy model/test processes on 8 GB machine.
- ACT accept/edit/reject wiring uses existing tested APIs and passes FE checks; not live-tested with newly generated paid actions this session.
- Background receipt is process-local, not a durable queue: a restart before checkpoint consumption may require resubmission. UI confirms only committed final state, and checkpoint retains gate/result.
- First trial report `236afe1e-ac63-4d50-a62c-c4c46616de61` exposed cluster-scope bug and was relabeled as a diagnostic through audited editor. Second run `95bdfef1-71cc-4069-86ae-955947820167` exposed sampled absence claim and was rejected with reason. Neither is quality evaluation evidence.

## Blocked / risks
- Extensive pre-existing and concurrent DataTable/Vault edits remain. Preserved them; Data Graph has overlapping changes from that work. Do not attribute the whole git diff to this session.
- Local services left running; do not launch duplicates. Last direct health check returned status=ok, db=ok, pii_mode=full.

## Next steps
- User can review in Data Graph or Chat, open diagnostics on demand, and inspect saved results in Reports.
- For further quality evaluation, use controlled synthetic cases and measure correctness separately from successful UI/graph execution.
