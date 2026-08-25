# Phase 17 — Agent substrate: migration 0007 + bộ dữ liệu demo

> **Nguồn:** brainstorm agent-module 2026-08-25 (transcript owner) + decisions 2026-08-26 (khai báo series 17–20) · RAG amendment: `insights.embedding` cho precedent retrieval · Ngày viết: 2026-08-26
> **Thứ tự pha:** P6-A của [delivery-execute-plan.md](delivery-execute-plan.md) — độc lập với 14/15/16 về code, CHỈ cần head migration ổn định. **Executor đọc thêm decisions 2026-08-26 trước khi làm.**

## 1 · Bối cảnh & hiện trạng (verify bằng lệnh thật khi mở phase, ghi kết quả vào đây)

```bash
cd backend
uv run alembic history | head -4     # kỳ vọng head = 0006_feedback_cluster_id (nếu đã trôi → chain revision xuống head THẬT)
uv run pytest -q                     # unit suite xanh trước khi đụng
grep -n "embedding" app/models/insight.py   # kỳ vọng: KHÔNG match → gap thật
psql-ish Supabase Studio: \dT llm_call_type → chưa có value 'route'/'critic'
```

| Thành phần | Trạng thái lúc viết plan | Việc phase này |
|---|---|---|
| Bảng `insights` | Có (`migration 0003`) — đủ title/summary/suggested_action/evidence_ids/review_status, **chưa có embedding** | Thêm 3 cột vector |
| `human_reviews` | Feedback-level (phase 13 đang ghi) | Giữ nguyên — audit INSIGHT-level cần bảng riêng |
| `action_drafts`, `insight_reviews`, `impact_checks` | **Chưa tồn tại** | Tạo mới |
| `LlmCallType` | 4 values: classify/embed/name_cluster/generate_insight (`enums.py:64-68`) | ADD VALUE `route`, `critic` |
| Data demo | 22 row (run `9c6687bc`) — không đủ cụm/trend để demo agent | Generator ~650 row |

> **Đồng bộ với decisions 2026-08-26 (phase 14 blocker):** data 22 row cho **100% noise / 0 cụm** (không có nhóm chủ đề dày đặc) — evidence "trang clusters hiện name tiếng Việt trên data thật" bị dời sang P5 chờ thêm data. Dataset planted của phase này CHÍNH là nguồn nhóm chủ đề đó (~50 row/chủ đề baseline + 40 emerging): sau Task 3, rerun `/api/clusters/run` phải cho ≥2 cụm thật — dùng luôn làm bằng chứng P5, một mũi tên hai đích.

**Quyết định thiết kế chốt cứng (executor không tự đổi):**

- **Agent KHÔNG thay runner phase 09.** Runner deterministic vẫn là đường sản xuất (classify/embed hàng loạt); agent là tầng điều tra TRÊN cụm do `/api/clusters/run` (phase 14) tạo. Phân biệt trong DB: agent run ghi `analysis_runs.pipeline_version = 'agent-router-v1'`.
- `llm_call_logs` chỉ ghi call LLM thật → chỉ thêm `'route'` và `'critic'`; **KHÔNG thêm `'tool_call'`** (tool không-LLM không thuộc bảng "llm" call logs — lệch so với brainstorm 25/08, đã ghi decisions 2026-08-26).
- Impact check KHÔNG FK về `clusters.id` (clusters bị DELETE-all mỗi lần rerun phase 14) — chỉ snapshot `cluster_name`; FK về `insights.id` với `ON DELETE SET NULL`.

## 2 · Mục tiêu pha + Non-goals

**Mục tiêu:** (1) migration `0007_agent_substrate` — 3 cột embedding trên insights + 3 bảng mới + 2 enum mới + mở rộng `llm_call_type`; (2) script phát bộ dữ liệu demo ~650 row vi-en 6 tuần có CÀI CẢM BÁO: 1 cụm emerging thật + 1 false-alarm burst (cho demo reject); (3) import + classify xong để các phase 18–20 có sân chơi.

**Non-goals:** viết code agent/toolbox/graph (18–19); endpoint mới nào; đụng bảng checkpoint langgraph (filter Alembic giữ nguyên); pre-label dữ liệu synthetic (labels phải đến từ classifier thật để pipeline demo trung thực).

**Chi phí LLM (chốt trước):** classify ~650 row ≈ ~650 call nhỏ qua relay rẻ (S2). Nếu tín dụng căng → chạy `--rows 300` (vẫn đủ: 5 chủ đề baseline × ~50 + 40 emerging + 25 burst). Con số này là tham số CLI, không phải hằng số cứng.

## 3 · Tasks

### Task 1 — Migration `0007_agent_substrate` + models đồng bộ

**Files:** Create `backend/alembic/versions/0007_agent_substrate.py`; Modify `backend/app/models/enums.py`, `backend/app/models/insight.py`; Create `backend/app/models/action_draft.py`, `backend/app/models/insight_review.py`, `backend/app/models/impact_check.py`; Modify `backend/app/models/__init__.py`

- [ ] Step 1.1: `enums.py` thêm 2 class mirror pattern sẵn có + bổ sung `LlmCallType`:
  ```python
  class DraftKind(str, enum.Enum):
      draft_ticket = "draft_ticket"
      slack_message = "slack_message"
      report = "report"

  class DraftStatus(str, enum.Enum):
      draft = "draft"
      exported = "exported"

  class LlmCallType(...):
      ...  # giữ 4 value cũ, thêm:
      route = "route"
      critic = "critic"
  ```
- [ ] Step 1.2: Revision `0007_agent_substrate` (down_revision = head THẬT lúc mở phase, hiện dự kiến `0006`):
  - `op.add_column("insights", ...)` × 3: `embedding` (`Vector(1536)`, nullable), `embedding_model` (`String(100)` nullable), `embedding_dim` (`Integer` nullable) — mirror chính xác `feedbacks.py:64-66`.
  - `sa.Enum("draft_ticket","slack_message","report", name="draft_kind_enum")` + `sa.Enum("draft","exported", name="draft_status_enum")` (create_type).
  - Bảng `action_drafts`: `id` UUID pk default gen_random_uuid, `insight_id` FK insights.id **ON DELETE CASCADE**, `kind` draft_kind_enum NOT NULL, `body` Text NOT NULL, `status` draft_status_enum NOT NULL server_default 'draft', `created_at` timestamptz server_default now.
  - Bảng `insight_reviews` (mirror `models/human_review.py`): `id`, `insight_id` FK CASCADE, `original_value` JSONB NOT NULL, `edited_value` JSONB NULL, `action` **REVIEW_ACTION_ENUM có sẵn** (approve/edit/reject — tái dùng, không tạo enum mới), `reason` Text NULL, `reviewer_id` FK users.id, `created_at`.
  - Bảng `impact_checks`: `id`, `insight_id` FK **SET NULL**, `cluster_id` UUID NULL (không FK — lý do §1), `cluster_name` String(255) NOT NULL, `checked_at` timestamptz NOT NULL, `window_days` Integer NOT NULL, `before_count` Integer NOT NULL, `after_count` Integer NOT NULL, `delta_ratio` Float NULL, `created_at`. Index `ix_impact_checks_insight_id`.
  - `op.execute("ALTER TYPE llm_call_type ADD VALUE IF NOT EXISTS 'route'")` + tương tự `'critic'`. (PG17 cho ADD VALUE trong transaction miễn KHÔNG dùng giá trị mới trong cùng transaction — migration này chỉ ADD.)
- [ ] Step 1.3: Models Python đồng bộ 100% với migration (mapped_column mirror feedback embedding triplet; 3 file model mới; export trong `__init__.py`). Verify import: `uv run python -c "from app.models.action_draft import ActionDraft; from app.models.insight_review import InsightReview; from app.models.impact_check import ImpactCheck"`.
- [ ] Step 1.4: Verify hai chiều: `uv run alembic upgrade head` → Supabase Studio thấy 3 bảng + 3 cột + 2 enum mới; `uv run alembic downgrade -1` rồi `upgrade head` lại được (reversible — down_revision nối đúng). Commit: `feat(db): agent substrate — insights.embedding, action_drafts, insight_reviews, impact_checks`

### Task 2 — Generator bộ dữ liệu demo `scripts/generate_demo_dataset.py`

**Files:** Create `backend/scripts/generate_demo_dataset.py`

- [ ] Step 2.1: CLI argparse: `--rows` (default 650), `--weeks` (default 6), `--out` (default `demo_dataset.csv`). Output CSV cột đúng schema import hiện có: `external_ref,source,created_at,raw_content` (UTF-8, LF).
- [ ] Step 2.2: Thành phần dữ liệu (toàn bộ tiếng Việt trộn tiếng Anh kiểu code-switching, nội dung GIẢ hoàn toàn):
  - **Baseline:** 5 chủ đề (vd: tốc độ phản hồi chậm, dịch thuật sai nghĩa, giọng đọc tự nhiên, giá gói premium, lỗi phát âm từ lạ) — mật độ đều ~50 row/chủ đề trải `--weeks` tuần (jitter ±2 ngày, giờ hành chính).
  - **Planted emerging:** ~40 row cùng 1 chủ đề ("không đăng nhập được bằng Google trên app mobile") dồn vào 5 NGÀY cuối timeline — phải đủ để phase 14 tính `is_emerging=true` (previous==0, current≥CLUSTER_EMERGING_MIN) và `is_spike`.
  - **Planted false alarm:** ~25 row 1 chủ đề ("email thông báo tới trễ") bung ở tuần giữa rồi TẮT hẳn 3 tuần cuối — dùng để demo đường REJECT (agent đề xuất escalate, người nhận ra không phải sự cố thật).
  - **PII giả có chủ đích:** ~15% row baseline nhét tên/email/số điện thoại giả (domain `.example`, đầu số 09xx) để `pii_detected>0` sau sanitize — demo badge PII.
  - `external_ref = f"demo-{i:05d}"` (tiền tố phục vụ cleanup); `source` luân version {app_review, email, web_form}; `created_at` ISO 8601.
- [ ] Step 2.3: Verify offline trước khi import: chạy script → CSV đúng số dòng, parse lại bằng `csv.DictReader` không lỗi, mọi `created_at` nằm trong cửa sổ `--weeks`. Commit: `feat(scripts): demo dataset generator with planted emerging cluster and false alarm`

### Task 3 — Nạp dữ liệu + classify qua runner hiện có

**Files:** không có file code mới — vận hành API đang sống

- [ ] Step 3.1: Import: `POST /api/feedbacks/import-csv` (auth pm, upload `demo_dataset.csv`) → 200, đếm row import thành công = số dòng CSV (dedup external_ref không có — file mới tinh).
- [ ] Step 3.2: Classify: `POST /api/analysis/runs` → chờ completed (poll `GET /api/analysis/runs/{id}`; ~650 item, runner xử lý tuần tự — ghi lại duration thật vào file này làm số liệu luận văn).
- [ ] Step 3.3: Clustering: `POST /api/clusters/run` (yêu cầu phase 14 đã xong Task 3–4) → kiểm tra `GET /api/clusters`: cụm Google-login có `is_spike=true` (hoặc `is_emerging` tuỳ cửa sổ), false-alarm cụm có `growth_ratio` cao ở lịch sử nhưng `current_count≈0`.
- [ ] Step 3.4: Ghi kết quả verify (JSON rút gọn) vào mục §1 của file này. Commit tài liệu: `docs(plans): phase 17 verification results`

## 4 · Acceptance criteria + Evidence cần chụp

- [ ] `alembic upgrade/downgrade/upgrade` sạch; 3 bảng + 2 enum + 2 value mới tồn tại; 4 bảng checkpoint vẫn ngoài Alembic
- [ ] CSV nạp được qua import-csv; sau classify: ≥95% row có labels; `pii_detected > 0` trên nhóm row nhét PII
- [ ] Sau `/clusters/run`: planted emerging cluster được flag đúng (is_emerging/is_spike); false-alarm cụm tồn tại với hình dạng trend phù hợp reject-demo
- [ ] Không `raw_content` nào lộ qua `GET /api/feedbacks` list/detail (test tay + assert suite hiện có vẫn xanh)
- [ ] **Evidence luận văn:** bảng Supabase Studio 3 bảng mới rỗng-sạch-trước-khi-dùng; CSV header + 5 dòng mẫu; biểu đồ số row/ngày của CSV (chứng minh hình dạng planted spike/burst)

## 5 · Blocker rule

ALTER TYPE ADD VALUE vướng pooler/prepared statement (lỗi PG "unsafe use of new value") → tách 2 revision: 0007 bảng+cột, 0008 chỉ 2 lệnh ADD VALUE chạy `op.execute` ngoài transaction (`migration.run_transaction = False` không có trong alembic 1.x → dùng `with op.get_context().autocommit_block():`). Vẫn fail → STOP task, entry decisions, chuyển Task 2 (script không phụ thuộc DB). Dataset chạy xong mà cụm planted KHÔNG tách ra được ở phase 14 → đừng sửa generator vội: sweep `CLUSTER_MIN_SIZE` theo blocker rule phase 14 trước, chỉ đụng generator khi đã loại trừ nguyên nhân phía engine.
