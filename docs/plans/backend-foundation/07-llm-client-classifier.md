# Phase 07 — LLM Client · Classifier · Tracing

> **Nguồn:** execute-plan §1 (LLM, Structured output, HITL trigger, Observability) + §7 contracts + DoD mục 5 (một phần), 7
> **Trạng thái:** ⬜ · **Blocked by:** Phase 03 + `.env` có key LLM thật; kết quả spike S2 chọn mode mặc định
> **Commit mẫu:** `feat(llm): structured chat client with fallback chain, classifier v1, tracing`

## 1 · Mục tiêu

Module duy nhất gọi LLM chat (`llm_client`) với chuỗi fallback cấu trúc đầu ra đã khóa: `json_schema` → prompt-JSON + Pydantic validate → 1 retry kèm lỗi validate. Classifier prompt v1 gắn rubric severity + công thức HITL. Mọi call được log vào bảng `llm_call_logs` + trace Langfuse (EU) — chỉ với text ĐÃ sanitize.

Contracts khóa (§7):
```python
def chat_structured(system: str, user: str, schema: type[BaseModel]) -> BaseModel
def classify_feedback(sanitized_text: str, few_shot: list[dict] | None = None) -> Classification
```

## 2 · Việc CON NGƯỜI

- `.env` có `LLM_BASE_URL/API_KEY/MODEL` thật (từ Phase 01). Không key → phase này code xong nhưng chỉ verify bằng mock.

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 Taxonomy — `app/schemas/taxonomy.py`
- Enums Python khớp TUYỆT ĐỐI enum DB của Phase 03 (ai_issue / sentiment / severity).
- `Classification(BaseModel)`:
  ```python
  categories: list[str]          # 1..n nhãn chủ đề tự do theo prompt
  ai_issue: AiIssue | None
  sentiment: Sentiment
  severity: Severity
  safety_issue: bool             # cần cho HITL formula — thêm field này vào output schema
  confidence: float [0..1]
  rationale: str                 # ngắn ≤ 2 câu
  ```
  (Field `safety_issue` không có cột riêng trên `feedbacks` — lưu trong `categories`/đánh dấu qua `pii_detected`? KHÔNG: giữ trong rationale là mất dữ liệu. Quyết định đề xuất: thêm cột `safety_issue bool default false` vào `feedbacks` bằng migration nhỏ → **entry decisions.md** vì lệch §6. Công thức HITL cần nó nên phải lưu.)

### 3.2 Tracing — `app/services/tracing.py`
- Langfuse v3: client singleton, khởi tạo nếu `settings.LANGFUSE_TRACING_ENABLED` và đủ key; kill-switch env=false → mọi wrapper thành no-op.
- Wrapper `trace_llm_call(name, input_text_sanitized, output_summary, usage, latency_ms, error=None)` tạo span/generation.
- Writer `write_llm_call_log(session, *, analysis_run_id?, feedback_id?, call_type, prompt_version, model, latency_ms, prompt_tokens?, completion_tokens?, error?)` — INSERT bảng `llm_call_logs`. Bảng Postgres là bằng chứng vĩnh viễn độc lập vendor (quyết định đã khóa).
- `flush()` gọi ở lifespan shutdown thay cho `langfuse.shutdown()`.

### 3.3 Client — `app/services/llm_client.py`
- OpenAI SDK: `OpenAI(base_url=settings.LLM_BASE_URL, api_key=settings.LLM_API_KEY)`, `temperature=0`.
- `chat_structured(system, user, schema, *, feedback_id=None, analysis_run_id=None) -> BaseModel`:
  1. **Mode A** `response_format={"type":"json_schema", "json_schema": {name, strict:true, schema}}`;
  2. lỗi provider (400/reject/timeout JSON hỏng) → **Mode B**: system + user + "Trả về CHỈ một JSON object hợp lệ khớp schema sau: …" → strip code fence → parse → Pydantic validate;
  3. ValidationError → retry MỘT lần, append "JSON trước sai lỗi: …";
  4. vẫn fail → raise `LLMStructureError`.
- Sau MỖI call (kể cả call lỗi): đo latency, lấy `usage`, ghi `llm_call_logs` + langfuse generation; set module state `_structured_output_mode` ("json_schema" | "prompt_json") cho `/api/health` hiển thị.
- **Assert/docstring: `user`/`system` PHẢI là text đã sanitize** — client không nhận raw bao giờ.

### 3.4 Classifier — `app/services/classifier.py`
- `PROMPT_VERSION="v1"` ghi trong code + system prompt tiếng Việt rõ ràng:
  - vai trò: phân loại feedback sản phẩm AI, văn phong VI trộn EN kỹ thuật;
  - định nghĩa severity rubric:
    - `low`: phiền nhỏ, thẩm mỹ, wording;
    - `medium`: ảnh hưởng trải nghiệm một phần;
    - `high`: chặn tính năng chính, mất dữ liệu tạm thời;
    - `critical`: an toàn/bảo mật, mất dữ liệu thật, pháp lý, nội dung độc hại;
  - yêu cầu tự đánh giá `confidence` và tách `safety_issue`.
- `classify_feedback(sanitized_text, few_shot=None) -> Classification`: dựng messages (+ few-shot examples nếu truyền — param tồn tại bây giờ, loop correction sẽ cắm vào sau); gọi `chat_structured`; validate range confidence.
- Helper `compute_requires_human_review(classification, pii_detected) -> bool` đúng công thức §1:
  `severity=="critical" OR safety_issue OR pii_detected OR confidence < settings.CLASSIFY_CONFIDENCE_REVIEW_BELOW`
  - ⚠️ `HIGH_SEVERITY_CONFIDENCE_REVIEW_BELOW=0.75` plan chưa nói dùng chỗ nào — đề xuất: `severity in {high, critical} AND confidence < 0.75` cũng đẩy review. Chốt ý này bằng entry decisions.md khi làm.

### 3.5 Health mở rộng — sửa `/api/health`
- Trả thêm `{"db": "ok|error", "structured_output_mode": "...", "llm_model": ..., "embedding_model": ...}` (DB check `SELECT 1`).

### 3.6 Tests — `backend/tests/test_classifier_unit.py` (mock, không network)
- FakeLLMClient trả JSON cố định → classification đầy đủ; compute HITL phủ từng nhánh công thức (critical/safety/pii/confidence thấp);
- fallback chain: fake lần 1 ném lỗi format → lần 2 ok (Mode B đi được);
- 2 lần fail → `LLMStructureError`;
- llm_call_logs row được ghi với đúng call_type/prompt_version (dùng DB test).

## 4 · Tiêu chí nghiệm thu

| Mục tiêu | Bằng chứng |
|---|---|
| chat_structured hoạt động mode thật trên provider | chạy smoke script 1 câu |
| Fallback chain chứng minh được | test mock |
| HITL formula đúng từng nhánh | test |
| llm_call_logs ghi mỗi call | query DB |
| Langfuse trace xuất hiện trên dashboard EU, input CHỈ sanitized | inspect 1 trace thủ công |
| Kill switch: `LANGFUSE_TRACING_ENABLED=false` → không trace, app vẫn chạy | test env |

## 5 · Lệnh kiểm chứng

```powershell
cd backend
uv run pytest tests/test_classifier_unit.py
uv run python -c "from app.services.classifier import classify_feedback; print(classify_feedback('App dịch sai hoàn toàn đoạn văn quan trọng, tôi bị mất công trình lại từ đầu'))"
# kỳ vọng: severity high/critical, confidence >0, rationale tiếng Việt
# rồi check trace trên Langfuse dashboard + SELECT * FROM llm_call_logs ORDER BY created_at DESC LIMIT 1;
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| Provider không hỗ trợ json_schema hoàn toàn | Mode B mặc định (S2 đã dự báo), entry ghi evidence |
| Thêm cột `safety_issue` vào feedbacks | Entry bắt buộc (lệch §6) kèm migration |
| Cách dùng HIGH_SEVERITY threshold khác đề xuất | Entry dated trước khi code |
| Prompt v1 kém trên sample thật (severity lệch) | Đổi sang PROMPT_VERSION=v2 — KHÔNG sửa v1; version hóa để so sánh |
