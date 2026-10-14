# 7. Sơ đồ module API & xác thực

## 7.1. Tổ chức module API (package diagram)

```mermaid
flowchart TB
    subgraph app["backend/app"]
        MAIN["main.py<br/>lifespan: presidio init · checkpointer setup ·<br/>mark_stale_running_failed · tracing.flush"]

        subgraph ROUTES["api/routes — 10 router"]
            AUTH["auth<br/>/api/auth"]
            FEED["feedback<br/>/api/feedbacks"]
            IMP["imports<br/>/api/imports (Cổng #1)"]
            ANA["analysis<br/>/api/analysis/runs"]
            TAX["taxonomies<br/>/api/taxonomies (cổng apply)"]
            ADM["admin<br/>/api/clusters · /api/reports · impact-checks"]
            AGEN["agent<br/>/api/agent/runs (Cổng #2)"]
            INS["agent.py<br/>/api/insights"]
            ACTR["actions<br/>/api/actions (Cổng #3)"]
            PROD["products<br/>/api/products"]
        end

        DEPS["api/deps.py<br/>get_current_user (OAuth2 cookie)<br/>shared authenticated access"]
        subgraph SVC["services"]
            S1["presidio_service · ingest_service · import_service<br/>llm_mapper · profiler"]
            S2["analysis_service · enricher · embedder · clustering<br/>taxonomy_service"]
            S3["understand_agent/ (graph·nodes·runner) · graph_runtime"]
            S4["act_agent · act_grounding · act_practices"]
            S5["llm_client · tracing · decision_log · impact_service"]
        end
        JOBS["jobs/analysis_runner.py<br/>BackgroundTasks"]
        MODELS["models/ — 15 ORM models · enums.py"]
        DB["db/session.py<br/>pool_size=2, max_overflow=2<br/>search_path=extensions,public · pool_pre_ping"]
    end

    MAIN --> ROUTES
    ROUTES --> DEPS
    ROUTES --> SVC
    ANA --> JOBS
    JOBS --> S2
    DB --> MODELS
    SVC --> DB

    AUTH -.->|"health · token/register/logout"| NOGUARD["public: token/register/logout · health"]
```

## 7.2. Ma trận endpoint × xác thực (45+ endpoint, tất cả đã production)

| Nhóm | Endpoint đại diện | Method | Xác thực |
|---|---|---|---|
| Health | `/api/health` | GET | công khai |
| Auth | `/api/auth/token` · `/register` · `/logout` · `/me` | POST/GET | công khai (login) / user |
| Products | `/api/products` | GET/POST | cookie/Bearer |
| Products | `/api/products/{id}` | PATCH/DELETE | cookie/Bearer |
| Feedback | `/api/feedbacks` (+ `/similar`) | GET/POST | cookie/Bearer |
| Feedback | `/api/feedbacks/{id}` · `/bulk-delete` | PATCH/DELETE | cookie/Bearer |
| Imports (Cổng #1) | `/api/imports/**` (mapping proposal/decision, cancel) | POST/GET | cookie/Bearer |
| Imports | `/api/imports/{id}` | DELETE | cookie/Bearer |
| Analysis | `/api/analysis/runs/**` · `/re-enrich-uncategorized` | POST/GET | cookie/Bearer |
| Taxonomies | `/api/taxonomies/generate` · `/recommend` (tốn phí LLM) | POST | cookie/Bearer |
| Taxonomies | `/api/taxonomies/apply` · `/review/{id}` | POST | cookie/Bearer (cổng con người) |
| Agent (Cổng #2) | `/api/agent/runs/**` (+trace, decision) | POST/GET | cookie/Bearer |
| Insights | `/api/insights` | GET | cookie/Bearer |
| Insights | `/api/insights/{id}` | PATCH/DELETE | cookie/Bearer |
| Actions (Cổng #3) | `/api/insights/{id}/actions/**` · `/api/actions/{id}` | POST/GET/PATCH | cookie/Bearer |
| Clusters/Reports | `/api/clusters` · `/api/reports/summary` · `/api/reports/kpis` | GET/POST | cookie/Bearer |
| Impact | `/api/impact-checks/run` | POST | cookie/Bearer |

Quy ước lỗi chuẩn: `401` hết hạn/không đăng nhập · `404` không tồn tại · `409` xung đột trạng thái · `422` schema sai · `500` lỗi hệ thống.

## 7.3. Luồng xác thực theo request

```mermaid
flowchart TB
    REQ["Request /api/* (kèm cookie access_token)"] --> CHK{"middleware FE<br/>(chỉ routing trang)"}
    CHK -->|"path công khai"| PUB["landing / login / register"]
    CHK -->|"path được bảo vệ"| API["FastAPI"]

    API --> C1{"get_current_user<br/>decode JWT (HS256, TTL 12h)"}
    C1 -->|hỏng| E401["401 → FE expireSession()<br/>auto logout → /login"]
    C1 -->|OK| OK["Handler + get_db session<br/>workspace dùng chung"]
    OK --> RESP["Response<br/>(raw_content không bao giờ xuất hiện)"]
```

## 7.4. Chuỗi gọi LLM có cấu trúc (structured output pipeline)

```mermaid
flowchart LR
    CALL["chat_structured(schema, call_type,<br/>prompt_version)"] --> ROUTE["_resolve_model<br/>MODEL_* theo use-case qua .env"]
    ROUTE --> A["Chế độ A:<br/>response_format=json_schema (strict)"]
    A -->|thành công| V["Pydantic validate"]
    A -->|thất bại| B["Chế độ B: prompt-JSON<br/>+ _extract_json"]
    B -->|sai schema| B2["1 lần retry<br/>(kèm nội dung lỗi)"]
    B2 -->|vẫn sai| ERR["LLMStructureError"]
    B --> V
    V --> LOG["_record_attempt:<br/>Langfuse generation<br/>+ llm_call_logs (metadata)"]
    ERR --> LOG
    LOG --> RES["Kết quả validated"]

    style ERR fill:#fee
```

> Mỗi lần gọi ghi **cả hai** lớp trace (kể cả lần thất bại); Langfuse nhận input đã sanitize (≤2000 ký tự), `llm_call_logs` chỉ nhận metadata.
