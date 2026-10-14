# 1. Sơ đồ tổng thể hệ thống

## 1.1. Sơ đồ bối cảnh (C4 — Level 1: System Context)

Hệ thống tương tác với ai và cái gì ở bên ngoài.

```mermaid
flowchart LR
    USR["👤 Người dùng đăng nhập"]

    subgraph System["AI Feedback Agent (VoC OS)"]
        S["Tổng hợp · phân loại · phát hiện vấn đề<br/>từ phản hồi người dùng về sản phẩm AI"]
    end

    LLM["OpenAI-compatible LLM API<br/>(base_url override, temperature=0)"]
    EMB["Embeddings API<br/>(/v1/embeddings, 1536 chiều)"]
    SUPA[("Supabase PostgreSQL 17<br/>+ pgvector (session pooler)")]
    LF["Langfuse Cloud (EU)<br/>Truy vết LLM"]
    CSV["Nguồn dữ liệu CSV<br/>(phản hồi người dùng, VI–EN)"]

    USR -->|"đăng nhập, nhập liệu, phân tích,<br/>ra quyết định ở 3 cổng HITL"| S
    CSV -->|"upload (LISTEN)"| S
    S -->|"prompt JSON đã sanitize"| LLM
    S -->|"batch ≤2048"| EMB
    S -->|"SQL + pgvector <=> (quét chính xác)"| SUPA
    S -->|"trace LLM (chỉ text đã sanitize)"| LF
```

## 1.2. Sơ đồ thành phần (C4 — Level 2: Containers / Components)

```mermaid
flowchart TB
    subgraph Browser["Trình duyệt"]
        FE["Frontend Next.js (App Router)<br/>shadcn/ui + React Query<br/>middleware.ts chặn cookie access_token"]
    end

    subgraph BE["Backend FastAPI (port 8000)"]
        direction TB
        API["app/api/routes<br/>auth · feedback · imports · analysis · taxonomies<br/>admin (clusters/reports) · agent · actions · products"]
        DEPS["app/api/deps.py<br/>OAuth2 cookie + get_current_user"]

        subgraph SERVICES["app/services"]
            PRES["presidio_service<br/>PII sanitize (Stanza vi+en)"]
            INGEST["ingest_service · import_service<br/>llm_mapper (Gate #1)"]
            ENR["enricher (closed-set classify)<br/>embedder · clustering (HDBSCAN)"]
            TAXO["taxonomy_service"]
            AGENT["understand_agent/<br/>graph · nodes · runner"]
            ACT["act_agent + act_grounding<br/>+ act_practices (act-v2)"]
            IMPACT["impact_service"]
            TRACE["tracing + llm_client<br/>(2 lớp truy vết)"]
            GRAPH_RT["graph_runtime<br/>checkpointer AsyncPostgresSaver"]
        end

        JOBS["app/jobs/analysis_runner<br/>BackgroundTasks (không Celery)"]
    end

    subgraph INFRA["Hạ tầng ngoài"]
        PG[("Supabase PostgreSQL 17<br/>pgvector VECTOR(1536)<br/>+ 4 bảng checkpoint LangGraph")]
        LLMAPI["LLM / Embeddings API"]
        LANGFUSE["Langfuse Cloud"]
        DISK[("Disk: storage/imports<br/>CSV gốc")]
    end

    FE -->|"fetch credentials:include<br/>Next rewrite /api/* → :8000"| API
    API --> DEPS
    DEPS --> SERVICES
    JOBS --> ENR
    INGEST --> PRES
    ENR --> TRACE
    AGENT --> GRAPH_RT
    AGENT --> TRACE
    ACT --> TRACE
    BE --> PG
    BE --> LLMAPI
    BE --> LANGFUSE
    INGEST --> DISK
```

## 1.3. Ba lớp chức năng LISTEN → UNDERSTAND → ACT

```mermaid
flowchart LR
    subgraph L["LISTEN — Thu thập & chuẩn hóa"]
        L1["Upload CSV + profile"] --> L2["LLM mapping proposal<br/>✂ CỔNG #1: duyệt mapping"]
        L2 --> L3["Import rows (sanitize PII)"]
        L4["Nhập thủ công POST /feedbacks"] --> L3
    end

    subgraph U["UNDERSTAND — Phân tích & phát hiện vấn đề"]
        U1["Batch classify (closed-set taxonomy)<br/>+ embed 1536d"] --> U2["HDBSCAN cosine<br/>+ naming LLM"]
        U2 --> U3["Trend / Spike / Emerging"]
        U4["Agent LangGraph: planner → tools → evidence → synthesizer"]
        U4 --> U5["✂ CỔNG #2: duyệt insight<br/>(interrupt persist_insight)"]
    end

    subgraph A["ACT — Hành động & đo lường"]
        A1["act_agent: đề xuất theo 8 business function<br/>priority = công thức tất định"]
        A1 --> A2["✂ CỔNG #3: điều chỉnh<br/>human_impact/effort/urgency"]
        A2 --> A3["Impact check<br/>delta_ratio trước/sau"]
    end

    L3 --> U1
    U3 --> U4
    U5 --> A1
    A3 -.->|"vòng lặp đóng KPI"| U1
```

Mọi quyết định tại 3 cổng đều ghi vào `decision_logs` (`agent_value` vs `human_value`) — bộ nhớ quyết định của hệ VoC OS.
