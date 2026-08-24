# Phase 08 — Embedder · pgvector · Similarity

> **Nguồn:** execute-plan §1 (Vector, Embeddings) + §7 contracts + DoD mục 6
> **Trạng thái:** ⬜ · **Blocked by:** Phase 03 + key `EMBEDDING_MODEL` thật (spike S3 đã xác nhận model/dims)
> **Commit mẫu:** `feat(embedding): embedder service, vector storage, similar endpoint`

## 1 · Mục tiêu

Module DUY NHẤT gọi `/v1/embeddings` (`embedder`), lưu vector kèm `embedding_model` + `embedding_dim` mỗi row, endpoint cosine nearest-neighbor exact scan (không ANN index — dataset ≤1500 rows, quyết định đã khóa).

Contracts khóa (§7):
```python
def embed_texts(texts: list[str]) -> list[list[float]]   # batch ≤2048, retry backoff
def embed_one(text: str) -> list[float]
```

## 2 · Việc CON NGƯỜI

- Không có (key đã ở `.env`). Nếu provider đổi model → cập nhật env + entry.

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 Service — `app/services/embedder.py`
- Cùng pattern SDK như llm_client: `OpenAI(base_url, api_key)` → `client.embeddings.create(model=settings.EMBEDDING_MODEL, input=[...])`.
- `embed_texts`: chia batch **≤2048 input/call**; ghép kết quả đúng thứ tự; validate số chiều trả về == `settings.EMBEDDING_DIM`, lệch → raise `EmbeddingDimError`.
- Retry: `tenacity.retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(4))` trên call network (tenacity đã pre-approved).
- Mỗi call ghi `llm_call_logs` call_type=`embed` qua `tracing.py` (latency, usage nếu có).
- Input chỉ nhận text đã sanitize — cùng nguyên tắc với llm_client.

### 3.2 Storage helper
- `store_embedding(session, feedback, vector)` set đồng thời 3 cột: `embedding=vector`, `embedding_model=settings.EMBEDDING_MODEL`, `embedding_dim=len(vector)` (quyết định §1: luôn đi cùng model+dim).

### 3.3 Route similarity — sửa `routes/feedback.py`
- Thay stub 501 bằng:
  `GET /api/feedbacks/{id}/similar?k=5`
- Logic: load row `{id}` → thiếu embedding → 409 kèm message rõ; query:
  ```sql
  SELECT id, source, sanitized_content,
         1 - (embedding <=> :query_vec) AS score
  FROM feedbacks
  WHERE id <> :id AND embedding IS NOT NULL
  ORDER BY embedding <=> :query_vec
  LIMIT :k
  ```
  (exact scan, không tạo index — ghi comment ngay trong code lý do ≤1500 rows).
- Trả `[{id, score, source, snippet}]` (snippet = sanitized cắt ~200 ký tự).
- Guard `k` ∈ [1..50].

### 3.4 Tests
- Unit `test_embedder_unit.py`: FakeOpenAI trả vector giả → batch split đúng, thứ tự giữ nguyên, dim sai raise lỗi, log row ghi.
- Integration `test_similarity_roundtrip.py` (**marker `integration`**): insert N=5 feedback có embedding tay (vector cố định, ví dụ unit vectors dễ đoán), self/kề nhau rank đúng thứ tự kỳ vọng khi query similar.

## 4 · Tiêu chí nghiệm thu (map DoD mục 6)

| DoD | Bằng chứng |
|---|---|
| `/similar` trả neighbors có cosine score giảm dần | curl thật / test integration |
| Vector lưu kèm model+dim | query DB 3 cột |
| Không ANN index được tạo | Supabase Studio → Database → Indexes (chỉ PK/FK mặc định) |

## 5 · Lệnh kiểm chứng

```powershell
cd backend
uv run pytest tests/test_embedder_unit.py
uv run pytest -m integration tests/test_similarity_roundtrip.py   # cần PG
# end-to-end tay: ingest 2 câu tương tự nhau → chạy analysis (Phase 09) hoặc embed tay →
curl -s "http://localhost:8000/api/feedbacks/<id>/similar?k=3" -b cookie.txt
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| Provider embeddings trả dims ≠ env | `EmbeddingDimError` chặn sớm; đổi `EMBEDDING_DIM` + migration `VECTOR(n)` + re-embed toàn bộ — entry bắt buộc |
| Rate limit provider | tenacity backoff đã xử lý; nếu vẫn fail → entry + cân nhắc hạ batch size |
| Cosine distance operator `<=>` lỗi version pgvector | Kiểm tra extension version, entry nếu phải đổi cách tính |
