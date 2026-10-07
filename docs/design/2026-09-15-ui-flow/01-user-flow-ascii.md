# Happynest / Complete UI flow

**Design review edition | 15 September 2026 | Desktop first**

Six screens. Three human decisions. One continuous path from feedback to action.

This is the authoritative interaction specification for the accompanying generated UI images.
All sample records are fictional. All displayed feedback is sanitized.

## Reading key

```text
[ Button ]       Action                 [ Choice v ]    Dropdown
[x] / [ ]        Selection              >               Current item
-->              Forward path          <-->             Return path available
G1 / G2 / G3     Human decision         S01-S06          Main screen IDs
```

## 00 / The complete journey

```text
                                      SIGN IN
                                         |
                              CHOOSE / CREATE PRODUCT
                                         |
                   +---------------------+--------------------+
                   |                                          |
              First visit                               Returning visit
                   |                                          |
                   v                                          v
             S01 IMPORTER                           Last visited screen
                   |
       File <--> Preview <--> Mapping
                                 |
                        G1: CONFIRM MAPPING
                                 |
                         Import and receipt
                                 |
                                 v
                        S02 FEEDBACK VAULT <-------------------------+
                                 |                                  |
                         Select pending items                       |
                                 |                                  |
                    Review scope / usage --> Analyze                |
                                 |                                  |
                                 v                                  |
                         S03 DATA GRAPH <--> Feedback details -------+
                                 |
                    Explore --> Ask AI --> Investigate
                                 |
                                 v
                           S04 REPORTS <--> Evidence <--> Feedback
                                 |
                +----------------+-------------------+
                |                |                   |
              Reject      Investigate more      Review / edit
                |                |                   |
          Retain history    S03 Data Graph     G2: APPROVE FINDING
                                 |                   |
                          Revised report     Review usage / generate
                                 |                   |
                                 +--> S04            v
                                              S05 PRIORITY MATRIX
                                                     |
                                             Open / edit action
                                                     |
                                             G3: ACCEPT ACTION
                                                     |
                                                     v
                                              S06 STAKEHOLDERS
                                                     |
                                            Team carries out work
                                                     |
                                             Collect new feedback
                                                     |
                                   S01 --> S02 --> S03 follow-up
                                                     |
                                   New report linked to earlier report
```

**The stages organize navigation; they do not lock users into a wizard.** Review gates control
specific actions. Users can inspect saved data and return to earlier screens at any time.

## 01 / Persistent shell and entry

The header owns product selection, current tasks, and account access. The sidebar owns stage
navigation. Inner file, dataset, report, and department lists belong to the active screen.

```text
+----------------------------------------------------------------------------------------------------+
| Happynest   [ Demo AI v ]                                     [ Current tasks  2 ]   [ Account v ] |
+--------------------+-------------------------------------------------------------------------------+
|                    | STAGE / Screen                                                                |
| LISTEN             | Context and scope                                                             |
|   Importer         |                                                                               |
|   Feedback Vault   |                                                                               |
|                    |                                                                               |
| UNDERSTAND         |                            WORKSPACE                                          |
|   Data Graph       |                                                                               |
|   Reports          |                                                                               |
|                    |                                                                               |
| ACT                |                                                                               |
|   Priority Matrix  |                                                                               |
|   Stakeholders     |                                                                               |
|                    |                                                                               |
+--------------------+-------------------------------------------------------------------------------+
```

```text
+--------------------------------------------+     +----------------------------------------------+
| Happynest                                  |     | Choose a product                             |
| Sign in                                    |     |                                              |
|                                            |     | > Demo AI                       [ Open ]     |
| Email      [.............................] | --> |   Other product                              |
| Password   [.............................] |     |                                              |
|                                            |     | [ + Create product ]                         |
| [ Sign in ]                                |     | Name [....................................]  |
| Error stays beside the relevant field.     |     | Description [.............................]  |
+--------------------------------------------+     +----------------------------------------------+
```

- A new product with no feedback opens **Importer**.
- A returning product restores its last visited screen, including its valid navigation state.
- A pending task is visible in the header; it does not force a redirect away from the user's work.
- Sign out ends access. An expired session requests sign-in, then returns to the requested screen.

## 02 / LISTEN

### S01 / Importer

**Job:** bring a file into the product and finish its mapping review.

```text
+---------------------------------------------------------------------------------------------------+
| LISTEN / Importer                                                     Product: Demo AI            |
| Bring feedback into your product.                                                                 |
+--------------------------------------------------------------------+------------------------------+
|                                                                    | CURRENT TASKS                |
|                                                                    |                              |
|                         Get started                                | feedback-sep.csv             |
|                                                                    | Needs mapping review         |
|                   +--------------------------+                     | [ Continue mapping ]         |
|                   |       Import CSV         |                     |                              |
|                   +--------------------------+                     | Analysis A-12                |
|                                                                    | Processing 32 of 80          |
|                   [ Source ]     [ Source ]                        | [ View progress ]            |
|                   [ Source ]     [ Source ]                        |                              |
|                   Additional sources: coming later                 | [ View task history ]        |
|                                                                    |                              |
| RECENT IMPORTS                                                     |                              |
| feedback-aug.csv          120 rows       Imported     [ Open ]      |                             |
| survey-jul.csv             96 rows       Imported     [ Open ]      |                             |
+--------------------------------------------------------------------+------------------------------+
```

The four source tiles are inactive placeholders. CSV is the supported source in this design.

### L01-L04 / Four-step import wizard

```text
                   1 FILE <--> 2 PREVIEW <--> 3 MAPPING ---> 4 RESULT
                      ^            ^             |
                      |            |             v
                      |            +----- G1: CONFIRM MAPPING
                      |
                 Back preserves choices; no operation is automatically replayed.
```

```text
+---------------------------------------------------------------------------------------------------+
| L01 / Upload file                                                     Step 1 of 4                 |
| FILE ---------------- Preview ---------------- Mapping ---------------- Result                    |
+---------------------------------------------------------------------------------------------------+
| Product: Demo AI                                                                                  |
|                                                                                                   |
|                  +------------------------------------------------------------+                   |
|                  | Drop a CSV here, or [ Choose file ]                         |                  |
|                  | feedback-sep.csv                                           |                   |
|                  +------------------------------------------------------------+                   |
|                                                                                                   |
| File errors appear here, with a specific correction.                                              |
|                                                                                                   |
| [ Cancel ]                                                               [ Upload and preview ]   |
+---------------------------------------------------------------------------------------------------+
```

```text
+----------------------------------------------------------------------------------------------------+
| L02 / Preview                                                         Step 2 of 4                  |
| File ---------------- PREVIEW ---------------- Mapping ---------------- Result                     |
+----------------------------------------------------------------------------------------------------+
| feedback-sep.csv     83 rows     5 columns     Preview ready                                       |
| No AI used yet. Samples below are sanitized.                                                       |
|                                                                                                    |
| comment                         submitted_at     app_version    channel      extra                 |
|--------------------------------------------------------------------------------------------------  |
| <ORG> received a slow answer.   2026-09-01       2.1            Support      --                    |
| <ORG> found a bad citation.     2026-09-02       2.1            Survey       --                    |
|                                                                                                    |
| Review structure before asking AI to propose column meanings.                                      |
|                                                                                                    |
| [ Back to file ]                                                        [ Suggest mapping ]        |
+----------------------------------------------------------------------------------------------------+
```

```text
+---------------------------------------------------------------------------------------------------+
| L03 / Column mapping                                                  Step 3 of 4                 |
| File ---------------- Preview ---------------- MAPPING ---------------- Result                    |
+---------------------------------------------------------------------------------------------------+
| CSV COLUMN          PRODUCT MEANING                         SAMPLE                   REVIEW       |
|-------------------------------------------------------------------------------------------------- |
| comment             [ Feedback text v ]                    <ORG> received...        Ready         |
| submitted_at        [ Feedback date v ]                    2026-09-01               Ready         |
| app_version         [ Product field: version v ]           2.1                      Ready         |
| channel             [ Source metadata v ]                  Support                  Ready         |
| extra               [ Ignore v ]                           --                       Ready         |
|                                                                                                   |
| G1 / Confirm what these columns mean.                                                             |
| Resolve ambiguous mappings and missing required fields before importing.                          |
|                                                                                                   |
| [ Back to preview ]    [ Cancel import ]                              [ Confirm mapping & import ]|
+---------------------------------------------------------------------------------------------------+
```

```text
+----------------------------------------------------------------------------------------------------+
| L04 / Import result                                                   Step 4 of 4                  |
| File ---------------- Preview ---------------- Mapping ---------------- RESULT                     |
+----------------------------------------------------------------------------------------------------+
| Import completed                                                                                   |
|                                                                                                    |
|         83 source rows                 80 imported                 3 failed                        |
|                                                                                                    |
| [ View row errors ]                                                                                |
| Row 21: date needs ISO format.     Row 54: missing feedback.     Row 77: missing feedback.         |
| Correct and re-import only the failed rows.                                                        |
|                                                                                                    |
| [ Import another file ]                                                  [ Open Feedback Vault ]   |
+----------------------------------------------------------------------------------------------------+
```

**Progress and cancellation:** while mapping/importing runs, display progress and allow leaving
the screen. Reopen the same task from Current tasks. Offer cancellation only where supported;
closing the wizard never means cancelling a job. Back after import shows read-only history,
not an editable mapping that appears able to undo an already completed import.

### S02 / Feedback Vault

**Job:** inspect imported feedback and choose exactly what to analyze or explore.

```text
+---------------------------------------------------------------------------------------------------+
| LISTEN / Feedback Vault                                                        [ Import CSV ]     |
+----------------------+----------------------------------------------------------------------------+
| FILES                | [ Search feedback...................................................... ]  |
|                      | [ Date v ] [ Topic v ] [ Sentiment v ] [ Analysis state v ]                |
| All imports          |                                                                            |
| > feedback-sep.csv   | [ ] FEEDBACK                     SOURCE       TOPIC          STATE         |
|   feedback-aug.csv   |--------------------------------------------------------------------------- |
|   survey-jul.csv     | [x] <ORG> received a slow answer. Support      Performance    Ready        |
|                      | [x] <ORG> found a bad citation.   Survey       Accuracy       Ready        |
|                      | [ ] <ORG> saw output stop.       Support      --             Pending       |
|                      |                                                                            |
|                      | 2 selected                              [ Clear selection ]                |
|                      |                                                                            |
|                      | [ Analyze pending items ]                    [ Explore selected ]          |
|                      |                                                                            |
|                      | Showing 1-25 of 80                                  [ < ] 1 2 3 4 [ > ]    |
+----------------------+----------------------------------------------------------------------------+
```

- Opening the Vault from an import selects that import.
- Analysis uses explicitly selected pending items; without a selection, preview a clearly
  counted pending batch from the active import. A batch contains at most 100 items.
- Ready selections can be explored immediately. Mixed selections show how many items need
  analysis and how many are excluded from analysis-dependent charts.
- In the illustrated selection, both rows are Ready: Analyze pending items is disabled with
  the helper `0 pending selected`, while Explore selected remains active.
- Pending items can still be read as feedback. They are never silently counted as analyzed.

### L05 / Analysis receipt and resumable progress

```text
+------------------------------------------------+   +----------------------------------------------+
| Review analysis                                |   | Analysis A-12                                |
|                                                |   |                                              |
| Product: Demo AI                               |   | Processing selected feedback                 |
| Import: feedback-sep.csv                       |   |                                              |
| Scope: 80 pending items                        |-->| [################..............] 32 / 80     |
|                                                |   |                                              |
| Estimated usage: from the current preview      |   | You can leave this screen.                   |
| Maximum attempts: shown before starting        |   | Reopen from Current tasks.                   |
|                                                |   |                                              |
| [ Back ]                     [ Start analysis ]|   | [ Return to Vault ]        [ Stop analysis ] |
+------------------------------------------------+   +----------------------------------------------+
```

Stop analysis requests a stop after the current item/chunk; it does not claim an immediate abort.
If the selection changed since preview, refresh the receipt and require a fresh explicit start.
Never invent a precise monetary estimate when the provider only supplies usage estimates.

### D01 / Shared feedback detail

```text
+---------------------------------------------------------------+
| Feedback F-18                                  [ Close  X ]   |
| [ < Previous ]                                  [ Next > ]    |
+---------------------------------------------------------------+
| <ORG> found an invalid citation in the answer.                |
|                                                               |
| Import        feedback-sep.csv                                |
| Occurred      2026-09-02                                      |
| Topic         Accuracy                                        |
| Sentiment     Negative                                        |
| Analysis      Ready                                           |
|                                                               |
| [ Similar feedback ]              [ Explore this topic ]      |
|                                                               |
| REFERENCED IN                                                 |
| R-07  Accuracy complaints increased             [ Open ]      |
|                                                               |
| [ Back to originating view ]                                  |
+---------------------------------------------------------------+
```

Previous/Next traverse the originating result set. Closing restores its filters, selection,
pagination, and scroll. If similarity is unavailable, explain that analysis is required.

## 03 / UNDERSTAND

### S03 / Data Graph

**Job:** explore data, inspect its feedback, and investigate a clear question.

```text
+----------------------------------------------------------------------------------------------------+
| UNDERSTAND / Data Graph                                                                            |
| Demo AI / 2 imports / Sep 1-14 / 120 analyzed / 15 pending excluded                                |
+--------------------+-------------------------------------------------------+-----------------------+
| DATASETS           | [ Word cloud ]  [ Trends ]  [ Topics ]  [ Table ]      | ACTIVITY TRACE       |
|                    |                                                       |                       |
| [x] sep-survey     | [ Date v ] [ Topic v ] [ Sentiment v ]                | Investigation I-07    |
| [x] sep-support    |                                                       |                       |
| [ ] aug-survey     |                  slow                                 | [x] Scope checked     |
|                    |                                                       | [x] Trend checked     |
| [ Apply scope ]    |         citations       ACCURACY                      | [x] Samples found     |
|                    |                                                       | [x] Draft ready       |
| [ Open Vault ]     |                 response        timeout               |                       |
|                    |                                                       | [ Open report ]       |
|                    |         reliability          speed                    | [ View evidence ]     |
|                    |                                                       |                       |
|                    | Selected: accuracy                                    | Scope fixed at start  |
|                    | [ View 24 feedback items ]                            |                       |
|                    | Word size = frequency in this scope.                  |                       |
+--------------------+-------------------------------------------------------+-----------------------+
|                    | Ask about this data                                                           |
|                    | [ Why did accuracy complaints rise?.......................... ] [ Ask AI ]    |
+--------------------+-------------------------------------------------------------------------------+
```

```text
EXPLORE                                                INVESTIGATE
Select datasets / filters                              Question OR emerging signal
          |                                                       |
     Apply scope                                            Review scope / usage
          |                                                       |
  Click word / chart point                                  Explicitly start
          |                                                       |
  Matching feedback <--> Feedback detail                    Running activity trace
          |                                                       |
  Back to same visualization                                 Draft --> Open report
```

The trace contains observable checks, tool activity, evidence, and failures. It is not a private
reasoning transcript. Changing chart filters cannot change a running investigation's scope.

### S04 / Reports

**Job:** review an investigation's findings against evidence and decide whether to act.

```text
+--------------------------------------------------------------------------------------------------+
| UNDERSTAND / Reports                                                                             |
+--------------------+-------------------------------------------------------+---------------------+
| REPORTS            | R-07 / Accuracy complaints increased                  | EVIDENCE            |
|                    | Needs review                                          |                     |
| [ Search....... ]  |                                                       | E-01 / Trend        |
| [ Status v ]       | [ Read report ] [ Review history ]                   | [ Inspect ]          |
|                    |                                                       |                     |
| > R-07             | SUMMARY                                               | E-02 / Samples      |
|   Needs review     | Accuracy complaints increased in the selected period.| [ Inspect ]          |
|                    |                                                       |                     |
|   R-06             | FINDINGS                                              | COVERAGE            |
|   Approved         | Supported observations with evidence links. [E-01]   | 120 analyzed         |
|                    |                                                       | 15 pending excluded |
|   R-05             | HYPOTHESES                                            |                     |
|   Rejected         | Possible explanations, clearly marked unconfirmed.   | Source imports       |
|                    |                                                       | [ Open in Vault ]   |
|                    | LIMITATIONS                                           |                     |
|                    | Missing version values limit attribution.            | Fixed scope          |
|                    |                                                       | Sep 1-14            |
|                    | [ Back to investigation ]                             |                     |
+--------------------+-------------------------------------------------------+---------------------+
| G2 / Review the finding                                                                          |
| [ Reject ] [ Investigate more ] [ Edit finding ]                            [ Approve finding ]  |
+--------------------------------------------------------------------------------------------------+
```

The report body is rendered Markdown, with distinct findings, hypotheses, and limitations.
Evidence opens in a nested panel while preserving the report position.

### U01-U03 / Evidence, review, and revision

```text
+--------------------------------+   +--------------------------------+   +-------------------------+
| R-07 / Report                  |   | E-02 / Supporting evidence     |   | F-18 / Feedback         |
|                                |-->|                                |-->|                         |
| Finding links to [ E-02 ]      |   | Source: feedback samples       |   | Sanitized text          |
|                                |   | Scope: Sep 1-14                |   | Import and labels       |
| Report scroll stays unchanged. |   | F-18 [ Open feedback ]         |   |                         |
|                                |<--| [ Back to report ]             |<--| [ Back to evidence ]    |
+--------------------------------+   +--------------------------------+   +-------------------------+
```

```text
NEEDS REVIEW
    +--> Approve finding -------------------------------> APPROVED
    +--> Edit finding --> Save edit and approve ---------> APPROVED (edited)
    +--> Reject ----------------------------------------> REJECTED / retained
    +--> Investigate more --> original context in S03 ---> INVESTIGATING
                                                               |
                                                        Revised report
                                                               |
                                                        NEEDS REVIEW

APPROVED --> Generate actions --> Review expected usage --> S05 Priority Matrix
```

- Editing shows the finding and reason fields; evidence is not silently rewritten to fit the edit.
- An approved report retains its recorded scope. Fresh imports do not rewrite its conclusions.
- Review history records the decision, time, reviewer, and revision; rejected reports remain visible.
- If the investigation budget is exhausted, explain the limit before offering a new run.
- New follow-ups link to the earlier report and retain both. No report is labelled approved just
  because another report on the same topic was approved.

## 04 / ACT

### S05 / Priority Matrix

**Job:** decide which proposed actions deserve attention, using effort and customer impact.

```text
+---------------------------------------------------------------------------------------------------+
| ACT / Priority Matrix                                                                             |
| [ Report: R-07 v ] [ Department: All v ] [ Status: Active v ]                    [ + Add action ] |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
| Expected customer impact                                                                          |
| High ^                                                                                            |
|      |          QUICK WINS                    |          STRATEGIC INVESTMENTS                    |
|      |                                        |                                                   |
|      |           o A-02                       |                     o A-01                        |
|      |                                        |                                                   |
|      |                                        |                                                   |
|      +----------------------------------------+-------------------------------------------------- |
|      |          LOW PRIORITY                  |          RECONSIDER                               |
|      |                                        |                                                   |
|      |                 o A-03                 |                 o A-04                            |
|      |                                        |                                                   |
| Low  +--------------------------------------------------------------------------------------->    |
|                  Low                          Effort                                  High        |
|                                                                                                   |
| Points are actions. Priority also considers urgency and confidence.                               |
| [ View source report ]                                                [ View by department ]      |
+---------------------------------------------------------------------------------------------------+
```

Impact and effort use 1-10 scales, split at 5. Clicking opens the action. Dragging previews new
scores in the same drawer; only Save edits or Accept action confirms them. Keyboard-accessible
numeric inputs provide the same change without dragging. Active includes proposed, edited, and
accepted actions; rejected items are available through the status filter.

### D02 / Shared action drawer

```text
+--------------------------------------------------------------------+
| A-02 / Improve citation fallback                   [ Close  X ]    |
| Engineering / Proposed                                             |
+--------------------------------------------------------------------+
| WHAT                                                               |
| Show a clear fallback when a citation cannot be verified.          |
|                                                                    |
| WHY                                                                |
| Supported by the reviewed finding in R-07. [ Open report ]         |
|                                                                    |
|                         AI ESTIMATE          YOUR DECISION         |
| Impact                       8                   [ 8 ]             |
| Effort                       3                   [ 3 ]             |
| Urgency                      9                   [ 9 ]             |
| Confidence                 0.84                  --                |
|                                                                    |
| Reason for changes                                                 |
| [..............................................................]   |
|                                                                    |
| G3 / You decide the final priority.                                |
| [ Reject ]           [ Save edits ]           [ Accept action ]    |
+--------------------------------------------------------------------+
```

```text
PROPOSED --> Save edits --> EDITED / awaiting decision
    |                         |
    +---- Accept action ------+--> ACCEPTED --> visible by department
    |                         |
    +---- Reject -------------+--> REJECTED --> retained in history
```

Save edits never implies acceptance. AI estimates remain visible after human overrides.
Adding a manual action requires a department, recommendation, and scores; its final button
is **Add and accept action**, making that decision explicit.

### S06 / Stakeholders

**Job:** see what each department should do and inspect the evidence behind each decision.

```text
+---------------------------------------------------------------------------------------------------+
| ACT / Stakeholders                                                                                |
| [ Report: R-07 v ] [ Status: Accepted v ]                                                         |
+--------------------+--------------------------------------------------+---------------------------+
| BY DEPARTMENT      | [ Search actions.............................. ] | WHAT                      |
|                    |                                                  |                           |
| All                | ACTION                 PRIORITY    STATUS        | A-02                      |
| > Engineering      |--------------------------------------------------| Citation fallback         |
| Support            | > Citation fallback    High        Accepted      |                           |
| Design             |   Citation checks      High        Accepted      | Recommendation            |
| Marketing          |                                                  | Show a clear fallback     |
| Legal              |                                                  | when a citation cannot    |
| Finance            |                                                  | be verified.              |
| Operations         |                                                  |                           |
| Sales              |                                                  | WHY                       |
|                    |                                                  | Finding in R-07           |
|                    |                                                  | [ Open report ]           |
|                    |                                                  |                           |
|                    |                                                  | [ Open action ]           |
|                    |                                                  | [ Show in matrix ]        |
+--------------------+--------------------------------------------------+---------------------------+
```

Matrix and Stakeholders show the same action records. Changes appear in both views. Switching
between them preserves the selected report and action; the destination reveals its department
or matrix point. A selected proposed action may temporarily reveal that status in Stakeholders,
so the usual Accepted filter does not hide the item the user just opened.

No named-person assignment is implied. Departments without relevant actions show an empty
state with **Show proposed actions** and **Open Priority Matrix**.

### A01 / Follow-up

```text
ACCEPTED ACTIONS --> Team acts outside this flow --> NEW FEEDBACK
                                                        |
                                       Import --> Analyze --> Data Graph
                                                        |
                                       Follow up on R-07 / choose new dates
                                                        |
                                               NEW REPORT R-08
                                                        |
                                       [ View previous report R-07 ]
                                                        |
                                       Review observed changes and limitations
                                                        |
                                       Approve --> revise / add actions
```

Accepted means the decision is accepted, not that implementation is complete. A follow-up
reports observed changes; it does not assume that an action caused them.

## 05 / Global tasks, back/forward, and recovery

### G01 / Current tasks

```text
+---------------------------------------------------------------+
| Current tasks                                 [ Close  X ]    |
| Product: Demo AI                                              |
+---------------------------------------------------------------+
| NEEDS YOUR REVIEW                                             |
| Import / feedback-sep.csv          [ Continue mapping ]       |
| Investigation / I-07              [ Review finding ]          |
|                                                               |
| RUNNING                                                       |
| Analysis / A-12 / 32 of 80         [ View progress ]          |
|                                                               |
| HISTORY                                                       |
| Previous completed and failed tasks [ View history ]          |
+---------------------------------------------------------------+
```

The Importer panel and header task drawer refer to the same jobs. Labels reflect actual state.
Opening, refreshing, or navigating back to a task never replays a mutation.

### G02 / Unsaved work

```text
+---------------------------------------------------------------+
| Discard your changes?                                         |
| Your unsaved edits to A-02 will be lost.                      |
|                                                               |
| [ Keep editing ]                         [ Discard changes ]  |
+---------------------------------------------------------------+
```

This protects action edits, finding edits, and unfinished mapping changes when navigating away
or switching products. Saved task state survives refresh; unsaved changes must not be presented
as saved. A browser unload warning is the fallback when an in-app dialog cannot be shown.

### Navigation rules

| From | Open | Return restores |
|---|---|---|
| Import wizard | Previous step | File and valid choices; no duplicate request |
| Vault | Feedback detail | Import, filters, selected IDs, page, and scroll |
| Data Graph | Matching feedback | Dataset scope, chart tab, selected point, and scroll |
| Report | Evidence, then feedback | Nested panel stack, report section, and evidence selection |
| Matrix / Stakeholders | Report | Original action, report scope, department, and matrix selection |
| Matrix | Stakeholders | Same action and report; reveal department and appropriate status |
| Any screen | Current task | Existing job, its progress, or its pending decision |
| Any screen | Browser Back / Forward | Navigation state only; never re-submit or re-approve |
| Any product | Another product | Separate data and tasks, with unsaved-edit protection |

### Recovery routes

```text
EMPTY PRODUCT          --> Import CSV
EMPTY FILTER RESULT    --> Clear filters --> previous complete result set
BAD FILE               --> File-specific error --> replace / correct CSV
AMBIGUOUS MAPPING      --> Highlight unresolved columns --> edit --> confirm
PARTIAL IMPORT         --> Row errors --> correction file with failed rows only
PENDING ANALYSIS       --> Review scope --> analyze --> return to exploration
SELECTION CHANGED      --> Refresh receipt --> explicit new confirmation
AI OPERATION FAILED    --> Failed stage / retained context --> explicit retry
INSUFFICIENT EVIDENCE  --> Explain limits --> investigate more / collect more data
UNAPPROVED REPORT      --> Review finding before generating actions
NO DEPARTMENT ACTIONS --> Show proposed actions / open matrix
MISSING SAVED ITEM     --> Explain unavailable item --> return to containing list
SESSION EXPIRED        --> Sign in --> return to requested screen
```

## 06 / Review walkthroughs

| # | Walkthrough | Pass condition |
|---|---|---|
| 1 | Product -> CSV -> G1 -> Vault -> analysis -> investigation -> G2 -> actions -> G3 -> department | All six screens participate; each human decision is explicit |
| 2 | Matrix -> action -> report -> evidence -> feedback -> Back through every level | Each origin and selection is restored |
| 3 | Needs-review report -> investigate more -> revised finding -> review | Revised report requires a new decision and retains history |
| 4 | Leave analysis -> browse Vault -> reopen Current tasks | Same job continues; nothing is submitted twice |
| 5 | Fresh feedback -> follow-up -> new report -> prior report | Both scopes remain visible and earlier conclusions are preserved |
| 6 | Preview -> Back -> Preview; browser Back/Forward after approval | No duplicate upload, AI run, import, or approval |
| 7 | Drag action -> discard; edit score -> save; accept action | Discard restores position; save preserves AI values; accept is explicit |
| 8 | Partial import -> inspect row errors -> import corrections | Successful rows are not accidentally repeated |
| 9 | Edit finding -> switch product -> Keep editing / Discard | Unsaved work is protected and products never mix |

## 07 / Generated-image coverage

The images illustrate the UI. This ASCII document defines exact interaction behavior and copy.

| Image | Main coverage |
|---|---|
| 01-importer.png | S01: upload entry, source placeholders, recent imports, current tasks |
| 02-feedback-vault.png | S02 and D01: files, filters, feedback selection, detail drawer |
| 03-listen-flow.png | Entry, file, preview, mapping G1, import receipt, analysis receipt/progress |
| 04-data-graph.png | S03: datasets, visualization, scoped question, activity trace |
| 05-reports.png | S04: investigation list, rendered report, evidence, G2 decisions |
| 06-understand-flow.png | Usage/start, evidence round trip, edit, revise, approve/generate |
| 07-priority-matrix.png | S05 and D02: action points, correct axes, estimates, G3 decisions |
| 08-stakeholders.png | S06: departments, accepted actions, shared action details |
| 09-act-flow.png | Score preview/save, manual action, acceptance, department view, follow-up, recovery |

Image filenames are the target set; the final gallery links only to verified delivered files.
No production application/API implementation is part of this design-artifact deliverable.
