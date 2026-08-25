# Phase 18 — Agent toolbox: 5 tool deterministic sau lưng router

> **Nguồn:** brainstorm agent-module 2026-08-25 + decisions 2026-08-26 · tái dùng services có sẵn (classifier/embedder/clustering) — toolbox là LỚP BAO ĐỒNG NHẤT QUÁN, không viết lại logic · Ngày viết: 2026-08-26
> **Thứ tự pha:** P6-B của [delivery-execute-plan.md](delivery-execute-plan.md) — điều kiện cứng: **17 ✅** (schema + data demo) và **phase 14 Task 3–4 ✅** (`services/clustering.py` tồn tại, công thức trend canonical nằm ở đó). **Executor đọc thêm contracts C1/C2 (shape metrics/evidence).**

## 1 · Bối cảnh & hiện trạng (verify bằng lệnh thật khi mở phase, ghi kết quả)

```bash
cd backend
ls app/services/clustering.py && grep -n "def compute_trend\|def run_clustering" app/services/clustering.py   # hàm trend nằm đâu, chữ ký gì
uv run pytest -q                    # xanh trước khi đụng
curl -s http://127.0.0.1:8000/api/clusters -b cookie.txt | head -c 400   # data demo phase 17 đã có cụm
```

| Thành phần | Trạng thái | Việc phase này |
|---|---|---|
| classify/embed | `services/classifier.py`, `services/embedder.py` ổn định từ phase 07/08 | Wrap mỏng |
| Trend math | `compute_trend(...)` canonical trong `clustering.py` (commit `171f094`) | **Import dùng lại — CẤM copy công thức** |
| pgvector kNN | Pattern `/feedbacks/{id}/similar` (phase 08): brute-force `ORDER BY embedding <=> :q` | Áp sang bảng insights |
| `insights.embedding` | Đã có từ migration 0007, đang NULL toàn bộ | Backfill script |

## 2 · Mục tiêu pha + Non-goals

**Mục tiêu:** (1) package `app/agents/tools/` với đúng **5 tool**, mỗi tool một module, Pydantic in/out schema tường minh; (2) registry `TOOLS: dict[str, ToolSpec]` để graph (phase 19) dispatch bằng tra cứu tên; (3) script backfill embedding cho insight cũ; (4) unit test mocked phủ toàn bộ + assert biên PII.

**Bộ 5 tool (tên chuỗi là HỢP ĐỒNG với router phase 19 — đổi tên = sửa cả phase 19):**

| Tên tool | Việc | Nguồn logic |
|---|---|---|
| `classify_batch` | Classify các row chưa có labels của 1 run | wrap `classifier.classify_feedback` |
| `embed_batch` | Embed các row thiếu vector | wrap `embedder` |
| `get_cluster_metrics` | Số liệu + trend 1 cụm (member_count, growth_ratio, is_emerging/spike, severity_dist, top_categories ≤5) | query feedbacks theo cluster_id + import hàm trend từ clustering service |
| `fetch_evidence_quotes` | ≤8 snippet 200 ký tự cắt từ `sanitized_content`, ORDER confidence DESC NULLS LAST | thuần SQL |
| `retrieve_similar_insights` | kNN trên `insights.embedding`, trả kèm quyết định người (nếu có) | embedder + brute-force `<=>` |

**Non-goals:** router/graph (19); endpoint HTTP mới; ANN index (no-ANN đã lock v1.1); few-shot retrieval cho classifier (roadmap riêng); sửa bất kỳ service nào đang xanh.

## 3 · Tasks

### Task 1 — Khung `app/agents/tools/base.py`

**Files:** Create `backend/app/agents/__init__.py` (rỗng), `backend/app/agents/tools/__init__.py`, `backend/app/agents/tools/base.py`

- [ ] Step 1.1: Định nghĩa hợp đồng tool:
  ```python
  class ToolSpec(BaseModel):
      name: str
      description: str          # 1 câu tiếng Anh — router sẽ đọc description này để chọn
      input_model: type[BaseModel]
      output_model: type[BaseModel]

  def TOOLS() -> dict[str, ToolSpec]: ...   # gom registry từ 5 module con
  ```
  Mọi input schema bắt buộc có field `run_id: uuid.UUID` (để passthrough trace vào llm_call_logs khi tool chạm LLM).
- [ ] Step 1.2: Smoke test import registry KHÔNG LỖI lúc này (registry mới trả dict rỗng/partial — đóng đủ 5 tên ở Task 6). Commit: `feat(agents): tool spec contract and registry skeleton`

### Task 2 — Hai wrapper LLM: `classify_batch`, `embed_batch`

**Files:** Create `backend/app/agents/tools/classify_batch.py`, `backend/app/agents/tools/embed_batch.py`; Test `backend/tests/test_agent_tools_llm.py`

- [ ] Step 2.1: Input `{run_id, limit: int = 50}` → chọn feedback `analysis_run_id IS NULL OR categories IS NULL` LIMIT `limit` (đúng predicate resume phase 09), gọi classifier/embedder tuần tự với `feedback_id`/`analysis_run_id` passthrough (kwargs đã hỗ trợ từ entry 2026-08-25). Output `{processed, failed, skipped_ids}`.
- [ ] Step 2.2: Unit test mock hoàn toàn classifier/embedder (pattern fake trong `tests/` hiện hành): assert passthrough id đúng, item lỗi không chặn item kế. Verify: `uv run pytest tests/test_agent_tools_llm.py -q` PASS. Commit: `feat(agents): classify/embed batch tools wrapping existing services`

### Task 3 — `get_cluster_metrics`

**Files:** Create `backend/app/agents/tools/metrics.py`; Test `backend/tests/test_agent_tools_metrics.py`

- [ ] Step 3.1: Input `{run_id, cluster_id}` → Output model `ClusterMetricsOut`: `cluster_id, name, summary, member_count, first_seen, last_seen, current_count, previous_count, growth_ratio, is_emerging, is_spike, suggested_priority, severity_dist: dict[Severity|int], top_categories: list[{category,count}] ≤5`.
- [ ] Step 3.2: Nguồn số: đọc thẳng các cột trend ĐÃ tính của row clusters (phase 14 lưu sẵn) — tool KHÔNG tính lại trend; chỉ member_count/severity_dist/top_categories query live từ `feedbacks.cluster_id`. Cluster id lạ → raise `ValueError("cluster not found")` (graph biến thành observation lỗi, không crash).
- [ ] Step 3.3: Unit test DB-backed `-m integration` nhẹ (fixture tiền tố `agtool-`) hoặc thuần unit với session giả — khớp chiến lược conftest phase 11. Verify PASS. Commit: `feat(agents): cluster metrics tool reading stored trends`

### Task 4 — `fetch_evidence_quotes`

**Files:** Create `backend/app/agents/tools/evidence.py`; Test gộp `tests/test_agent_tools_metrics.py`

- [ ] Step 4.1: Input `{run_id, cluster_id, limit: int = 8}` → `EvidenceQuotesOut{quotes: [{feedback_id, snippet ≤200 ký tự, severity, created_at}]}`, ORDER BY `confidence DESC NULLS LAST, created_at DESC`. Snippet cắt TỪ `sanitized_content`; row `sanitized_content IS NULL` bị loại.
- [ ] Step 4.2: **Test canary PII (bắt buộc):** fixture row có `raw_content` chứa chuỗi `"RAW-CANARY-XYZ"` (không nằm trong sanitized) → assert chuỗi canary KHÔNG xuất hiện trong output dump. Đây là test khuôn cho mọi tool sau. Verify PASS. Commit: `feat(agents): evidence quotes tool with pii canary test`

### Task 5 — `retrieve_similar_insights` + backfill

**Files:** Create `backend/app/agents/tools/precedents.py`; Create `backend/scripts/backfill_insight_embeddings.py`; Test `backend/tests/test_agent_tools_precedents.py`

- [ ] Step 5.1: Backfill script: SELECT insights `embedding IS NULL` ORDER BY created_at DESC LIMIT env `INSIGHT_EMBED_BACKFILL_LIMIT` (default 200); text nhúng = `f"{title}. {summary}"`; ghi `embedding/embedding_model/embedding_dim` qua embedder service (đầy đủ triplet như feedbacks). Idempotent — chạy lại bỏ qua row đã có.
- [ ] Step 5.2: Tool input `{run_id, query_text, top_k: int = 3}` → embed query 1 lần → `SELECT ... WHERE embedding IS NOT NULL ORDER BY embedding <=> :query_vec LIMIT top_k` (brute-force, cùng pattern `/similar` phase 08). Mỗi kết quả kèm `human_decision`: JOIN-LATERAL dòng `insight_reviews` mới nhất (action + reason) nếu có — đây là điểm "precedent có kèm phán quyết người" của thiết kế. Output `{matches: [{insight_id, title, summary ≤300, similarity, human_decision | None}]}`.
- [ ] Step 5.3: Unit/integration test: seed 2 insight + embedding giả (vector cố định viết tay, không đốt embed API), query gần vector A → A rank 1 đúng thứ tự cosine; insight không review → `human_decision=None`. Verify: `uv run pytest tests/test_agent_tools_precedents.py -v -m integration` PASS. Commit: `feat(agents): precedent retrieval over insight embeddings with human decisions`

### Task 6 — Registry đóng gói

**Files:** Modify `backend/app/agents/tools/__init__.py`

- [ ] Step 6.1: `TOOLS()` trả đủ 5 ToolSpec theo đúng tên bảng §2; test assert `set(TOOLS()) == {"classify_batch","embed_batch","get_cluster_metrics","fetch_evidence_quotes","retrieve_similar_insights"}`. Commit: `feat(agents): close tool registry for router dispatch`

## 4 · Acceptance criteria + Evidence cần chụp

- [ ] `set(TOOLS())` đúng 5 tên; mỗi ToolSpec có description tiếng Anh 1 câu (router phase 19 đọc được)
- [ ] Trên data demo phase 17: `get_cluster_metrics(cụm Google-login)` trả `is_spike=true` + severity_dist hợp lệ; `fetch_evidence_quotes` đủ ≤8 quote chỉ từ sanitized
- [ ] Sau backfill: `SELECT count(*) FROM insights WHERE embedding IS NOT NULL` > 0; `retrieve_similar_insights` với query mô tả cụm Google-login trả insight đó trong top-k
- [ ] Canary test xanh — không tool nào đưa `raw_content` ra ngoài
- [ ] Suite cũ vẫn xanh (`uv run pytest -q`)
- [ ] **Evidence luận văn:** JSON output mẫu của metrics + precedents trên planted cluster (chụp vào file này mục §1)

## 5 · Blocker rule

Công thức trend trong `clustering.py` khác mô tả plan 14 (do executor phase 14 amend) → TUÂN THEO code thật, ghi chú lệch vào file này, không "sửa giúp". kNN `<=>` lỗi kiểu dữ liệu qua pooler (vector param bind) → cast `::vector` trong SQL text như spike S3 đã làm. Lỗi khác sau nỗ lực hợp lý → STOP task, entry decisions, chuyển Task độc lập kế tiếp (registry vẫn đóng được với 4/5 tool nhưng PHẢI ghi rõ tool thiếu vào handoff — phase 19 phụ thuộc đủ 5).
