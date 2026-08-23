# Phase 01 — Preconditions & Môi trường

> **Nguồn:** execute-plan §3 (preconditions) + §5 (env contract) + rule §10.1 (pin ngày đầu) · **v1.1: DB = Supabase**
> **Trạng thái:** ⬜ · **Blocked by:** — (phase đầu tiên)
> **Commit mẫu:** `chore(env): pin deps day one, add .env.example` + `chore(infra): supabase setup note`

## 1 · Mục tiêu

Máy đạt đủ điều kiện để mọi phase sau chạy được: **Supabase project** sẵn sàng với connection string session pooler (việc người dùng), uv + Python 3.12 pinned + toàn bộ dependencies cài xong (việc agent), env contract `.env.example` commit, `.env` thật có key LLM/Langfuse/DB.

**Nguyên tắc §3:** precondition fail → in hướng dẫn, KHÔNG âm thầm bỏ qua.

## 2 · Việc CON NGƯỜI tự làm (agent không thể thay)

### 2.1 Tạo Supabase project (~10 phút, trên trình duyệt)

1. Đăng ký/đăng nhập [supabase.com](https://supabase.com) — free tier đủ dùng (500 MB, 2 free projects).
2. **New project**:
   - **Region: Singapore** (gần VN, latency thấp nhất) — hoặc EU nếu muốn đồng bộ region với Langfuse EU;
   - Đặt **Database Password** mạnh, LƯU NGAY vào password manager (quên phải reset).
3. Lấy connection string: **Dashboard → Connect → tab "Session pooler"** — copy URI dạng:
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`
   → đổi scheme thành `postgresql+psycopg://` khi điền vào `.env`.
   - **KHÔNG dùng** transaction pooler (port `6543`) — phá prepared statements của Alembic/psycopg;
   - Direct connection `db.<ref>.supabase.co:5432` chỉ dùng nếu mạng nhà hỗ trợ IPv6 tốt — mặc định ưu tiên pooler.
4. Ghi chú anti-pause: free tier **tự pause sau 7 ngày low-activity** → đặt lịch nhắc tuần: mở dashboard hoặc chạy ≥1 query.

### 2.2 Điền `.env` thật

Copy `.env.example` (agent tạo ở mục 3.4) thành `backend/.env`, điền giá trị thật:

| Biến | Người dùng cung cấp |
|---|---|
| `DATABASE_URL` | Session-pooler URI từ 2.1 (scheme `postgresql+psycopg://`) |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | Provider OpenAI-compatible đã chọn |
| `EMBEDDING_MODEL` | Tên model embedding **đã xác nhận bằng 1 call `/v1/embeddings` thật** (spike S2/S3 sẽ verify lại) |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | Tạo project trên Langfuse Cloud **Hobby, region EU**, copy key từ project settings |

Không commit `.env`. Không paste key vào chat/docs.

## 3 · Việc AGENT làm — checklist chi tiết

- [ ] **3.1 Cài uv** (PowerShell, không cần admin):
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  uv --version   # mở terminal mới nếu chưa thấy PATH
  ```
- [ ] **3.2 Đặt Windows user-level env vars** (đúng tên plan §3.3):
  ```powershell
  [Environment]::SetEnvironmentVariable('STANZA_RESOURCES_DIR','D:\stanza_resources','User')
  [Environment]::SetEnvironmentVariable('PIP_CACHE_DIR','D:\.pip-cache','User')
  New-Item -ItemType Directory -Force D:\stanza_resources, D:\.pip-cache | Out-Null
  # terminal mới sau khi đặt để env mới có hiệu lực
  ```
- [ ] **3.3 Tải models NLP** (chạy sau 3.2; nặng ~vài GB, máy 8 GB nên đóng app khác):
  ```powershell
  cd backend
  uv run python -c "import stanza; stanza.download('vi'); stanza.download('en')"
  # spaCy en_core_web_lg: cài thẳng wheel theo AGENTS.md
  uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
  ```
- [ ] **3.4 Tạo `.env.example` tại root repo** — nội dung Y HỆT khối ini dưới đây (contract §5 v1.1, thêm bớt là lệch):

  ```ini
  # --- App ---
  APP_ENV=dev                      # dev|prod
  SECRET_KEY=changeme-openssl-rand-hex-32
  CORS_ORIGINS=http://localhost:3000

  # --- Database (Supabase session pooler; direct db.<ref>.supabase.co:5432 chỉ khi IPv6 OK) ---
  DATABASE_URL=postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

  # --- LLM provider (OpenAI-compatible) ---
  LLM_BASE_URL=
  LLM_API_KEY=
  LLM_MODEL=
  EMBEDDING_MODEL=
  EMBEDDING_DIM=1536

  # --- Pipeline thresholds (configurable per thesis spec) ---
  CLASSIFY_CONFIDENCE_REVIEW_BELOW=0.60
  HIGH_SEVERITY_CONFIDENCE_REVIEW_BELOW=0.75

  # --- Tracing (Langfuse Cloud EU) ---
  LANGFUSE_PUBLIC_KEY=
  LANGFUSE_SECRET_KEY=
  LANGFUSE_BASE_URL=https://cloud.langfuse.com
  LANGFUSE_TRACING_ENABLED=true    # false = offline demo kill switch
  PROMPT_VERSION=v1
  ```

- [ ] **3.5 Tạo `.gitignore` tại root**: `.env`, `backend/.env`, `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`, `dist/`, `.pytest_cache/`, `*.egg-info/`, `.ruff_cache/`.
- [ ] **3.6 Tạo `backend/.python-version`** nội dung đúng một dòng: `3.12`
- [ ] **3.7 Tạo `backend/pyproject.toml`** — uv project, pin CHÍNH XÁC ngày đầu (rule §10.1), yêu cầu `requires-python == "3.12.*"`. Danh sách pin từ §1 (điền version cụ thể hiện hành tại thời điểm cài, ghi từng số vào decisions.md entry "day-one pins"):

  | Nhóm | Package |
  |---|---|
  | Web | `fastapi`, `uvicorn>=0.30`, `python-multipart` |
  | DB | `sqlalchemy>=2`, `alembic`, `psycopg[binary,pool]`, `pgvector>=0.5,<0.6` |
  | Auth | `pwdlib[argon2]`, `pyjwt` |
  | PII | `presidio-analyzer`, `presidio-anonymizer`, `stanza`, `spacy` |
  | LLM/trace | `openai`, `langfuse` v3, `langgraph>=1.2,<2`, `langgraph-checkpoint-postgres` 3.1.x |
  | Backoff | `tenacity` (pre-approved) |
  | Settings | `pydantic-settings` (cần thiết cho config — log 1 dòng lý do vào decisions.md vì không nêu tên trong §1) |
  | Dev group | `pytest`, `pytest-asyncio`, `httpx` (TestClient cần) |

  Sau đó:
  ```powershell
  cd backend
  uv sync          # sinh uv.lock — COMMIT uv.lock
  uv run python -V # phải ra 3.12.x
  ```
- [ ] **3.8 Smoke import** các lib nặng (bắt sớm lỗi wheel Windows):
  ```powershell
  uv run python -c "import fastapi, sqlalchemy, alembic, psycopg, pgvector, openai, langfuse, presidio_analyzer, stanza, spacy, pwdlib, jwt, tenacity; print('OK')"
  ```
- [ ] **3.9 Tạo hạ tầng `infra/`** (§4 layout v1.1):
  - `infra/supabase_setup.md` — note setup 1 lần: link dashboard Connect, SQL cần chạy tay trong **SQL Editor** nếu muốn kiểm soát (`CREATE EXTENSION IF NOT EXISTS vector;` — bare, không pin version), region/password đã dùng, quy tắc anti-pause;
  - `infra/setup_vps.sh` — placeholder skeleton (Ubuntu native deploy, điền ở phase deploy sau);
  - `infra/systemd/` — thư mục rỗng + `.gitkeep`.

## 4 · Tiêu chí nghiệm thu (map DoD)

| Tiêu chí | Bằng chứng |
|---|---|
| Supabase project active, connection string session pooler đã có | `.env` điền xong (không hiện giá trị) |
| Kết nối DB test được: `uv run python -c "import psycopg; psycopg.connect('<url>').execute('select 1'); print('DB OK')"` | output `DB OK` |
| `uv run python -V` = 3.12.x trong backend/ | output |
| `.env.example` tồn tại, đúng contract §5 v1.1, đã commit; `.env` bị ignore (`git check-ignore backend/.env`) | git |
| Models tải xong: `D:\stanza_resources\vi` + `\en` tồn tại; `import spacy; spacy.load('en_core_web_lg')` OK | lệnh |
| `uv.lock` commit, pins không có `latest` | git diff |

## 5 · Lệnh kiểm chứng tổng

```powershell
cd backend
uv sync
uv run python -V
uv run python -c "import spacy; spacy.load('en_core_web_lg'); print('spaCy OK')"
# DB reachability (dán URL thật vào lệnh, KHÔNG commit):
uv run python -c "import os, psycopg; c=psycopg.connect(os.environ['DATABASE_URL']); print(c.execute('select version()').fetchone()[0])"
git status --short   # sạch sau commit, không thấy .env
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| Direct connection `db.<ref>.supabase.co` lỗi IPv6 | Đã mặc định dùng session pooler — nếu pooler cũng lỗi, kiểm firewall/proxy; entry nếu phải đổi kiến trúc kết nối |
| Free project bị pause giữa phase | Dashboard → Resume; entry nhỏ nếu mất dữ liệu (không đáng lẽ) |
| Wheel nào fail cài trên Windows (thường là spaCy/stanza build) | Ghi entry, thử wheel prebuilt tương ứng Python 3.12 win_amd64 |
| Máy hết RAM khi tải/cài models | Đóng app, chạy từng model một; entry nếu phải hạ kích thước model |
| Supabase hết free quota / đổi policy | Cân nhắc PG native Windows làm mirror — entry bắt buộc trước khi chuyển |
