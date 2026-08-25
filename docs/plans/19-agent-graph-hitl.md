# Phase 19 — Fully LLM-routed agent graph + HITL interrupt + API

> **Nguồn:** brainstorm 2026-08-25 (owner chốt **fully LLM-routed** — router node quyết từng bước, chấp nhận chi phí) + `docs/example-agent-flow.mmd` (đã critique: loop có cap) + spike S5 + pattern phase 13 (`hitl_graph`) · decisions 2026-08-26 · Ngày viết: 2026-08-26
> **Thứ tự pha:** P6-C của [delivery-execute-plan.md](delivery-execute-plan.md) — điều kiện cứng: **18 ✅** (đủ 5 tool) + data demo đã `/clusters/run` (17 Task 3). **Executor đọc cả plan 13 (pattern checkpointer) + decisions 2026-08-25 entry checkpoint-thread.**

## 1 · Bối cảnh & hiện trạng (verify bằng lệnh thật khi mở phase, ghi kết quả)

```bash
cd backend
grep -n "ensure_checkpointer_ready\|def run_graph" app/services/hitl_graph.py   # pattern tái dùng
grep -n "pipeline_version\|llm_model" app/models/analysis_run.py                # cột phân biệt agent run
uv run pytest -q
```

| Thành phần | Trạng thái | Việc phase này |
|---|---|---|
| Checkpointer | AsyncPostgresSaver qua `ensure_checkpointer_ready()` (thread nền boot, SelectorEventLoop riêng — entry 2026-08-25) | Tái dùng NGUYÊN cho thread agent |
| Graph HITL nhỏ | `hitl_graph.py` feedback-level đã production | Tham khảo; graph agent là StateGraph RIÊNG `thread_id = f"agent-{run_id}"` |
| `analysis_runs` | Đang chỉ do runner deterministic tạo (`pipeline_version` tự do String(50)) | Agent ghi row với `pipeline_version='agent-router-v1'` |
| Budget trace | `llm_call_logs.analysis_run_id` sẵn; call_type mới `route`/`critic` từ migration 0007 | COUNT theo run để bóp chi phí |
| FE approval UI | **Chưa có** — UF-03/FE-04 là màn runs deterministic | Non-goal; demo duyệt qua Swagger/curl |

## 2 · Mục tiêu pha + Non-goals

**Mục tiêu:** (1) StateGraph fully LLM-routed: node `route` (structured output, temperature=0) chọn tool/synthesize/finish MỖI BƯỚC, có cap bước + cap ngân sách LLM; (2) synthesize → Insight có `evidence_ids` validate whitelist + embedding; (3) critic checklist deterministic + đúng 1 lần reflection LLM; (4) risk gate RULE-BASED (không LLM phán rủi ro): cao → `interrupt()` chờ người, thấp → auto lưu draft; (5) decision endpoint resume graph → `insight_reviews` + `action_drafts`; (6) kill-restart-resume không duplicate.

**Non-goals:** FE màn approval (roadmap sau P6 — demo bằng API); scheduler/tự chạy định kỳ; Slack/Jira thật (draft copy-paste là đích cuối — quyết 25/08); multi-cluster song song (tuần tự từng cụm trong 1 run); sửa runner deterministic hay plans 13–16.

**Biên an toàn (chốt cứng):**
- `AGENT_MAX_STEPS=12` — vượt cap → buộc nhánh finish (synthesize nếu đã đủ evidence, không thì kết thúc không-insight).
- `AGENT_LLM_BUDGET_PER_RUN=24` — trước MỌI call tốn LLM (route/classify/generate_insight/critic), COUNT `llm_call_logs WHERE analysis_run_id=run.id AND call_type IN ('classify','embed','name_cluster','generate_insight','route','critic')`; ≥ budget → buộc finish ngay.
- Router CHỈ được chọn tên tool nằm trong `TOOLS()` registry — schema Literal chặn từ tầng Pydantic.

## 3 · Tasks

### Task 1 — Settings + state

**Files:** Modify `backend/app/core/config.py`; Create `backend/app/agents/state.py`

- [ ] Step 1.1: Settings thêm: `AGENT_MAX_STEPS:int=12`, `AGENT_LLM_BUDGET_PER_RUN:int=24`, `AGENT_TOP_CLUSTERS:int=3`, `AGENT_RISK_PRIORITY_THRESHOLD:float=0.70`, `AGENT_RISK_SEVERITY_SHARE:float=0.30`.
- [ ] Step 1.2: `AgentState(TypedDict)`: `run_id`, `targets: list[uuid]` (cluster ids sẽ điều tra), `current_cluster: uuid|None`, `observations: list[dict]` (mỗi obs `{tool, input_tóm_tắt, output_tóm_tắt ≤500 ký tự}`), `evidence: dict` (theo cluster), `insight_draft: dict|None`, `critic_failed_once: bool`, `risk_level: str|None`, `steps_used: int`, `decision: dict|None`. Commit: `feat(agents): settings caps and agent state schema`

### Task 2 — Nodes

**Files:** Create `backend/app/agents/nodes.py`

- [ ] Step 2.1: `assess`: nếu `targets` còn → set `current_cluster`, tổng hợp digest (metrics tóm tắt từ observations có sẵn). Node thuần code.
- [ ] Step 2.2: `route`: build prompt gồm digest + danh sách `{name, description}` từ `TOOLS()` + observation gần nhất; gọi `chat_structured(RouteDecision, ..., call_type=LlmCallType.route, temperature=0)` với `RouteDecision = {next: Literal[<5 tool>,"synthesize","finish"], rationale: str ≤200}`. **Guard trước khi gọi:** hàm `_llm_calls_used(db, run_id)` ≥ budget → trả cứng `{next:"finish", rationale:"budget exhausted"}` (không tốn call).
- [ ] Step 2.3: `dispatch`: tra `TOOLS()[decision.next]`, thực thi, đẩy obs vào state, tăng `steps_used`. `steps_used > AGENT_MAX_STEPS` → conditional edge ép về `synthesize_or_finish` thay vì quay lại assess. Tool raise → bắt thành obs lỗi (`{tool, error}`) và QUAY LẠI route (router tự thấy và chọn đường khác — đây là giá trị agentic).
- [ ] Step 2.4: `synthesize`: payload = metrics + quotes + precedents của cụm hiện tại (chỉ sanitized); 1 call `generate_insight` trả draft `{title ≤120, summary ≤600, suggested_action ≤400, evidence_feedback_ids[]}`; **validate server-side**: lọc id theo whitelist member cụm, cắt ≤5 (nguyên tắc plan 15 Task 2.4). Draft chưa persist.
- [ ] Step 2.5: `critic`: checklist deterministic — (a) ≥1 evidence hợp lệ; (b) title/summary/action khác rỗng đúng giới hạn; (c) ≥1 precedent ĐÃ tra hoặc obs chứa lý do "không cần" (tránh insight mù tổ chức memory). Fail lần 1 VÀ `critic_failed_once=false` → 1 call `critic` (reflection: nhận deficit, trả draft sửa lại, temperature=0), set flag, quay lại kiểm tra. Fail lần 2 → **BỎ cụm này** (không persist insight yếu), obs ghi lý do, sang target kế. Pass → persist.
- [ ] Step 2.6: `persist_insight`: INSERT Insight (`review_status=pending`, `cluster_id`, evidence_ids, embedding triplet điền bằng embedder cho `title.summary`) TRONG transaction; trả id. Node tách `finalize_no_insight` cho nhánh finish-sớm (chỉ đóng run).
- [ ] Step 2.7: `risk_gate` (thuần rule, KHÔNG LLM):
  ```
  escalate ⇐ suggested_priority ≥ AGENT_RISK_PRIORITY_THRESHOLD
          OR share(severity ∈ {high,critical}) ≥ AGENT_RISK_SEVERITY_SHARE
          OR (is_emerging AND is_spike)
  ```
  Thấp → `auto_finalize`: sinh `action_drafts` bằng TEMPLATE fill từ title/summary/suggested_action (kind=`draft_ticket` + `slack_message`, body tiếng Việt khuôn sẵn — KHÔNG tốn LLM), `review_status='approved'`, KHÔNG ghi `insight_reviews` (KPI phase 20 phân biệt auto/HITL chính nhờ vắng row này). Cao → `await_approval`: `interrupt(payload)` với `{insight, quotes, metrics, precedents, options:["approve","edit","reject"]}`.
- [ ] Step 2.8: `apply_decision`: đọc resume payload `{action, edited_title?, edited_summary?, edited_suggested_action?, reason?}`:
  - `approve` → status `approved` + drafts template + `InsightReview(original_value=draft snapshot, action=approve, reason, reviewer_id)`;
  - `edit` → các trường được sửa: text chạy `presidio_service.sanitize` TRƯỚC khi lưu (raw người gõ không bao giờ lưu thẳng — nguyên tắc phase 13), regenerate embedding nếu title/summary đổi, status `edited` + drafts từ nội dung MỚI + `InsightReview(edited_value=…, action=edit)`;
  - `reject` → status `rejected`, KHÔNG sinh draft, `InsightReview(original_value=…, reason)` — rejection trở thành precedent âm mà `retrieve_similar_insights` sẽ trả ra ở các run sau.
  Toàn bộ trong 1 transaction; commit: gộp cùng Task 4 sau khi route sống.

### Task 3 — Graph assembly + runner job

**Files:** Create `backend/app/agents/graph.py`, `backend/app/jobs/agent_runner.py`

- [ ] Step 3.1: `build_agent_graph(checkpointer)`: edges — `assess→route`; `route` conditional: tool→`dispatch→assess` / `synthesize→synth...→critic` / `finish→finalize_no_insight`; critic pass→`persist→risk_gate`; risk_gate conditional auto/interrupt; interrupt resume→`apply_decision→END`. Compile với checkpointer.
- [ ] Step 3.2: `agent_runner.start_agent_run(db, targets)`: INSERT AnalysisRun(`pipeline_version="agent-router-v1"`, llm_model/prompt_version/embedding_model từ settings, total_count=len(targets)); spawn background thread (pattern y hệt jobs/analysis_runner) chạy `run_graph(lambda: graph.ainvoke(init_state, config))` với wrapper SelectorEventLoop của `hitl_graph.run_graph`; thread_id `f"agent-{run_id}"`; on-complete/crash update `status/completed_at/error` nuốt exception (BackgroundTasks philosophy phase 09). Chọn targets: TOP `AGENT_TOP_CLUSTERS` clusters ORDER BY `suggested_priority DESC NULLS LAST` WHERE `is_emerging OR is_spike OR suggested_priority >= threshold`; rỗng → run completed ngay với note. Commit: `feat(agents): langgraph router graph with budget-capped background runner`

### Task 4 — Routes

**Files:** Create `backend/app/api/routes/agent.py`; Modify `backend/app/main.py` (include router); Modify `docs/api-checklist.md` (**hard rule #10 — cùng commit**)

- [ ] Step 4.1: Router prefix `/api/agent`, `dependencies=[Depends(require_role("pm","operations"))]`.
- [ ] Step 4.2: `POST /runs` → 200 `{run_id, targets}` (thread nền khởi động). Run đang running cho cùng điều kiện → vẫn cho tạo run mới (agent run replace-all KHÔNG xảy ra vì insight mới insert thêm, không xoá cũ — khác runner deterministic; ghi rõ hành vi này vào api-checklist).
- [ ] Step 4.3: `GET /runs/{id}` → `{status, steps_used, llm_calls_used, llm_budget, targets, insights_created, error?, pending_approval?}` — pending_approval đọc từ graph state snapshot (`get_state(config)`) khi thread đang interrupted; 404 run lạ.
- [ ] Step 4.4: `POST /runs/{id}/decision` body `AgentDecisionIn` (validator: `edit` phải có ≥1 trường edited; sai → 422) → `run_graph(lambda: graph.ainvoke(Command(resume=payload), config))` → 200 `{insight_id, review_status, drafts_created}`. Thread completed mà nhận POST → 409 (mirror pre-check thu hẹp phase 13: chỉ chặn cứng khi graph đã END; crash-dở-dâng vẫn resume được).
- [ ] Step 4.5: Unit test schemas + integration `-m integration` (`tests/test_agent_api_integration.py`): fake-LLM trajectory scripted (mock `chat_structured` trả kịch bản route→metrics→quotes→precedents→synthesize→finish) chạy full đến interrupt trên 1 cụm giả → approve qua API → assert Insight + 2 ActionDraft + InsightReview đúng 1 bộ. Verify PASS. Commit: `feat(agents): run/status/decision endpoints replace nothing (new surface)`

### Task 5 — Kill/restart/resume evidence

**Files:** Create `backend/scripts/evidence_agent_checkpoint_resume.py`; Create `docs/evidence/agent-checkpoint-resume.md`

- [ ] Step 5.1: Script mirror `evidence_hitl_checkpoint_resume.py`: start run thật trên planted cluster → poll tới interrupted → KILL process → process mới login + POST decision → assert insight/draft/review ĐÚNG 1 bản (SQL count), run completed.
- [ ] Step 5.2: Chụp log 2 phiên + SQL counts vào `docs/evidence/agent-checkpoint-resume.md`. Commit: `docs(evidence): agent kill-restart-resume procedure and results`

## 4 · Acceptance criteria + Evidence cần chụp

- [ ] Trên planted cluster: run đầy đủ kết thúc bằng interrupt; payload hiển thị insight + quotes (sanitized) + precedents; `llm_calls_used ≤ AGENT_LLM_BUDGET_PER_RUN` (assert từ mock call-count unit + số liệu thật integration)
- [ ] Approve/edit/reject qua API đúng §3.8 (status, drafts, review rows); edit thiếu trường → 422; sai role → 403
- [ ] Auto path (cụm rủi ro thấp): approved ngay, CÓ drafts, KHÔNG insight_reviews row — test khẳng định cả 3
- [ ] Critic fail ×2 → cụm bị bỏ, không insight yếu tồn tại; run vẫn completed
- [ ] Kill-restart-resume: zero duplicate side effects (bằng chứng script Task 5) — **evidence số 1 chương kết quả**
- [ ] Không response/prompt nào chứa `raw_content` (canary test tái dùng từ 18)
- [ ] `docs/api-checklist.md` có đủ 3 endpoint mới (endpoint + method + auth + trạng thái + tác dụng)
- [ ] **Evidence:** JSON `GET /runs/{id}` lúc interrupted; screenshot interrupt payload; bảng llm_call_logs một run (thấy route/generate_insight/critic xen kẽ classify)

## 5 · Blocker rule

Router LLM "lạc đề" liên tục (chọn tool ngoài registry dù Literal chặn — fallback chain trả mode B) → hạ tham vọng có kiểm soát: giữ fully-routed CHO VIỆC CHỌN TOOL nhưng thêm heuristic warm-start (obs đầu tiên luôn auto-dispatch `get_cluster_metrics` không hỏi router — 1 ngoại lệ có lý do, entry decisions). interrupt × pooler quirks mới → fallback đã chứng kiến ở phase 13 (review-không-graph): apply decision trực tiếp kiểu endpoint corrections + vẫn ghi InsightReview; bằng chứng checkpoint trỏ về script S5 + evidence phase 13. Chi phí tín dụng cạn giữa pha → STOP, giữ phần committed, chuyển 20 (phần reports/KPI thuần SQL làm được độc lập), quay lại khi nạp tiền.
