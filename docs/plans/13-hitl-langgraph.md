# Phase 13 — HITL LangGraph production + Reviews/Corrections API

> **Nguồn:** [`delivery-design-spec.md`](delivery-design-spec.md) §5 P2 + §3 C3 · [`delivery-contracts.md`](delivery-contracts.md) C3 + "Áp dụng chung" + "Migration duy nhất" · spike S5 (`decisions.md` 2026-08-24: AsyncPostgresSaver + SelectorEventLoop) · Ngày viết: 2026-08-25 (viết sớm theo decisions cùng ngày)
> **Thứ tự pha:** P2 của [delivery-execute-plan.md](delivery-execute-plan.md) — điều kiện vào: UF-04 spec đã xong (chỉ chặn FE mount màn; BE làm độc lập được). **Executor đọc cả spec + contracts.**

## 1 · Bối cảnh & hiện trạng (verify bằng lệnh thật khi mở phase, ghi kết quả vào đây)

```bash
cd backend && uv run pytest -q                      # kỳ vọng: suite Phase 11 xanh
curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8000/api/reviews/00000000-0000-0000-0000-000000000000   # 501 (stub admin.py)
grep -n "review_status" app/jobs/analysis_runner.py # kỳ vọng: KHÔNG match trong _process_item → gap thật
```

| Thành phần | Trạng thái lúc viết plan | Việc phase này |
|---|---|---|
| `POST /api/reviews/{feedback_id}` | STUB 501 `app/api/routes/admin.py:30` | Thay bằng route thật |
| `POST /api/corrections/{feedback_id}` | STUB 501 `admin.py:38` | Thay bằng route thật |
| Runner `_process_item` | set `requires_human_review` nhưng **không** set `review_status` → row đủ điều kiện vẫn `unreviewed`, không vào được queue | Task 1 |
| Bảng `human_reviews`, `correction_examples` | Đã tạo migration 0003, chưa ai ghi | Task 3/4 ghi |
| LangGraph + checkpoint-postgres | Đã pin `pyproject.toml` (`langgraph>=1.2,<2`, `langgraph-checkpoint-postgres>=3.1,<3.2`) | Không thêm dep |
| Spike S5 quirks | Windows: async psycopg **bắt buộc SelectorEventLoop**; checkpoint write ~9s qua WAN Supabase | Task 3 mang pattern vào app |
| `classify_feedback(few_shot=…)` | Param sẵn từ v1 (`classifier.py:38`) | Stretch Task 7 wire |

## 2 · Mục tiêu pha + Non-goals

**Mục tiêu:** (1) runner đẩy row đủ điều kiện HITL thành `review_status='pending'`; (2) graph LangGraph nhỏ interrupt/resume với checkpoint Postgres SỐNG SÓT restart; (3) hai endpoint C3 production đúng contract; (4) edit/reject tự nuôi `correction_examples`; (5) evidence luận văn kill-restart-resume.

**Non-goals (chống scope creep):**
- Tự reclassify lại feedback sau edit/reject (few-shot chỉ có tác dụng lần classify SAU).
- Few-shot ĐỘNG theo từng feedback — stretch chỉ wire N example gần nhất tĩnh.
- FE màn review (FE-05, session FE sở hữu); đổi shape C3; CRUD human_reviews; endpoint liệt kê corrections.
- Migration mới — phase này KHÔNG đụng schema (4 bảng checkpoint do `saver.setup()` tạo, ngoài filter Alembic như cũ).

## 3 · Tasks

### Task 1 — Runner đánh dấu pending

**Files:** Modify `backend/app/jobs/analysis_runner.py` (_process_item ~line 109); Test `backend/tests/test_classifier_idempotency.py`

- [ ] Step 1.1: Viết test trước — case mới trong test idempotency: feedback có `pii_detected=True` (hoặc severity critical mock) sau khi chạy item phải `review_status == ReviewStatus.pending`; feedback thường phải giữ `unreviewed`.
- [ ] Step 1.2: Chạy `uv run pytest tests/test_classifier_idempotency.py -q` → FAIL (status vẫn `unreviewed`).
- [ ] Step 1.3: Sửa `_process_item` ngay sau dòng gán `requires_human_review`:
  ```python
  fb.review_status = (
      ReviewStatus.pending if fb.requires_human_review else ReviewStatus.unreviewed
  )
  ```
  (import `ReviewStatus` từ `app.models.enums`). Row đã classify trước đó KHÔNG bị đụng — runner chỉ xử lý row `categories IS NULL`.
- [ ] Step 1.4: Chạy lại → PASS. Commit: `feat(hitl): runner marks qualifying rows review_status=pending`

### Task 2 — Schemas request/response cho C3

**Files:** Create `backend/app/schemas/hitl.py`; Modify `backend/app/schemas/__init__.py`

- [ ] Step 2.1: `ReviewIn`: `action: Literal["approve","edit","reject"]`, `edited_content: str | None = None`, `reason: str | None = None`. Model_validator: `action=="edit"` mà `edited_content` rỗng/trống → raise ValueError (FastAPI tự trả **422**, đúng contract C3).
- [ ] Step 2.2: `CorrectionIn`: cả field optional — `categories: list[str] | None`, `ai_issue/severity/sentiment: <enum tương ứng> | None`, `note: str | None`. Validator: **ít nhất 1** nhãn khác None (rỗng toàn bộ → 422); phần tử `categories` validate thuộc taxonomy enums sẵn có (`schemas/taxonomy.py`) để không nhét string lạ vào JSONB.
- [ ] Step 2.3: `CorrectionOut(FeedbackOut)` thêm `correction_recorded: bool` — response phẳng đúng contract ("FeedbackOut cập nhật nhãn + correction_recorded").
- [ ] Step 2.4: Test thuần schema (không DB): edit thiếu nội dung → ValidationError; correction rỗng → ValidationError; approve kèm edited_content thừa → chấp nhận (bỏ qua). Verify: `uv run pytest tests/test_hitl_schemas.py -q` PASS. Commit: `feat(hitl): review/correction request schemas per C3`

### Task 3 — Graph HITL nhỏ + checkpoint

**Files:** Create `backend/app/services/hitl_graph.py`

State (TypedDict): `feedback_id`, `reviewer_id`, `snapshot` (dict nhãn+sanitized_content TRƯỚC review), `resume_payload` (action/edited_content/reason từ Command).

```text
[prepare_review] ─► interrupt(payload cho FE) ─► [apply_action] ─► [record_correction?] ─► END
```

- [ ] Step 3.1: `build_graph(checkpointer)` — node `prepare_review`: load Feedback theo id, chụp `snapshot` = `{categories, ai_issue, sentiment, severity, sanitized_content, pii_detected}` vào state, rồi `interrupt({"feedback": …tóm tắt labels…})`. Node `apply_action`: đọc resume payload; `approve` → `review_status=approved` (không đụng content); `edit` → chạy lại `presidio_service.sanitize(edited_content)` rồi GHI `sanitized_content/pii_detected/pii_entities` mới + `review_status=edited`; `reject` → `review_status=rejected` (content nguyên vẹn). Node `record_correction`: chỉ chạy khi action ∈ {edit, reject} — ghi 1 dòng `HumanReview` (original_value=snapshot, edited_value=labels/content sau, action, reason, reviewer_id) và 1 dòng `CorrectionExample` (original_prediction=snapshot labels, corrected_value=xem bảng dưới, reason).
- [ ] Step 3.2: **Ngữ nghĩa corrected_value** (chốt cứng để executor khỏi đoán): `edit` → nhãn GIỮ NGUYÊN từ snapshot, kèm `sanitized_content` mới (ví dụ dương text-mới/nhãn-cũ cho few-shot); `reject` → `corrected_value = {"categories": [], "ai_issue": null, "severity": null, "sentiment": null}` (tín hiệu âm "text này không có nhãn nào"). Lệch muốn đổi → entry decisions.md trước.
- [ ] Step 3.3: Checkpointer = `AsyncPostgresSaver` (chuỗi conn từ settings, session pooler như DB chính). Wrapper chạy-graph trong threadpool với loop SÁCH LỘC (S5 quirk — ProactorEventLoop mặc định làm psycopg nổ):
  ```python
  import asyncio, selectors

  def run_graph(coro_fn):
      return asyncio.run(
          coro_fn(),
          loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
      )
  ```
  Endpoint sync gọi `run_graph(lambda: ainvoke(...))` — không đụng event loop của uvicorn.
- [ ] Step 3.4: `thread_id = f"hitl-{feedback_id}"`. Flow mỗi request POST /reviews: `get_state(config)` → nếu thread chưa tồn tại: `ainvoke({feedback_id, reviewer_id}, config)` chạy tới interrupt; nếu đang interrupted (case resume sau crash): bỏ qua bước invoke input. Sau đó LUÔN `ainvoke(Command(resume=payload), config)`. Thread completed mà vẫn nhận POST → **409** (đã review).
- [ ] Step 3.5: Lifespan trong `app/main.py`: gọi `await saver.setup()` một lần lúc boot (idempotent — tái tạo 4 bảng checkpoint nếu thiếu; Alembic ignore-filter giữ nguyên, verify `alembic history` không thấy bảng lạ).
- [ ] Step 3.6: Unit test mock hoàn toàn (không DB thật): fake checkpointer in-memory, assert approve không sửa content; edit gọi sanitize + đổi status; reject ghi corrected_value rỗng. Verify: `uv run pytest tests/test_hitl_graph_unit.py -q` PASS. Commit: `feat(hitl): langgraph interrupt/resume graph with postgres checkpointer`

### Task 4 — Routes production thay stub

**Files:** Create `backend/app/api/routes/review.py`; Modify `backend/app/api/routes/admin.py` (xoá 2 stub reviews/corrections, GIỮ 3 stub còn lại), `backend/app/main.py` (include router)

- [ ] Step 4.1: Router `prefix="/api", tags=["hitl"], dependencies=[Depends(require_role("pm", "operations"))]` — guard router-level y hệt `routes/feedback.py:37-41`.
- [ ] Step 4.2: `POST /reviews/{feedback_id}`: load Feedback (404 nếu thiếu; **409 nếu `review_status != pending`**); gọi flow Task 3.4; commit session; trả `FeedbackOut` model_validate(row) — status giờ là approved/edited/rejected.
- [ ] Step 4.3: `POST /corrections/{feedback_id}`: 404 nếu thiếu; **409 nếu `categories is None`** (marker "chưa classify" — quy ước runner); apply trực tiếp KHÔNG qua graph (sửa nhãn là thao tác thuần DB): cập nhật các nhãn có trong body, ghi `CorrectionExample` + `human_reviews(action=edit, reason=note)`, trả `CorrectionOut(correction_recorded=True)`. Không phụ thuộc review_status — đúng C3.
- [ ] Step 4.4: Xoá 2 stub tương ứng trong `admin.py` (docstring stub còn 3 cái clusters/insights/reports — DoD cũ yêu cầu "còn nguyên" đã hết hiệu lực từ khai báo delivery, ghi chú dòng này vào decisions nếu cần).
- [ ] Step 4.5: Integration test `-m integration` (`tests/test_hitl_flow_integration.py`): seed feedback pending (external_ref prefix `hitl-it-` để dọn sạch sau), gọi cả 3 action qua `client` với cookie login pm; assert response + row `human_reviews`/`correction_examples` + `review_status`; cleanup theo prefix. Verify: `uv run pytest -m integration tests/test_hitl_flow_integration.py -v` PASS (cần Supabase + internet). Commit: `feat(hitl): POST reviews/corrections endpoints replace 501 stubs`

### Task 5 — Wire few-shot stretch [TUỲ CHỌN — bỏ được khi trễ]

**Files:** Modify `backend/app/jobs/analysis_runner.py`

- [ ] Step 5.1: Trong `_process_item` trước khi classify: query tối đa `N=5` `CorrectionExample` mới nhất, map thành `[{"text": ex.original_prediction["sanitized_content"] hoặc snapshot text, "label": ex.corrected_value}]` truyền vào `classify_feedback(..., few_shot=examples)`. Chỉ bật khi env `CLASSIFY_FEWSHOT_ENABLED=true` (default false — chi phí token tăng).
- [ ] Step 5.2: Unit test mock LLM assert prompt chứa khối "Ví dụ:" khi enabled. Commit: `feat(hitl): static few-shot wiring from recent corrections (stretch)`

### Task 6 — Evidence luận văn + docs

**Files:** Create `docs/evidence/hitl-checkpoint-resume.md` (thủ tục + screenshot chỗ trống); Modify `docs/api-notes.md` (đổi 2 dòng 501 → endpoint thật)

- [ ] Step 6.1: Thủ tục chụp bằng chứng (checkpoint SỐNG SÓT restart): seed 1 row pending → `POST /reviews` với body hợp lệ NHƯNG ngắt process giữa interrupt và resume (Ctrl+C server ngay sau khi log "interrupted") → khởi động lại server → POST lại cùng body → 200 và row `human_reviews` xuất hiện ĐÚNG 1 lần (không duplicate — bằng chứng resume-no-duplicate của S5 ở scale production). Chụp: log 2 phiên, SQL `SELECT * FROM human_reviews`.
- [ ] Step 6.2: Cập nhật `docs/api-notes.md` bảng endpoint (501 → 200 + role). Commit: `docs(hitl): checkpoint-resume evidence procedure + api notes`

## 4 · Acceptance criteria + Evidence cần chụp

- [ ] Runner đẩy row đủ điều kiện sang `pending` (test idempotency chứng minh, cả 2 nhánh)
- [ ] `POST /api/reviews/{feedback_id}`: approve/edit/reject đúng C3; edit thiếu content → 422; review lặp → 409; sai/quên quyền → 401/403
- [ ] `POST /api/corrections/{feedback_id}`: body rỗng → 422; feedback chưa classify → 409; response có `correction_recorded: true`
- [ ] Edit/reject sinh ĐÚNG 1 dòng `human_reviews` + `correction_examples` (ngữ nghĩa corrected_value §3.2)
- [ ] `edited_content` đi qua Presidio TRƯỚC khi lưu — raw do người dùng gõ không bao giờ lưu thẳng (test assert `pii_detected` cập nhật)
- [ ] Kill-restart-resume không mất state, không duplicate record (§3.6.1) — **evidence số 1 cho chương kết quả**
- [ ] Suite unit xanh offline (`uv run pytest -q`); integration PASS khi có mạng
- [ ] Không response nào chứa `raw_content` hay text chưa sanitize (grep schema + test)

## 5 · Blocker rule

Fail sau nỗ lực hợp lý (đặc biệt: checkpoint × pooler quirk mới, SelectorEventLoop xung đột middleware) → STOP task đó, entry dated `decisions.md`, fallback đã định sẵn trong spec §8: **review-không-graph** (apply trực tiếp kiểu corrections endpoint + vẫn ghi human_reviews; demo bằng chứng checkpoint dùng lại script S5) — chuyển việc độc lập khác (14-clusters) trong khi chờ quyết.
