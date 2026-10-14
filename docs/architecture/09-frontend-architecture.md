# 9. Kiến trúc Frontend (Next.js App Router)

## 9.1. Sơ đồ thành phần frontend

```mermaid
flowchart TB
    subgraph B["Trình duyệt"]
        MW["middleware.ts<br/>anon → /landing · logged-in → /importer<br/>bỏ qua /api, /_next, assets"]
        LAY["app/layout.tsx + (app)/layout.tsx<br/>(bảo vệ shell ứng dụng)"]
        TOP["top-navbar: product switcher<br/>+ Activity Sheet (activity-sheet.tsx)<br/>ActivityProvider poll /imports + /analysis/runs"]
        SUB["components/ (shadcn/ui preset b4IdeDqtkJ)"]
    end

    subgraph N["Next.js server (:3000)"]
        RQ["hooks/* (React Query)<br/>use-imports · use-feedbacks · use-analysis<br/>use-clusters · use-insights · use-agent<br/>use-actions · use-taxonomy · use-me"]
        APIF["lib/api.ts: apiFetch<br/>credentials: include · ApiError<br/>401 → expireSession → /login"]
        REW["next.config.ts rewrite:<br/>/api/* → http://127.0.0.1:8000/api/*<br/>proxyTimeout 300s"]
    end

    B --> RQ --> APIF --> REW --> BE["FastAPI :8000"]
```

## 9.2. Bản đồ trang ↔ chức năng ↔ endpoint

```mermaid
flowchart LR
    subgraph PUBLIC["Công khai"]
        LP["/landing"]
        LG["/login"] 
        RG["/register"]
    end

    subgraph LISTEN["LISTEN"]
        IMP["/importer<br/>wizard: File → Preview →<br/>Cổng #1 mapping → Result"]
        VAU["/vault<br/>kho dữ liệu + activity receipt"]
        FDB["/feedbacks (+/[id])<br/>danh sách · chi tiết · nhập tay"]
        TAX["/taxonomy<br/>AI generate/recommend,<br/>Human apply"]
    end

    subgraph UND["UNDERSTAND"]
        ANA["/analysis<br/>chạy + theo dõi batch"]
        CLU["/clusters<br/>HDBSCAN + trend"]
        DGR["/data-graph<br/>Ask AI (S03) + trace +<br/>poll Cổng #2"]
        INS["/insights"]
    end

    subgraph ACT["ACT"]
        REP["/reports (/summary)<br/>Cổng #2 decision bar<br/>+ evidence panel"]
        MAT["/matrix<br/>priority matrix + drawer Cổng #3"]
        STK["/stakeholders<br/>decision-support panel"]
    end

    DSH["/dashboard<br/>đích sau login"]

    LG --> DSH --> IMP
    IMP --> VAU --> FDB
    FDB --> ANA --> CLU
    CLU --> DGR --> INS --> REP
    REP --> MAT --> STK
    TAX -.->|"taxonomy v2 → re-enrich"| ANA
```

## 9.3. Ánh xạ hook ↔ endpoint (React Query)

| Hook / UI | Endpoint BE | Trang |
|---|---|---|
| `use-me` · account-menu · login/register | `POST /api/auth/token` · `/register` · `/logout` · `GET /me` | login, register, navbar |
| `top-navbar` (product switcher) | `GET/POST /api/products` · `PATCH/DELETE /api/products/{id}` | mọi trang (app shell) |
| `use-imports` | `POST /api/imports` · `GET /imports/{id}` (+`/preview`, `/mapping`) · `POST .../mapping/proposal` · `POST .../mapping/decision` · `POST /cancel` · `DELETE` | **/importer** (Cổng #1) |
| `use-feedbacks` · data-entry-dialog | `GET/POST /api/feedbacks` · `GET/PATCH/DELETE /{id}` · `POST /bulk-delete` · `GET /{id}/similar` | /feedbacks, /vault |
| `use-analysis` | `POST /analysis/runs/preview` · `POST /runs` · `GET /runs` · `GET /runs/{id}` · `POST /runs/{id}/cancel` | /analysis, /vault |
| `use-taxonomy` | `POST /taxonomies/generate` · `/apply` · `/recommend` · `/recommend/apply` · `POST /analysis/re-enrich-uncategorized` | /taxonomy |
| `use-clusters` | `GET /api/clusters?sort=…` · `POST /api/clusters/run` | /clusters |
| `use-insights` · `use-reports` | `GET /api/insights` · `PATCH/DELETE /insights/{id}` · `GET /reports/summary?days=7\|30\|90` | /insights, /reports |
| `use-agent` | `POST /agent/runs` · `GET /runs/{id}` (pending_approval + progress) · `GET /trace` · `POST /runs/{id}/decision` | /data-graph, /reports (Cổng #2) |
| `use-actions` | `POST /insights/{id}/actions/generate` · `GET /insights/{id}/actions` · `POST /insights/{id}/actions` · `PATCH /actions/{id}` | /matrix, /stakeholders (Cổng #3) |

Chưa nối FE (chỉ Swagger): `/api/health`, `/api/products/{id}`, schema endpoints, `GET/POST /api/taxonomies` (+`/review`), `GET /api/reports/kpis`, `POST /api/impact-checks/run`.

## 9.4. Trình tự tương tác FE với Cổng #2 (polling + interrupt)

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng
    participant FE as /data-graph (React Query)
    participant MW as Next rewrite
    participant BE as /api/agent/runs
    participant PG as checkpoints (LangGraph)

    U->>FE: gõ câu hỏi → POST /api/agent/runs
    FE->>MW: fetch (credentials: include)
    MW->>BE: rewrite :8000
    BE-->>FE: {run_id, status: running}
    loop poll (use-agent refetch)
        FE->>BE: GET /api/agent/runs/{id}
        BE->>PG: get_run_snapshot
        BE-->>FE: progress + (khi interrupt) pending_approval payload
    end
    FE-->>U: hiện draft insight + evidence
    U->>FE: chọn approve/edit/investigate_more/reject (+ reason)
    FE->>BE: POST /api/agent/runs/{id}/decision
    BE->>PG: Command(resume) → apply_decision
    BE-->>FE: {final_status, insights_created}
    Note over FE: 401 bất kỳ → auto logout → /login
```
