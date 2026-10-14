# 8. Sơ đồ triển khai (Deployment)

> Quy tắc cứng: **không dùng Docker trong mọi môi trường**. Dev = FastAPI native trên Windows; Prod = Ubuntu VPS + systemd + Caddy.

## 8.1. Môi trường phát triển (dev — Windows)

```mermaid
flowchart TB
    subgraph DEV["Máy phát triển Windows (8 GB RAM)"]
        subgraph WIN["Terminal Windows"]
            UVI["uvicorn app.main:app --reload<br/>chạy ĐỘC LẬP 1 terminal riêng"]
            PNPM["pnpm dev (Next.js :3000)"]
        end
        ENV[".env (backend/) — không commit<br/>DATABASE_URL · MODEL_* · LLM_* · LANGFUSE_*"]
        STANZA["Stanza resources vi+en (D:\stanza_resources)"]
        STOR[("backend/storage/imports<br/>CSV gốc")]
        PROCS["Presidio analyzer singleton<br/>(~1GB RAM, khởi tạo 1 lần lúc startup)"]
    end

    subgraph CLOUD["Cloud (managed)"]
        SUPA[("Supabase PostgreSQL 17<br/>session pooler :5432<br/>region ap-southeast-2")]
        LANGFUSE["Langfuse Cloud EU"]
        LLMAPI["LLM/Embeddings API<br/>(base_url override)"]
    end

    PNPM -->|"rewrite /api/* → 127.0.0.1:8000<br/>proxyTimeout 300s"| UVI
    UVI --> SUPA
    UVI --> LLMAPI
    UVI --> LANGFUSE
    UVI --> STOR
    ENV --> UVI
    STANZA --> PROCS
    PROCS --> UVI

    note1["pgvector nằm trong schema extensions<br/>→ search_path=extensions,public<br/>pool_pre_ping=True (pooler ngắt idle)"]
```

## 8.2. Môi trường sản xuất (prod — Ubuntu VPS)

```mermaid
flowchart TB
    USER["Người dùng (trình duyệt)"] -->|HTTPS| CADDY

    subgraph VPS["Ubuntu VPS (native, không Docker)"]
        CADDY["Caddy<br/>reverse proxy → 127.0.0.1:3000 và :8000<br/>TLS tự động"]
        SVC1["systemd unit 1<br/>Next.js (frontend) :3000<br/>node + pnpm"]
        SVC2["systemd unit 2<br/>FastAPI (backend) :8000<br/>uv + uvicorn (không --reload)"]
        SVC1 --> CADDY
        SVC2 --> CADDY

        subgraph APPDIR["/srv (rsync backend/ + frontend/)"]
            UVP["uv sync --frozen<br/>(pyproject pins chốt)"]
            BUILD["next build output"]
        end
        SVC2 --> UVP
        SVC1 --> BUILD
        SECRET["SECRET_KEY thật (từ prod env)<br/>main.py từ chối boot nếu còn default"]
    end

    CADDY --> SVC1
    CADDY --> SVC2

    subgraph CLOUD["Dịch vụ ngoài (không tự host)"]
        SUPA[("Supabase PG 17<br/>session pooler :5432<br/>TCP keepalives 15/5/3<br/>cho checkpointer")]
        LANGFUSE["Langfuse Cloud EU"]
        LLMAPI["LLM/Embeddings API"]
    end

    SVC2 --> SUPA
    SVC2 --> LANGFUSE
    SVC2 --> LLMAPI
```

Các bước deploy (`infra/setup_vps.sh`): `apt install python3.12 uv caddy` → tạo user hệ thống non-login → `rsync backend/` → `uv sync --frozen` → copy unit files `infra/systemd/` → `systemctl enable --now` → Caddy reverse proxy + TLS.

## 8.3. Khởi động ứng dụng (lifespan sequence)

```mermaid
sequenceDiagram
    autonumber
    participant SYS as systemd / dev terminal
    participant APP as FastAPI main.py
    participant PZ as presidio_service
    participant RT as graph_runtime (daemon thread)
    participant PG as Supabase PG

    SYS->>APP: start process
    APP->>APP: _enforce_secret_key<br/>(từ chối boot nếu SECRET_KEY default ở prod)
    APP->>PZ: init_presidio() (Stanza vi+en, analyzer singleton)
    APP->>RT: background thread langgraph-checkpoint-setup
    RT->>PG: ensure_checkpointer_ready() → AsyncPostgresSaver.setup()<br/>(tạo 4 bảng checkpoint nếu thiếu)
    RT->>PG: mark_stale_running_failed() (chữa run treo từ lần trước)
    APP->>APP: register 10 routers + CORS + exception handler
    APP-->>SYS: Uvicorn listening :8000

    Note over APP: Shutdown → tracing.flush() (đẩy batch Langfuse cuối)
```

## 8.4. Rủi ro vận hành & biện pháp (từ thực tế dev)

| Rủi ro | Biện pháp thiết kế |
|---|---|
| Pooler Supabase ngắt kết nối idle | `pool_pre_ping=True`; TCP keepalives (15/5/3) cho checkpointer; pool nhỏ 2+2 |
| pgvector type không resolve | `search_path=extensions,public` trong connect args |
| LLM chạy lâu vượt proxy | `proxyTimeout: 300_000` ở Next; graph chạy background thread + FE polling |
| Run treo do server restart giữa chừng | trạng thái graph persist trong checkpoint tables + `mark_stale_running_failed` lúc startup |
| Supabase free tier tự pause (7 ngày) | chạy ≥1 query mỗi tuần |
| Windows + `--reload` spawn subprocess | uvicorn chạy terminal riêng; background work dùng BackgroundTasks/daemon thread, không Celery |
