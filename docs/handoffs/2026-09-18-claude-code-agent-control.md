# Handoff: agent-control folder — schema + standalone HTML editor (phase 1, docs only)
- Date: 2026-09-18 (evening)
- From: claude-code
- To: any
- Branch / worktree: codex/activity-center (shared working tree — commit via pathspec, only docs/agent-control/*)
- Milestone: docs/agent-control (user-requested building-box control panel for the UNDERSTAND agent; plan saved at C:\Users\ADMIN\.commandcode\plans\agent-control-docs-folder.md)
- Status: done

## Done
- `docs/agent-control/` created:
  - `agent-schema.json` — machine-readable contract of the CURRENT understand agent, extracted from code: 7 nodes (with verbatim VI system prompts from nodes.py L168/L279/L339), 10 edges with branch conditions, 9 tools with params, 7 knobs (config.py L73-77 + nodes.py L38-40), output schemas (PlannerOut/EvaluateOut/InsightDraft), state fields, Gate #2 HITL block, 7 safety rules.
  - `README.md` + `schema-guide.md` — non-tech Vietnamese walkthrough (lifecycle, where LLM is called, how to use the folder).
  - `editor.html` — single-file standalone control panel (vanilla JS, no build, Happynest tokens: paper/ink/lichen/pollen/signal, Silkscreen eyebrows). Loads schema via relative fetch → file:// fallback to drag-drop/picker. Tabs: Tổng quan / Knobs / Tools / Prompts / Cấu trúc & JSON. VN-language client validation, flat-path diff, "Copy change-request" markdown generator, JSON download (`agent-schema.proposed.json`).
  - `change-requests/2026-09-18-template.md` — CR template.
- Scope per user comment: ONLY /docs touched; backend/frontend/API deferred to phase 2 (GET/PUT /api/agent-control/schema + pydantic validation — listed in plan, not implemented).

## Evidence
- `python -c json.load(agent-schema.json)` → OK, 7 nodes / 9 tools / 7 knobs.
- agent-browser against file://editor.html: intro fallback OK; file upload → all 7 nodes render with correct badges (LLM/GATE #2/CỐ ĐỊNH); knob edit 8→6 → chip "1 thay đổi", card shows "gốc: 8"; `buildChangeRequest()` emits correct markdown (UNDERSTAND_MAX_ITERATIONS 8 → 6); `validate()` returns VN error strings for broken schema (duplicate node, bad edge ref, empty prompt, non-numeric knob).

## Not done / gaps
- Phase 2 (backend validate/save API, pydantic models, tests) — intentionally deferred per user.
- Schema is a static contract: agent does NOT read it at runtime; sync discipline (code change ⇒ update agent-schema.json same commit) is manual and enforced only by convention + README §5.

## Blocked / risks
- file:// blocks fetch → editor relies on manual load on plain double-click (documented on intro screen). Served-over-http usage auto-loads.
- If understand_agent is refactored (e.g., agent series 17-20 replaces graph), agent-schema.json must be regenerated or it drifts from reality.

## Next steps
1. User edits schema in editor.html → Copy change-request → paste into change-requests/<date>-<slug>.md → ask Claude Code "áp dụng CR X".
2. Implementing agent: apply CR to code (nodes.py/config.py/graph.py) + update agent-schema.json in the SAME commit, keep the 7 safety_rules unless explicitly overridden (then log decisions.md).
3. When wanted: phase 2 = GET/PUT /api/agent-control/schema with pydantic validation + tests + api-checklist sync.
