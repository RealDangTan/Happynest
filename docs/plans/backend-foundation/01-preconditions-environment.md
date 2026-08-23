# Phase 01 — Preconditions & Môi trường

> **Nguồn:** execute-plan §3 (preconditions) + §5 (env contract) + rule §10.1 (pin ngày đầu)
> **Trạng thái:** ⬜ · **Blocked by:** — (phase đầu tiên)
> **Commit mẫu:** `chore(env): pin deps day one, add .env.example` + `chore(env): spike tooling bootstrap`

## 1 · Mục tiêu

Máy đạt đủ điều kiện để mọi phase sau chạy được: WSL2 Ubuntu 24.04 + PostgreSQL 16 + pgvector sẵn sàng (việc người dùng), uv + Python 3.12 pinned + toàn bộ dependencies cài xong (việc agent), env contract `.env.example` commit, `.env` thật có key LLM/Langfuse.

**Nguyên tắc §3:** precondition fail → in hướng dẫn, KHÔNG âm thầm bỏ qua.

## 2 · Việc CON NGƯỜI tự làm (agent không thể thay)

### 2.1 Cài WSL2 Ubuntu 24.04 ⚠️ cần quyền admin + có thể phải restart

Hiện trạng: lệnh `wsl` **không tồn tại** trên máy.

```powershell
# 1. PowerShell với Run as Administrator:
wsl --install -d Ubuntu-24.04
# 2. Restart máy khi được yêu cầu.
# 3. Lần boot đầu Ubuntu sẽ hỏi tạo user/password trong WSL (khác user Windows).
# 4. Bật systemd bên trong Ubuntu (cần cho service postgresql):
sudo tee /etc/wsl.conf >/dev/null <<'EOF'
[boot]
systemd=true
EOF
# 5. Từ Windows: restart distro để systemd ăn
wsl --shutdown
wsl -d Ubuntu-24.04 -- bash -lc "systemctl --version"   # phải ra số version, không lỗi
```

Giới hạn RAM (máy 8 GB) — tạo file `C:\Users\<user>\.wslconfig`:

```ini
[wsl2]
memory=2GB
processors=2
swap=1GB
```

Sau đó `wsl --shutdown` lần nữa.

### 2.2 Kiểm tra package PostgreSQL 16 + pgvector trong WSL

```bash
wsl -d Ubuntu-24.04 -- bash -lc "apt-cache policy postgresql-16 postgresql-16-pgvector"
```

- Ubuntu 24.04 (noble) có `postgresql-16` ở repo chính; `postgresql-16-pgvector` nằm ở universe — nếu trống → chạy `sudo add-apt-repository universe && sudo apt update`, vẫn thiếu thì build từ source (`postgresql-server-dev-16`, `make && make install`) và **GHI Decision Log**.
- Kết quả check này dán vào entry decisions.md nếu phải build source.

### 2.3 Điền `.env` thật

Copy `.env.example` (agent tạo ở mục 3.4) thành `backend/.env`, điền giá trị thật:

| Biến | Người dùng cung cấp |
|---|---|
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | Provider OpenAI-compatible đã chọn |
| `EMBEDDING_MODEL` | Tên model embedding **đã xác nhận bằng 1 call `/v1/embeddings` thật** (spike S2/S3 sẽ verify lại) |
| `DATABASE_URL` | Giữ mặc định `postgresql+psycopg://thesis:thesis@localhost:5432/feedback_agent` |
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
  # terminal mới sau khi đặt để PATH/env mới có hiệu lực
  ```
- [ ] **3.3 Tải models NLP** (chạy sau 3.2; nặng ~vài GB, máy 8 GB nên đóng app khác):
  ```powershell
  cd backend
  uv run python -c "import stanza; stanza.download('vi'); stanza.download('en')"
  # spaCy en_core_web_lg: cài thẳng wheel theo AGENTS.md (không qua pip resolve mạng dài)
  uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
  ```
- [ ] **3.4 Tạo `.env.example` tại root repo** — nội dung Y HỆT khối ini dưới đây (contract §5, thêm bớt là lệch):

  ```ini
  # --- App ---
  APP_ENV=dev                      # dev|prod
  SECRET_KEY=changeme-openssl-rand-hex-32
  CORS_ORIGINS=http://localhost:3000

  # --- Database (PG in WSL2, reached from Windows via localhost) ---
  DATABASE_URL=postgresql+psycopg://thesis:thesis@localhost:5432/feedback_agent

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
- [ ] **3.9 Tạo hạ tầng `infra/`** (§4 layout):
  - `infra/wsl_pg_setup.sh` — script **idempotent** chạy trong WSL Ubuntu: `apt install postgresql-16 postgresql-16-pgvector`, tạo role `thesis`/db `feedback_agent` (mật khẩu `thesis` khớp DATABASE_URL mặc định), grant đủ quyền, enable service qua systemctl; chạy lại không phá dữ liệu. LF-only (`sudo bash /mnt/d/AITHUCCHIEN/11236199-LeDangTan-Happynest-Thesis/infra/wsl_pg_setup.sh`);
  - `infra/setup_vps.sh` — placeholder skeleton (Ubuntu native deploy, điền ở phase deploy sau);
  - `infra/systemd/` — thư mục rỗng + `.gitkeep`.

## 4 · Tiêu chí nghiệm thu (map DoD)

| Tiêu chí | Bằng chứng |
|---|---|
| `wsl -l -v` thấy `Ubuntu-24.04 Running`, systemd bật | output lệnh |
| apt có `postgresql-16` + `postgresql-16-pgvector` (hoặc đã build source + logged) | output `apt-cache policy` |
| `uv run python -V` = 3.12.x trong backend/ | output |
| `.env.example` tồn tại, đúng contract §5, đã commit; `.env` bị ignore (`git check-ignore backend/.env`) | git |
| Models tải xong: `D:\stanza_resources\vi` + `\en` tồn tại; `import spacy; spacy.load('en_core_web_lg')` OK | lệnh |
| `uv.lock` commit, pins không có `latest` | git diff |

## 5 · Lệnh kiểm chứng tổng

```powershell
wsl -l -v
wsl -d Ubuntu-24.04 -- bash -lc "systemctl is-system-running"
cd backend; uv sync; uv run python -V
uv run python -c "import spacy; spacy.load('en_core_web_lg'); print('spaCy OK')"
git status --short   # sạch sau commit, không thấy .env
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| `postgresql-16-pgvector` thiếu ở apt | Build pgvector từ source + entry dated (context→decision→alternatives→consequence) |
| Người dùng chọn **không** cài WSL, dùng PG native Windows thay | Entry dated đánh dấu deviation khỏi locked stack; các phase sau đổi `DATABASE_URL` tương ứng; script `infra/wsl_pg_setup.sh` vẫn giữ cho VPS path |
| Wheel nào fail cài trên Windows (thường là spaCy/stanza build) | Ghi entry, thử wheel prebuilt tương ứng Python 3.12 win_amd64 |
| Máy hết RAM khi tải/cài models | Đóng app, chạy từng model một; entry nếu phải hạ kích thước model |
