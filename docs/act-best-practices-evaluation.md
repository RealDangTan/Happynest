# ACT best-practices walkthrough — 2026-10-09

All examples are artificial VI/EN inputs. This checks generation, grounding and presentation; it does not establish product effectiveness or causal impact.

## Reproduce

From `backend/`, using the configured Supabase and `MODEL_ACT`:

```powershell
uv run python scripts/e2e_act_best_practices.py --live
```

`--live` explicitly enables paid model calls. Add `--keep` to retain the labelled demo product; otherwise the script removes only its own fixture rows. The script requires a relevant practice somewhere in each case's portfolio, valid snapshots, and investigation-only output when evidence is absent.

## Final observed run

Model: `openai/gpt-4o-mini`; prompt: `act-v2`; library: `act-practices-v1`; existing output cap: 8192 tokens. All four calls succeeded in strict mode after the schema fix, with no fallback warning in this run.

Permanent trace metadata confirms four successful calls at 10:11:24–10:12:11 UTC: prompt/completion tokens `3545/1085`, `3565/1116`, `3555/731`, `3494/547`; all `error=NULL`. No prompt or real feedback is reproduced here.

| Artificial case | Actions | Examples of canonical practice references | Result |
|---|---:|---|---|
| Citation quality | 3 | Microsoft HAX explanation; NIST risk treatment; Google SRE canary | PASS |
| Latency without p95 telemetry | 3 | Google SRE reliability/canary; Qualtrics follow-up | PASS |
| Difficulty correcting AI responses | 2 | Microsoft HAX correction; Google SRE rollback | PASS |
| Cost concern without evidence | 2 | FinOps unit economics; one explicit operational-guidance gap | PASS; both `investigate`, no invented evidence |

Ten actions persisted; nine include references and one explicitly declares a library gap. Every snapshot includes 2–3 distinct lenses, an alternative, tradeoffs, assumptions, success criteria and estimate basis. Links and source metadata come from the catalog, while the model supplies card IDs and their proposed application.

Retained demo product: `ACT best-practices demo e7c021eb` (`e7c021eb-e5df-42b5-bc7a-a08ecef55e5a`). Correction report: `38c5a4fb-19fe-40f4-a7e7-e73b1447e91c`. No real feedback was added or changed.

## Interpretation and limits

- Initial prompt-JSON trials omitted useful references by treating missing telemetry or cost data as a source gap. Field descriptions, source titles/sections, examples and a provider-compatible strict schema improved the final walkthrough.
- The script checks IDs, structure and an applicable practice in each portfolio. It cannot prove every application is appropriate or every alternative differs sufficiently. A reviewer must judge those semantics.
- Some generated success criteria are broad or propose numeric targets without a measured baseline. Treat these as suggestions requiring owner approval and baseline measurement, not observed results or guaranteed improvements.
- One estimate basis mentioned post-implementation support-ticket reduction that was absent from the input. This is an unsupported premise to correct at Gate #3; structural/source validation does not detect all semantic hallucinations.
- Sources support methods, not product-specific impact, ROI, confidence calibration or legal compliance. A larger labelled evaluation set is needed to measure recommendation quality.

## UI and regression evidence

Matrix drawer and Stakeholders detail panel were inspected in the local browser with synthetic records: internal evidence, multiple perspectives, reference links/sections, applicability limits and alternatives render in both places. Unit/UI tests cover invalid IDs, missing evidence, distinct lenses, legacy/manual null support, safe links and original-proposal notices after edits. DB integration covers JSONB persistence and preserving edited/accepted/rejected decisions.

Implementation details and final command outcomes are recorded in the [plan](plans/35-act-best-practices.md) and [session handoff](handoffs/2026-10-09-codex-act-best-practices.md).
