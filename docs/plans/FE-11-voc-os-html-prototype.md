# VoC OS Standalone HTML Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the `executing-plans` skill to implement this plan task-by-task INLINE (no subagents in this repo — limited LLM API credit). Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build one self-contained HTML file that demonstrates the complete product-scoped Happynest journey from feedback import to evidence-backed action and impact measurement.

**Architecture:** The artifact lives under `frontend/public/` and uses only semantic HTML, inline CSS, inline SVG, and vanilla JavaScript. A single state controller switches seven product views and advances a six-step guided mission; a persistent evidence rail makes provenance visible across LISTEN, UNDERSTAND, and ACT without calling real APIs.

**Tech Stack:** HTML5, CSS custom properties, inline SVG, vanilla JavaScript, Vitest static-contract test, in-app browser QA.

**Spec:** `docs/VoC Agent Operating System — Technical Implementation Plan.md` §§4–75, `docs/api-checklist.md`, `docs/plans/28-navbar-activity-budgeted-analysis.md`, `docs/ai-agent-success-story.md`.

## Global Constraints

- Create exactly one runnable UI artifact: `frontend/public/happynest-voc-os.html`; it must have no runtime dependency or build step.
- Use only fictional, sanitized feedback. Every displayed verbatim must contain placeholders such as `<ORG>` and never raw PII.
- Show the three non-negotiable human gates: schema meaning, insight meaning, and final priority.
- Keep findings and hypotheses visually distinct; show evidence IDs and field-coverage limitations.
- No API calls, backend changes, endpoint changes, or new package dependencies.
- Support desktop and mobile, visible keyboard focus, semantic labels, and `prefers-reduced-motion`.

## Design Direction — Evidence Loom

- **Subject / audience / job:** Happynest VoC OS for PM and operations teams; the page's single job is to let a thesis reviewer experience one complete customer-voice-to-product-action decision in under ten minutes.
- **Palette:** Pine Ink `#14251D`, Field Paper `#F1F3E9`, Chalk `#FCFCF8`, Lichen `#91A873`, Pollen `#DBAC3B`, Signal Blue `#3F738B`; risk coral is reserved for destructive states.
- **Type:** local editorial serif (`Iowan Old Style`/`Palatino`) for findings, humanist UI sans (`Aptos`/`Segoe UI`) for controls, and condensed utility (`Bahnschrift`/`Arial Narrow`) for evidence IDs and system facts.
- **Layout:** deep product rail + quiet working canvas + collapsible evidence ledger. On narrow screens the rail becomes a compact stage strip and the ledger moves below the active workspace.
- **Signature:** an inline SVG “evidence loom” braids source signals into a single decision thread; its highlighted segment follows the active stage and every insight/action cites the same evidence IDs.

```text
┌──────── product rail ────────┬──────────── active workspace ────────────┬── evidence ledger ──┐
│ Happynest / product          │ LISTEN ─── UNDERSTAND ─── ACT             │ EV-12 trend         │
│ Overview                     │                                             │ EV-14 segment       │
│ Sources / Schema / Feedback  │ guided task, data, gate, next action        │ EV-18 verbatims     │
│ Understand / Act / Reports   │                                             │ coverage + limits   │
└──────────────────────────────┴─────────────────────────────────────────────┴────────────────────┘
```

**Self-critique before build:** A full dark dashboard would repeat the landing page and reduce analytical legibility. The revision keeps brand-dark chrome only in the navigation and uses a paper-like work surface. The loom is not decorative: it carries stage state, evidence provenance, and gate completion; all other decoration is removed.

---

### Task 1: Lock the standalone artifact contract

**Files:**
- Create: `frontend/lib/voc-prototype.test.ts`
- Create later: `frontend/public/happynest-voc-os.html`

**Interfaces:**
- Consumes: the path `public/happynest-voc-os.html`.
- Produces: static assertions for view IDs, gate IDs, accessibility, privacy, and responsive/reduced-motion contracts.

- [x] **Step 1: Write the failing contract test**

```ts
const requiredViews = ["overview", "sources", "schema", "feedback", "understand", "act", "reports"];
const requiredGates = ["gate-listen", "gate-understand", "gate-act"];
expect(html).toContain('meta name="viewport"');
requiredViews.forEach((view) => expect(html).toContain(`data-view="${view}"`));
requiredGates.forEach((gate) => expect(html).toContain(`id="${gate}"`));
expect(html).toContain("prefers-reduced-motion");
expect(html).not.toMatch(/raw_content/i);
```

- [x] **Step 2: Run test to verify RED**

Run: `pnpm vitest run lib/voc-prototype.test.ts`

Expected: FAIL because `public/happynest-voc-os.html` does not exist.

### Task 2: Build the visual system and complete information architecture

**Files:**
- Create: `frontend/public/happynest-voc-os.html`

**Interfaces:**
- Consumes: `data-nav`, `data-view`, and `data-stage` attributes from the contract.
- Produces: `showView(viewId)`, `setStage(stageId)`, and a self-contained shell with seven views.

- [x] **Step 1: Implement the semantic shell and tokens**

```js
function showView(viewId) {
  document.querySelectorAll("[data-view]").forEach((view) => {
    view.hidden = view.dataset.view !== viewId;
  });
  document.body.dataset.activeView = viewId;
}
```

- [x] **Step 2: Add substantive content for all seven views**

The views must expose source/import state, schema coverage and taxonomy, feedback filters, agent investigation/evidence, action portfolio/matrix, and closed-loop KPIs. Overview must start the guided mission and show the AI/tools/human contract.

- [x] **Step 3: Run the focused contract test**

Run: `pnpm vitest run lib/voc-prototype.test.ts`

Expected: PASS for structure, privacy, and accessibility markers.

### Task 3: Implement the six-step guided mission and three human gates

**Files:**
- Modify: `frontend/public/happynest-voc-os.html`
- Modify: `frontend/lib/voc-prototype.test.ts`

**Interfaces:**
- Consumes: `showView(viewId)` and active mission state.
- Produces: `startMission()`, `advanceMission()`, `approveGate(gateId)`, `runInvestigation()`, `updateAction(actionId, patch)`, and `openActivity()`.

- [x] **Step 1: Extend contract test for mission controls and gate vocabulary**

```ts
expect(html).toContain("startMission");
expect(html).toContain("approveGate");
expect(html).toContain("Investigate more");
expect(html).toContain("AI proposes");
expect(html).toContain("Human governs");
```

- [x] **Step 2: Implement deterministic demo interactions**

The mission sequence is: upload/profile → mapping review → scoped analysis receipt → agent investigation → insight review → action prioritization/impact. Buttons update visible status, stage progress, evidence highlights, Activity Center counts, and a polite `aria-live` announcement.

- [x] **Step 3: Add failure/empty/help moments**

Include a UTF-8 import warning with recovery guidance, an empty-state invitation, disabled/high-consequence controls until prerequisites pass, a 100-item analysis cap receipt, and a plain-language PII boundary note.

- [x] **Step 4: Run focused and full frontend tests**

Run: `pnpm vitest run lib/voc-prototype.test.ts`

Run: `pnpm test`

Expected: all tests pass with zero failures.

### Task 4: Browser QA and delivery evidence

**Files:**
- Modify if needed: `frontend/public/happynest-voc-os.html`
- Modify: `docs/plans/FE-00-index.md`
- Create: `docs/handoffs/2026-08-31-codex-voc-os-html-prototype.md`

**Interfaces:**
- Consumes: the final static HTML through the local Next.js public server or a `file:///` URL.
- Produces: verified desktop/mobile screenshots and interaction evidence.

- [x] **Step 1: Validate markup and script syntax**

Run a Node extraction check that compiles the inline script with `new Function(script)` and confirms exactly one `<main>` plus no missing internal button targets.

- [x] **Step 2: Browser-test the critical path**

Open the artifact, navigate with sidebar controls, start the mission, pass Gates #1–#3, inspect evidence, adjust an action, open Activity Center, and verify no console errors.

- [x] **Step 3: Verify responsive and reduced-motion behavior**

Check at desktop and approximately 390px width; verify no horizontal overflow, readable evidence cards, reachable focus targets, and animations disabled under reduced motion.

- [x] **Step 4: Re-read spec and record evidence**

Confirm coverage of LISTEN, UNDERSTAND, ACT, three gates, dynamic schema/coverage, taxonomy governance, scoped budgeted analysis, findings vs hypotheses, action matrix, decision memory, and three latency KPIs. Record actual commands and outcomes in the append-only handoff.
