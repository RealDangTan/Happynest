# Phase 03 — Repo skeleton · SQLAlchemy models · Alembic

> **Nguồn:** execute-plan §4 (repo layout) + §6 (database models) + §1 (migrations decision)
> **Trạng thái:** ⬜ · **Blocked by:** Phase 01 · **Verify cần DB thật** (Supabase active, cần internet)
> **Commit mẫu:** `feat(db): app skeleton, all core models, alembic baseline`

## 1 · Mục tiêu

Dựng xong "xương sống" FastAPI + toàn bộ 8 bảng dữ liệu + migration chạy được lên **Supabase** (managed PG17). Các phase sau chỉ cắm module vào khung này.

Cây thư mục cần tạo đúng §4 (đã có sẵn từ 01: `pyproject.toml`, `.python-version`):

```text
backend/
├── alembic.ini
├── alembic/{env.py, script.py.mako, versions/}
└── app/
    ├── __init__.py
    ├── main.py
    ├── core/{__init__.py, config.py, security.py(placeholder), logging.py}
    ├── db/{__init__.py, base.py, session.py}
    └── models/{__init__.py, user.py, feedback.py, cluster.py, insight.py,
                human_review.py, correction_example.py, analysis_run.py, llm_call_log.py}
```

## 2 · Việc CON NGƯỜI

- Không có. (Cần internet + Supabase project active để verify — nếu project bị pause, vào dashboard Resume trước.)

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 Config — `app/core/config.py`
- pydantic-settings `Settings(BaseSettings)` đọc file `backend/.env` (`model_config = SettingsConfigDict(env_file=".env")`) — trường khớp 1:1 contract §5:
  `APP_ENV`, `SECRET_KEY`, `CORS_ORIGINS` (str → property trả list), `DATABASE_URL`, `LLM_BASE_URL/KEY/MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM:int=1536`, `CLASSIFY_CONFIDENCE_REVIEW_BELOW:float=0.60`, `HIGH_SEVERITY_CONFIDENCE_REVIEW_BELOW:float=0.75`, `LANGFUSE_PUBLIC_KEY/SECRET_KEY/BASE_URL`, `LANGFUSE_TRACING_ENABLED:bool=True`, `PROMPT_VERSION:str="v1"`.
- Singleton `get_settings()` với `@lru_cache`.

### 3.2 Logging — `app/core/logging.py`
- Cấu hình std logging format có timestamp + level + logger name.
- **Rule PII:** logger KHÔNG BAO GIỜ nhận payload content; chỉ id/metadata. Ghi comment cảnh báo ngay đầu module.

### 3.3 DB — `app/db/session.py`, `app/db/base.py`
- `engine = create_engine(settings.DATABASE_URL, connect_args={"options": "-csearch_path=extensions,public"}, pool_size=2, max_overflow=2)`:
  - `search_path` chứa schema `extensions` theo quy ước Supabase (nơi extension `vector` được cài);
  - pool nhỏ phù hợp free tier qua internet; `SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)`.
- `base.py`: `class Base(DeclarativeBase)`; import tất cả models để metadata đầy đủ cho Alembic.

### 3.4 App factory — `app/main.py`
- `create_app()`: include CORS middleware (origins từ settings), exception handler chung (JSON `{detail}`), router `/api/health`.
- `lifespan`: chỗ neo khởi tạo analyzer Presidio (Phase 06) + langfuse shutdown (Phase 07) — đặt hook trống có comment bây giờ.
- `/api/health` bản sơ khai: trả `{"status":"ok","app_env":...}` — Phase 08 mở rộng check DB + LLM mode.

### 3.4b Stub router — `app/api/routes/admin.py`
- Các endpoint **501 stub có docstring** giải thích phase sau sẽ làm (§7): `GET /api/clusters`, `GET /api/insights`, `POST /api/reviews/{feedback_id}`, `POST /api/corrections/{feedback_id}`, `GET /api/reports/summary`.
- Include router vào app factory — DoD Phase 12 sẽ rà lại các stub này còn nguyên.

### 3.5 Models — 8 bảng, ĐỦ trường theo §6, không thêm bớt

Chuẩn chung: pk `uuid` (`uuid.uuid4` default, PG UUID type); timestamp timezone-aware (`DateTime(timezone=True)`, server_default `func.now()`); enum native PG qua `sqlalchemy.Enum(..., name="...", native_enum=True)`.

| Bảng | Trường (nguồn §6) | Enum liên quan |
|---|---|---|
| `users` | email unique, password_hash, role, created_at | `user_role(pm, operations)` |
| `feedbacks` | external_ref?, source str, created_at (event time), imported_at; raw_content text, sanitized_content text?, pii_detected bool default false, pii_entities JSONB; categories JSONB list, ai_issue?, sentiment?, severity?, confidence float?; requires_human_review bool default false, review_status default unreviewed; embedding `Vector(1536)`? (`pgvector.sqlalchemy.Vector`), embedding_model str?, embedding_dim int?; analysis_run_id FK? | `ai_issue_enum`, `sentiment_enum`, `severity_enum(low, medium, high, critical)`, `review_status(unreviewed, pending, approved, edited, rejected)` |
| `clusters` | name, summary, feedback_count, first_seen, last_seen, current_count, previous_count, growth_ratio, is_emerging bool, is_spike bool, suggested_priority — **tạo bây giờ, unused** | — |
| `insights` | cluster_id FK?, title, summary, suggested_action, evidence_ids JSONB, review_status — **unused** | dùng lại review_status |
| `human_reviews` | feedback_id FK, original_value JSONB, edited_value JSONB?, action, reason?, reviewer_id FK users, created_at — **unused** | `review_action(approve, edit, reject)` |
| `correction_examples` | feedback_id FK, original_prediction JSONB, corrected_value JSONB, reason?, created_at — **unused** | — |
| `analysis_runs` | pipeline_version, llm_model, prompt_version, embedding_model, started_at, completed_at?, status, processed_count int, total_count int, error text? | `run_status(running, completed, failed)` |
| `llm_call_logs` | analysis_run_id FK?, feedback_id FK?, call_type, prompt_version, model, latency_ms int, prompt_tokens int?, completion_tokens int?, error text?, created_at | `llm_call_type(classify, embed, name_cluster, generate_insight)` |

⚠️ **Điểm phải chốt rõ (ghi vào decisions.md khi làm):** bộ giá trị enum `ai_issue_enum` và `sentiment_enum` plan chưa liệt kê — đề xuất khởi điểm: sentiment `(positive, negative, neutral, mixed)`; ai_issue gắn vấn đề sản phẩm AI `(hallucination, inaccuracy, bias, safety, privacy, performance, other)`. Đổi sau = phải viết migration `ALTER TYPE`, nên chốt sớm và nhất quán với `schemas/taxonomy.py` của Phase 07.

### 3.6 Alembic
- `alembic.ini` tại `backend/`; `env.py`:
  - đọc `DATABASE_URL` từ settings (ghi đè `sqlalchemy.url`);
  - `target_metadata = Base.metadata`;
  - **`include_object()` filter LOẠI 4 bảng langgraph**: `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations` (quyết định đã khóa §1) — autogenerate về sau sẽ không đụng chúng;
  - `compare_type=True`.
- Migration theo nhóm logic (autogenerate rồi rà tay):
  1. `0001_baseline_extensions_users` — `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` (**bare** — Supabase không cho pin version) + bảng `users`;
  2. `0002_feedback_analysis_logs` — `feedbacks`, `analysis_runs`, `llm_call_logs`;
  3. `0003_future_phase_tables` — `clusters`, `insights`, `human_reviews`, `correction_examples`.
- Chạy: `uv run alembic upgrade head` → verify `\dt` trong psql thấy đủ bảng, extension vector tồn tại.

## 4 · Tiêu chí nghiệm thu

| Tiêu chí | Bằng chứng |
|---|---|
| `uv run uvicorn app.main:app` boot xanh (không cần DB cho health cơ bản) | terminal output |
| `alembic upgrade head` sạch trên Supabase; `alembic downgrade base` + upgrade lại cũng sạch | lệnh |
| 8 bảng + 7 enum types tồn tại đúng tên; extension `vector` enabled | Supabase Studio → Database → Tables/Extensions, hoặc SQL Editor query `SELECT extname FROM pg_extension WHERE extname='vector'` |
| Filter langgraph hoạt động: tạo bảng giả `checkpoints` thủ công rồi `alembic revision --autogenerate` → diff KHÔNG sinh drop/create cho nó | test tay 1 lần, ghi kết quả |
| Không file nào log/print raw content | review diff |

## 5 · Lệnh kiểm chứng

```powershell
cd backend
uv run alembic upgrade head
# kiểm bảng/enum/extension: Supabase Studio → SQL Editor:
#   SELECT tablename FROM pg_tables WHERE schemaname='public';
#   SELECT extname FROM pg_extension WHERE extname='vector';
uv run uvicorn app.main:app   # Ctrl+C thoát; --reload để dành terminal riêng
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| `Vector(1536)` import/pgvector-python lệch API | Ghim đúng `pgvector>=0.5,<0.6`, entry nếu phải đổi cách khai báo |
| Autogenerate sinh sai enum/index | Sửa tay migration, entry ghi lý do |
| Supabase pause/mất mạng | Dashboard → Resume project; hoãn verify, làm tiếp code các phase độc lập |
| Đổi bộ giá trị enum so với đề xuất ở 3.5 | Entry dated trước khi viết migration |
