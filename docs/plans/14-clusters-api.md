# Phase 14 — Clustering engine + GET /api/clusters + POST /api/clusters/run

> **Nguồn:** [`delivery-design-spec.md`](delivery-design-spec.md) §5 P3 + §3 C1/C5 + "Migration duy nhất" · [`delivery-contracts.md`](delivery-contracts.md) C1/C5 · spike S4 (`decisions.md` 2026-08-24/25: sklearn HDBSCAN cosine PASS 3/3 cụm, noise ~8%, 0.165s) · Ngày viết: 2026-08-25 (viết sớm theo decisions cùng ngày)
> **Thứ tự pha:** P3 của [delivery-execute-plan.md](delivery-execute-plan.md) — chạy SAU P2 hoặc song song nếu Task 1 migration xong trước graph HITL chạm DB. **Executor đọc cả spec + contracts.**

## 1 · Bối cảnh & hiện trạng (verify bằng lệnh thật khi mở phase, ghi kết quả)

```bash
cd backend
uv run alembic history | head -3        # head hiện tại là baseline phase 03 (+0003 future tables)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/clusters          # 501 stub
uv run --with scikit-learn python -c "import sklearn; print(sklearn.__version__)"  # smoke lib có resolve được
psql-ish check qua Supabase Studio: bảng clusters rỗng, feedbacks chưa có cột cluster_id
```

| Thành phần | Trạng thái | Việc phase này |
|---|---|---|
| Bảng `clusters` | Đã tạo (migration 0003), rỗng, đủ cột trend | Chỉ INSERT từ service |
| `feedbacks.cluster_id` | **CHƯA TỒN TẠI** — membership không có chỗ lưu | Migration DUY NHẤT cả giai đoạn delivery |
| Embedding | 22 row demo đã có `(text-embedding-3-small, 1536)` từ run `9c6687bc` | Input chính của engine |
| Lib clustering | sklearn chỉ spike-only ad-hoc (`uv run --with`), KHÔNG nằm pyproject | Task 1 pin + entry decisions (dep ngoài danh sách §1 — quy tắc 00-index §3.7) |
| LLM naming | `chat_structured` Mode A/B sẵn; `LlmCallType.name_cluster` sẵn trong enum nhưng CHƯA ai gọi | Task 4 |

## 2 · Mục tiêu pha + Non-goals

**Mục tiêu:** (1) migration thêm `feedbacks.cluster_id`; (2) `services/clustering.py` HDBSCAN cosine tái dùng bằng chứng S4; (3) đặt tên/mô tả cụm bằng đúng 1 LLM call mỗi lần run; (4) `POST /api/clusters/run` idempotent trong 1 transaction; (5) `GET /api/clusters` đúng C1 kèm sample ids cho FE link chi tiết.

**Non-goals:** phân trang/lọc clusters (dataset ≤1500); CRUD cluster; ANN pgvector (lùi đường đã ghi spec §6); gán lại nhãn feedback thủ công; chạy nền/tự động định kỳ — trigger là nút tay `/run`.

## 3 · Tasks

### Task 1 — Pin scikit-learn + migration `feedbacks.cluster_id`

**Files:** Modify `backend/pyproject.toml`, `backend/app/models/feedback.py`; Create `backend/alembic/versions/0004_feedback_cluster_id.py`; `docs/decisions.md` (entry dated)

- [x] Step 1.1: Entry decisions TRƯỚC: chốt **scikit-learn** làm lib clustering production (lý do: S4 đã chứng minh API + hiệu năng trên đúng metric cosine; `hdbscan` package gốc không mang thêm giá trị nào cho dataset ≤1500 mà tăng rủi ro wheel Windows; phiên pin `scikit-learn>=1.9,<2`). Đây là dep ngoài danh sách §1 — bắt buộc log theo quy tắc 00-index §3.7.
- [x] Step 1.2: Thêm `"scikit-learn>=1.9,<2"` vào pyproject (nhóm LLM/graph, kèm comment dẫn decisions). Verify: `uv sync` sạch, `uv run python -c "from sklearn.cluster import HDBSCAN"` OK.
- [x] Step 1.3: Model `Feedback` thêm:
  ```python
  cluster_id: Mapped[uuid.UUID | None] = mapped_column(
      ForeignKey("clusters.id"), nullable=True
  )
  ```
- [x] Step 1.4: Revision thường `0004_feedback_cluster_id`: `op.add_column("feedbacks", sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=True))` + `op.create_foreign_key(...)` + `op.create_index("ix_feedbacks_cluster_id", ...)`. KHÔNG đụng bảng checkpoint (filter Alembic giữ nguyên).
- [x] Step 1.5: Verify: `uv run alembic upgrade head` trên Supabase dev → `\d feedbacks` thấy cột + index; `alembic downgrade -1` rồi `upgrade head` lại được (reversible). Commit: `feat(db): pin scikit-learn, add feedbacks.cluster_id (single delivery migration)`

### Task 2 — Settings + công thức trend (chốt cứng mọi hằng số)

**Files:** Modify `backend/app/core/config.py`

Thêm vào `Settings` (mỗi biến một dòng, default ghi rõ):
- `CLUSTER_MIN_SIZE: int = 10` — `min_cluster_size` HDBSCAN (S4 chứng minh 10 nằm giữa sweep {5,10,15} đều ra đúng cụm)
- `CLUSTER_WINDOW_DAYS: int = 30` — cửa sổ "hiện tại"
- `CLUSTER_SPIKE_RATIO: float = 2.0` và `CLUSTER_SPIKE_MIN_CURRENT: int = 5`
- `CLUSTER_EMERGING_MIN: int = 3`

**Công thức chuẩn (executor copy nguyên xi, không tự chế):**
- `current_count` = số member `created_at ∈ [now−W, now]`; `previous_count` = member `∈ [now−2W, now−W)`; W = `CLUSTER_WINDOW_DAYS`.
- `first_seen/last_seen` = min/max `created_at` toàn bộ member; `feedback_count` = tổng member.
- `growth_ratio` = `round(current/previous, 2)` khi `previous > 0`; khi `previous == 0`: `9.99` nếu `current > 0` còn `0.0` nếu không (chặn inf ra JSON).
- `is_spike` = `previous > 0 AND current ≥ CLUSTER_SPIKE_MIN_CURRENT AND current/previous ≥ CLUSTER_SPIKE_RATIO`.
- `is_emerging` = `previous == 0 AND current ≥ CLUSTER_EMERGING_MIN` (cụm hoàn toàn mới).
- `suggested_priority` (0..1) = `0.5·min(feedback_count/50, 1) + 0.3·(1 nếu is_spike hoặc is_emerging) + 0.2·(tỉ lệ member severity ∈ {high, critical})`, làm tròn 2 chữ số. (Scale này là lựa chọn v1 có lý do rõ — đổi sau phải qua decisions.)
- Verify: unit test thuần hàm `compute_trend(members, now, settings)` với fixture ngày giả lập phủ cả 4 nhánh (spike/emerging/ratio bình thường/cũ xa). Commit: `feat(clustering): trend constants + canonical window formulas`

### Task 3 — Engine `services/clustering.py`

**Files:** Create `backend/app/services/clustering.py`

- [ ] Step 3.1: `load_embedded(db) -> tuple[list[Feedback], np.ndarray]`: SELECT feedbacks `embedding IS NOT NULL`; vector stack thành matrix float32. Row thiếu embedding bị loại — trả kèm `excluded_count` (contract C5 bắt buộc báo).
- [ ] Step 3.2: `labels = HDBSCAN(metric="cosine", min_cluster_size=settings.CLUSTER_MIN_SIZE).fit_predict(X)`; label `-1` = noise → không gán cụm (giữ `cluster_id=NULL`, đếm vào unassigned).
- [ ] Step 3.3: Naming LLM — **1 call duy nhất mỗi run** (kiềm chế tín dụng): gom tối đa 5 snippet đại diện/cụm (member `confidence` cao nhất, cắt 200 ký tự TỪ `sanitized_content`) → `chat_structured(NAMING_PROMPT, payload, NamingOut, call_type=LlmCallType.name_cluster)` với `NamingOut = {clusters: [{idx, name ≤80 ký tự, summary ≤300}]}`. Fallback KHÔNG tốn LLM: cụm nào LLM bỏ sót → `name=f"Cụm #{idx}"`, `summary` ghép từ top categories của cụm.
- [ ] Step 3.4: Hàm tổng `run_clustering(db, settings) -> ClusteringRunStats` thực thi đúng thứ tự idempotent C5 **trong 1 transaction**:
  1. `DELETE FROM insights` (trước vì FK trỏ clusters) → 2. `DELETE FROM clusters` → 3. `UPDATE feedbacks SET cluster_id = NULL` → 4. INSERT cluster mới (trend theo Task 2 + name/summary Task 3) → 5. `UPDATE feedbacks SET cluster_id` cho member không phải noise → commit.
- [ ] Step 3.5: Unit test: ma trận embedding giả lập 2 cụm + noise (seed cố định), mock `chat_structured` → assert số cụm, noise không có cluster_id, excluded_count đếm row thiếu vector, stats khớp. Mock LLM fail → fallback name vẫn đủ. Verify: `uv run pytest tests/test_clustering_unit.py -q` PASS. Commit: `feat(clustering): hdbscan cosine engine with llm naming and idempotent rebuild`

### Task 4 — Hai endpoint thay stub

**Files:** Modify `backend/app/api/routes/admin.py` (xoá stub `/clusters`, router dependencies guard như feedback router), Create `backend/app/schemas/cluster.py`

- [ ] Step 4.1: `POST /api/clusters/run` (sync def — threadpool của FastAPI đủ cho ≤1500 row): gọi `run_clustering`, trả `{clusters_upserted, assigned_count, unassigned_count, duration_ms}` (đo `perf_counter`). Lỗi giữa chừng → rollback + 500 chuẩn, DB về trạng thái cũ (transaction bảo đảm).
- [ ] Step 4.2: `GET /api/clusters?sort=growth_ratio|recent` (default `feedback_count` giảm dần; `recent` = `last_seen` giảm): trả C1 nguyên vẹn — gồm `sample_feedback_ids` = ≤5 id member mới nhất (1 query phụ group-by, hoặc window function). Chưa từng run → `{"items": []}` 200.
- [ ] Step 4.3: Integration test `-m integration` (`tests/test_clusters_api_integration.py`): dùng 22 row demo đã có embedding → `POST /api/clusters/run` 200, số liệu hợp lệ (`assigned + unassigned == tổng row có embedding`) → `GET /api/clusters` shape C1 từng field → **rerun lần 2**: `clusters_upserted` ổn định, không nhân bản row (idempotence thật trên Supabase). Verify: `uv run pytest -m integration tests/test_clusters_api_integration.py -v` PASS. Commit: `feat(clustering): clusters run + list endpoints replace 501 stub`

## 4 · Acceptance criteria + Evidence cần chụp

- [ ] `feedbacks.cluster_id` tồn tại + index; revision reversible; 4 bảng checkpoint vẫn ngoài Alembic
- [ ] Rerun `/clusters/run` không sinh duplicate, insight cũ bị xoá sạch (nền cho P4)
- [ ] Noise `-1` và row chưa embed nằm hết trong `unassigned_count`, không bị gán bừa
- [ ] Không snippet nào trong prompt naming đến từ `raw_content` (test assert payload chỉ chứa sanitized)
- [ ] `llm_call_logs` ghi đúng 1 dòng `name_cluster` mỗi run (kể cả fallback — call thất bại cũng phải được log bởi `_record_attempt` sẵn có)
- [ ] GET shape khớp C1 100% field-by-field; sort 3 chế độ đúng thứ tự
- [ ] **Evidence luận văn:** screenshot trang Supabase Studio bảng clusters có name tiếng Việt + JSON response `/api/clusters` trên data demo 22 row; số liệu duration_ms đưa vào chương kết quả

## 5 · Blocker rule

HDBSCAN trên data thật ra 1 cụm duy nhất hoặc noise >50% (khác hẳn toy S4) → thử sweep `CLUSTER_MIN_SIZE` {5, 8, 10, 15} trong 1 script evidence; vẫn tệ → STOP, entry decisions (kèm JSON kết quả), fallback tạm: gán theo similarity threshold cosine ≥0.85 quanh medoid (ghi rõ là fallback, không phải quyết định cuối). Lỗi khác sau nỗ lực hợp lý → STOP task, chuyển việc độc lập (16-reports — thuần SQL, không phụ thuộc task nào của phase này).
