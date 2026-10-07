# Happynest UI mockups / shared visual brief

## Deliverable

Generate actual high-fidelity raster UI images using built-in image_gen. Six main desktop screens
and three supporting flow boards accompany `01-user-flow-ascii.md`. These are design mockups,
not a working application. Do not change application code, routes, APIs, or existing prototype.

Use case: ui-mockup. English UI copy. All sample records are fictional and sanitized.

## Visual direction

Carry forward the project's existing Evidence Loom identity, refined for the user's six-screen layout.

- Pine Ink `#14251D`: narrow persistent global sidebar, main typography, primary buttons.
- Field Paper `#F1F3E9`: surrounding workspace.
- Chalk `#FCFCF8`: main data canvas and drawers.
- Lichen `#91A873`: selected navigation and completed/accepted states.
- Pollen `#DBAC3B`: human review/attention badges.
- Signal Blue `#3F738B`: evidence links, selected data, chart focus.
- Small muted red accents only for errors/rejected status.
- Typography: Aptos/Segoe UI style humanist sans for interface; restrained Palatino-style serif
  for report titles and findings; narrow monospace for IDs, timestamps and numeric labels.
- Flat, straight-on desktop application screenshots; crisp borders, 6-8px corner radii, quiet
  shadows on drawers only, excellent whitespace and information hierarchy, readable precise text.
- Product character comes from traceable evidence: matching small blue evidence IDs connect
  chart, report and action. No ornamental hero illustrations, glassmorphism, laptop/device frames,
  background desk photography, oversized marketing text, gradients, or floating perspective cards.

## Shared shell / main screens

Preferred landscape composition near 16:10. Ask for high resolution and readable UI text in the
prompt, without inventing unsupported tool parameters.

- Header: `Happynest`, `Demo AI` product dropdown, `Current tasks 2`, account avatar.
- Fixed left sidebar groups, verbatim:
  - LISTEN: Importer; Feedback Vault.
  - UNDERSTAND: Data Graph; Reports.
  - ACT: Priority Matrix; Stakeholders.
- Show all six navigation labels on every main screen, highlight the active one.
- Inner screen-specific rail sits to the right of the global sidebar; do not conflate the two.
- On flow boards, concise enlarged UI fragments are preferable to six tiny complete screenshots.
- Main screen images show functional mockups; sequence labels/callout arrows belong on flow boards.

## Shared content and invariants

- Product: Demo AI.
- Datasets: `sep-survey`, `sep-support`, `aug-survey`.
- Import demo: `feedback-sep.csv`: 83 rows; 80 imported; 3 failed.
- Investigation: I-07; fixed Sep 1-14 scope; 120 analyzed; 15 pending excluded.
- Report: R-07, `Accuracy complaints increased`; status Needs review until approved.
- Finding is an observed increase. Hypothesis about version 2.1 is explicitly unconfirmed.
- E-01 is trend evidence; E-02 is sanitized feedback samples. Never fabricate real identities.
- Feedback F-18: `<ORG> found an invalid citation in the answer.`
- A-02: `Improve citation fallback`, Engineering, impact 8, effort 3, urgency 9, confidence .84.
- A-01: `Add citation verification`, Engineering, high impact / high effort.
- A-03 low impact / low effort; A-04 low impact / high effort. Keep axes correct.
- Matrix X = Effort increasing right; Y = Expected customer impact increasing up.
- Three explicit human decisions: G1 Confirm mapping; G2 Approve finding; G3 Accept action.
- Save edits is distinct from Accept action. Accepted is distinct from delivered.
- Preserve original AI scores when showing human edits. Numeric input is the accessible drag alternative.
- No person-level task assignments or invented stakeholders; departments are Engineering, Support,
  Design, Marketing, Legal, Finance, Operations, Sales.
- No invented provider charges. Cost/usage review can say `Review expected usage` or show a count
  with `Estimate available before starting`, never invented dollar amounts.
- Word size is frequency, not priority. Source tiles beyond CSV are disabled placeholders.
- Reports are rendered documents, not a markdown-code editor. Findings, hypotheses and limitations
  must be visibly separate. Trace shows observable activity, not private reasoning.

## Output set / agent ownership

Each agent generates three images, sequentially within its stage, using the same brief.
Persist imagegen prompts verbatim in its own stage directory. Do not edit shared files.

| Owner | Stage directory | Images |
|---|---|---|
| listen_images | listen/ | 01-importer.png, 02-feedback-vault.png, 03-listen-flow.png |
| understand_images | understand/ | 04-data-graph.png, 05-reports.png, 06-understand-flow.png |
| act_images | act/ | 07-priority-matrix.png, 08-stakeholders.png, 09-act-flow.png |

Main screens each need one full image. Each flow board should be a large portrait 2-column by
3-row storyboard with six readable enlarged UI fragments and explicit directional arrows or
numbered steps. Use small Back links and clear state badges to represent the reverse paths.

### LISTEN board

1. Sign in and choose/create product (compact two-part fragment).
2. File picker and sanitized preview (compact two-part fragment).
3. Mapping table and G1 Confirm mapping.
4. Import completed receipt: 80 imported / 3 failed; row error correction link.
5. Analysis usage receipt, then 32/80 progress and return-to-Vault link.
6. Current tasks resume panel, invalid CSV/partial-import recovery, Back preserves choices.

### UNDERSTAND board

1. Question / fixed scope / expected usage / Start investigation.
2. Running activity trace, Open report when draft ready.
3. Report -> E-02 evidence -> F-18 feedback, with Back to evidence / Back to report.
4. G2 review: Reject / Investigate more / Edit finding / Approve finding.
5. Edit finding and approve; investigate-more loop produces revised Needs review report.
6. Approved report / Review expected usage / Generate actions, with insufficient-evidence recovery.

### ACT board

1. Drag point preview, AI estimate versus your decision, Save edits.
2. Add manual action: department, recommendation, numeric scores, Add and accept action.
3. G3 decision drawer: Reject / Save edits / Accept action.
4. Accepted action under Engineering, Show in matrix and Open report links.
5. Follow-up: new feedback -> new investigation -> R-08 linked to previous R-07.
6. Unsaved-edit dialog Keep editing / Discard changes; department empty state and rejected history.

## Quality control

Use the image-generation tool, inspect every returned image, and correct material layout/copy
errors with the same tool if needed. No drawing/replacing the requested raster output with
HTML/SVG/canvas. Keep assets non-destructive. Return actual paths and any limitations honestly.
The exact-copy/interaction source remains the ASCII document even if raster text differs.
