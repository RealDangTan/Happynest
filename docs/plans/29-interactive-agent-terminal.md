# Interactive Agent Terminal Implementation Plan

## Extension 2026-09-07 — owner-approved CSV-to-impact flow

Owner yêu cầu adapt bản đang làm, không tạo entry point trùng. Giữ
`scripts/agent_terminal.py` mặc định cho chế độ cũ; thêm `--flow` gọi HTTP
wizard, launcher `scripts/start-be-terminal.ps1` tại root. Triển khai inline
tại checkout hiện có theo yêu cầu owner; bảo toàn thay đổi FE.

- [x] Extend existing entry point; separate HTTP adapter and sequential steps.
- [x] LISTEN preview, explicit paid mapping, Gate #1 edits/import progress.
- [x] Scoped analysis receipt, batch/selection, embedding readiness, similar.
- [x] UNDERSTAND, Gate #2 approve/edit/investigate/reject, ACT + Gate #3.
- [x] Reports and product-scoped impact endpoint; preserve legacy impact CLI.
- [x] ID-only resume, explicit cancel, no automatic mutation replay.
- [x] Sanitize question/decision/action input before graph or persistence.
- [x] Verify complete synthetic API/PG/graph flow with mocked providers.
- [x] Verify launcher interaction, finish docs and append handoff evidence.

Owner runs one command in their own terminal and types there directly;
this extension supersedes the old requirement to attach a Codex-owned PTY.

---

> **For agentic workers:** REQUIRED SUB-SKILL: Use the `executing-plans` skill to implement this plan task-by-task INLINE (no subagents in this repo — limited LLM API credit). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a real interactive terminal where the owner types a question, watches live LLM trace metadata, reviews Gate #2, optionally runs ACT, and returns to another prompt.

**Architecture:** A testable terminal application in `app/services/agent_terminal.py` owns prompts and output while a real runtime adapter owns Supabase, LangGraph, PII sanitization, live trace polling, Langfuse flush, and ACT. A thin script is the executable entry point. The existing UNDERSTAND decision path also closes `analysis_runs` after terminal/API final decisions so displayed lifecycle state is truthful.

**Tech Stack:** Python 3.12, SQLAlchemy, LangGraph, Presidio/Stanza, Langfuse, pytest.

**Spec:** User request dated 2026-09-02; `docs/VoC Agent Operating System — Technical Implementation Plan.md` §§38–44, §60; `docs/api-checklist.md` agent routes.

## Global Constraints

- Never send the raw terminal question to the agent; call `presidio_service.sanitize()` first and pass only `sanitized_text`.
- Live terminal traces show metadata only: call type, success/error, latency, token counts, and model; never prompt or response content.
- Keep the existing dual trace path: Langfuse plus permanent `llm_call_logs`.
- No Docker, no new dependencies, no frontend changes, no endpoint additions.
- Execute inline; do not spawn subagents.

---

### Task 1: Test-first interactive terminal orchestration

**Files:**
- Create: `backend/tests/test_agent_terminal_unit.py`
- Create: `backend/app/services/agent_terminal.py`
- Create: `backend/scripts/agent_terminal.py`

**Interfaces:**
- Consumes: `TerminalRuntime.list_products()`, `sanitize_question()`, `run_understand()`, `decide()`, and `generate_actions()`.
- Produces: `run_interactive(runtime, input_fn, output_fn)` and `format_trace_row(row)`; executable `python scripts/agent_terminal.py`.

- [x] **Step 1: Write the failing orchestration and trace-format tests**

```python
def test_session_sanitizes_before_agent_and_allows_owner_to_approve():
    runtime = FakeRuntime()
    inputs = iter(["Happynest", "contact test@example.com", "a", "n", "/quit"])
    output = []
    run_interactive(runtime, lambda prompt: next(inputs), output.append)
    assert runtime.questions == ["contact <EMAIL>"]
    assert runtime.decisions == ["approve"]
    assert any("[trace] plan | OK | 120ms" in line for line in output)

def test_trace_line_contains_metadata_but_not_payload():
    line = format_trace_row(FakeTrace())
    assert line == "[trace] plan | OK | 120ms | tokens 10→4 | demo-model"
    assert "raw input" not in line
```

- [x] **Step 2: Run RED**

Run: `python -m pytest tests/test_agent_terminal_unit.py -q`

Expected: collection fails because `app.services.agent_terminal` does not exist.

- [x] **Step 3: Implement the minimal terminal app and real runtime**

```python
def run_interactive(runtime, input_fn=input, output_fn=print):
    # choose product → sanitize question → run with trace sink → Gate #2
    # approve/reject → optional ACT → loop until /quit
```

The real runtime creates `AnalysisRun`, starts a metadata-only polling thread over `llm_call_logs`, calls `understand_agent.runner`, displays the interrupt payload, resumes the human decision, optionally calls `act_agent.generate_actions`, and flushes Langfuse after each cycle.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest tests/test_agent_terminal_unit.py -q`

Expected: all terminal unit tests pass.

### Task 2: Close UNDERSTAND lifecycle after final Gate #2 decisions

**Files:**
- Modify: `backend/tests/test_understand_agent.py`
- Modify: `backend/understand_agent/nodes.py`
- Modify: `docs/api-checklist.md`

**Interfaces:**
- Consumes: existing `resume_with_decision(run_id, payload)`.
- Produces: final approve/edit/reject sets `AnalysisRun.status=completed`, `processed_count=1`, and `completed_at`; `investigate_more` remains running.

- [x] **Step 1: Add the failing lifecycle assertion**

```python
db.expire_all()
finished = db.get(AnalysisRun, run_id)
assert finished.status == RunStatus.completed
assert finished.processed_count == 1
assert finished.completed_at is not None
```

- [x] **Step 2: Run RED**

Run: `python -m pytest tests/test_understand_agent.py -q -m integration`

Expected: approve scenario fails because the run remains `running`.

- [x] **Step 3: Implement the lifecycle transition in `apply_decision`**

```python
if action != "investigate_more":
    run = db.get(AnalysisRun, uuid.UUID(state["run_id"]))
    run.status = RunStatus.completed
    run.processed_count = 1
    run.completed_at = datetime.now(timezone.utc)
```

Update the existing GET status row in `docs/api-checklist.md` to state that final Gate #2 decisions close the run.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest tests/test_understand_agent.py -q -m integration`

Expected: all UNDERSTAND integration cases pass, including lifecycle completion.

### Task 3: Verify and open the interactive terminal

**Files:**
- Modify: `docs/plans/00-index.md`
- Create: `docs/handoffs/2026-09-02-codex-interactive-agent-terminal.md`

**Interfaces:**
- Consumes: `backend/scripts/agent_terminal.py` and configured `backend/.env`.
- Produces: a visible Codex terminal panel waiting at `Question >`.

- [x] **Step 1: Run focused and full verification**

Run: `python -m pytest tests/test_agent_terminal_unit.py -q`

Run: `python -m pytest -q`

Expected: zero failures; existing external-provider warnings may remain warnings only.

- [x] **Step 2: Start the CLI in a PTY**

Run: `python scripts/agent_terminal.py`

Expected: banner, Langfuse connection status, product prompt, then interactive question prompt.

- [ ] **Step 3: Open that PTY in the Codex terminal panel**

Attempted with PTY session `11691`; Codex returned `queued` instead of
attaching it to the visible terminal tab. The same interactive CLI is available
directly with the documented one-line command in the current terminal.

Use the returned terminal session id. The owner types directly; the agent must not pre-fill the question.

- [x] **Step 4: Record evidence and phase status**

Mark phase 29 complete only after tests pass and the terminal is visibly waiting for input. Record the session behavior and lifecycle fix in a new append-only handoff.
