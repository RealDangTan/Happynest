# Phase 09 — Analysis Runner (batch idempotent) + Progress API

> **Nguồn:** execute-plan §7 (jobs + routes analysis) + DoD mục 5
> **Trạng thái:** ✅ 2026-08-25 · **Blocked by:** Phase 06, 07, 08
> **Commit mẫu:** `feat(analysis): idempotent batch runner, run progress endpoints`

## 1 · Mục tiêu

Job batch chạy nền: với mỗi feedback chưa xử lý → classify → tính `requires_human_review` → embed → UPDATE row. **Idempotent/resumable**: crash giữa chừng, chạy lại không nhân đôi công việc. API tạo run + theo dõi tiến độ.

Contract khóa (§7):
```python
def run_analysis(run_id: uuid) -> None
# picks feedbacks WHERE analysis_run_id IS NULL, per item: classify ->
# requires_human_review -> embed -> UPDATE; processed_count mỗi item; commit per item
```

## 2 · Việc CON NGƯỜI

- Không có. (Chạy thật tốn LLM tokens — số lượng lớn nên cân nhắc chi phí; 20 rows test là đủ DoD.)

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 Job — `app/jobs/analysis_runner.py`
- Tạo session RIÊNG của job (không dùng session request).
- Tạo run: `POST /api/analysis/runs` insert row `analysis_runs` snapshot cấu hình: `pipeline_version` (hằng code), `llm_model`, `prompt_version`, `embedding_model`, `status=running`, `total_count = count(feedbacks WHERE analysis_run_id IS NULL)`.
- Vòng lặp từng item (SELECT tiếp 1 row `WHERE analysis_run_id IS NULL ORDER BY created_at`):
  1. Claim ngay: `UPDATE feedbacks SET analysis_run_id=:run_id` (+commit) — crash sau claim vẫn resume được vì vòng sau chỉ nhận row chưa claim;
  2. Xử lý item (labels đang NULL): classify từ `sanitized_content` (nếu NULL sanitize chưa chạy → chạy `sanitize(raw)` tại chỗ cho chắc);
  3. `compute_requires_human_review` → set `requires_human_review`;
  4. `embed_one(sanitized)` + `store_embedding`;
  5. `processed_count += 1` trên run;
  6. **Commit từng item** (crash-safe). Lỗi MỘT item (`LLMStructureError`, embedding fail) → ghi error summary vào run, KHÔNG chết cả batch; item lỗi bỏ qua (đã claim nên không retry trong run này).
- Kết thúc: `status=completed|failed`, `completed_at=now()`.
- Chạy nền qua FastAPI `BackgroundTasks` (đủ cho quy mô thesis; KHÔNG Celery/queue — ngoài scope).

### 3.2 Routes — `app/api/routes/analysis.py`
| Endpoint | Ý nghĩa |
|---|---|
| `POST /api/analysis/runs` | role pm\|operations; tạo run + `BackgroundTasks.add_task(run_analysis, run.id)`; trả `{run_id}` ngay |
| `GET /api/analysis/runs/{id}` | `{status, processed_count, total_count, error}` — progress |
| `GET /api/analysis/runs/{id}/results` | paginated feedbacks thuộc run: labels + severity + confidence + requires_human_review |

### 3.3 Tests — `backend/tests/test_classifier_idempotency.py` (mock LLM/embedder)
- FakeLLM/FakeEmbedder deterministic; seed 10 feedbacks;
- Chạy runner "vụng": giả lập crash sau item 4 (raise trong fake tại call thứ 5) → run status failed, 4 items có labels;
- Gọi lại `run_analysis` (run mới hoặc resume cùng run — chọn 1 cách, ghi rõ) → 6 items còn lại xử lý, 4 items cũ KHÔNG bị classify lại (assert bằng counter call fake LLM tổng đúng = 10, không phải 14);
- `requires_human_review` đúng công thức trên các item mock;
- processed_count monotonic.

## 4 · Tiêu chí nghiệm thu (map DoD mục 5)

| DoD | Bằng chứng |
|---|---|
| 1 full run trên 20 rows hoàn tất: labels + severity + confidence + review flag + embeddings(model+dim) | curl results + query DB |
| Crash mid-run → re-run resumes KHÔNG trùng lặp | test idempotency |
| Progress endpoint phản ánh đúng processed/total | poll GET run |

## 5 · Lệnh kiểm chứng

```powershell
cd backend
uv run pytest tests/test_classifier_idempotency.py
# end-to-end thật (20 rows đã ingest):
curl -s -X POST http://localhost:8000/api/analysis/runs -b cookie.txt
curl -s http://localhost:8000/api/analysis/runs/<run_id> -b cookie.txt   # poll đến completed
curl -s "http://localhost:8000/api/analysis/runs/<run_id>/results?limit=5" -b cookie.txt
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| BackgroundTasks bị kill khi uvicorn reload (Windows quirk §10.2) | Đó là lý do rule "reload chạy riêng terminal"; nếu vẫn vướng → chạy job bằng script CLI thay API trigger, entry nhỏ |
| Item lỗi quá nhiều (>50% batch) | Dừng sớm run status=failed kèm error; entry nếu đổi ngưỡng |
| Cần nhiều worker song song | NGOÀI scope — single worker tuần tự đủ ≤1500 rows; entry chỉ khi buộc đổi |
