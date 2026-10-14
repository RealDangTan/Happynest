# 3. Sơ đồ trình tự — Nhập liệu, Phân tích, Phân cụm

## 3.1. Nhập CSV + Cổng HITL #1 (duyệt mapping)

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng (FE importer)
    participant BE as FastAPI (imports)
    participant PR as Profiler
    participant LLM as LLM (schema_map)
    participant PG as PostgreSQL
    participant D as storage/imports

    U->>BE: POST /api/imports (multipart CSV, product_id)
    BE->>PR: profile_csv_for_import()
    BE->>D: save_raw_import() (CSV gốc)
    BE->>PG: INSERT imports (status=profile_ready, column_profiles)
    BE-->>U: 201 ImportOut

    U->>BE: POST /api/imports/{id}/mapping/proposal
    BE-->>U: 202 {status: mapping_generating}
    BE->>LLM: build_mapping_proposal (background)
    LLM-->>BE: MAP|PROMOTE|SOURCE_META|IGNORE|AMBIGUOUS (+needs_human_review)
    BE->>PG: UPDATE imports (mapping_proposal JSONB, status=mapping_review)

    U->>BE: GET /api/imports/{id}/mapping
    BE-->>U: MappingProposalOut
    note over U: ✂ CỔNG #1 — con người xem & quyết định mapping

    U->>BE: POST /api/imports/{id}/mapping/decision
    BE->>PG: status=importing · log_decision(subject=schema_mapping)
    BE->>D: load_raw_import()
    BE->>BE: execute_import_background(): từng dòng sanitize → feedback_text
    BE->>PG: INSERT feedback (raw_content, feedback_text, pii_detected, data, source_meta)
    BE->>PG: UPDATE imports (status=imported, report)
    BE-->>U: FE poll GET /api/imports/{id} → status=imported
```

## 3.2. Batch phân loại + embedding (analysis_runner v3)

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng (FE vault/analysis)
    participant BE as FastAPI (analysis)
    participant BG as jobs/analysis_runner (BackgroundTasks)
    participant TZ as Taxonomy cache
    participant LLM as LLM (enrich v3)
    participant EMB as Embeddings API
    participant PG as PostgreSQL

    U->>BE: POST /api/analysis/runs/preview (scope)
    BE-->>U: AnalysisCostPreviewOut (chi phí dự kiến)
    U->>BE: POST /api/analysis/runs
    BE->>PG: INSERT analysis_runs (status=running, snapshot model/prompt)
    BE-->>U: 201 RunCreatedOut
    BE->>BG: run_analysis(run_id)

    loop đến khi hết row pending (commit mỗi chunk, hỗ trợ hủy)
        BG->>PG: _pick_chunk (analysis_run_id IS NULL hoặc claim của run này)
        BG->>BG: sanitize nếu feedback_text NULL (ranh giới PII)
        BG->>TZ: get_taxonomy_labels()
        BG->>LLM: enrich_feedback (closed-set: topic chỉ lấy từ taxonomy active)
        LLM-->>BG: topics, sentiment, emotions, intent, severity,<br/>safety_issue, ai_issue, confidence, rationale
        note over BG: prob < 0.60 → "uncategorized"
        BG->>PG: UPDATE feedback SET ai_analysis (JSONB)
        BG->>EMB: embed_texts (batch ≤2048, tenacity retry 4×)
        EMB-->>BG: vector 1536d
        BG->>PG: store_embedding (embedding, embedding_model, embedding_dim)
        BG->>PG: commit chunk · processed_count tăng đơn điệu
    end

    alt >50% item lỗi
        BG->>PG: analysis_runs.status=failed
    else hoàn tất / bị hủy
        BG->>PG: status=completed|cancelled
    end
    U->>BE: GET /api/analysis/runs/{id} (poll tiến độ)
```

Giai đoạn sau (`POST /api/analysis/re-enrich-uncategorized` + apply taxonomy v2) tạo **vòng lặp tiến hóa taxonomy**: nhãn "uncategorized" được reset, chạy lại enrich với taxonomy mới.

## 3.3. Phân cụm HDBSCAN + trend/spike

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng (FE clusters)
    participant BE as FastAPI (admin)
    participant CL as clustering service
    participant LLM as LLM (name_cluster)
    participant PG as PostgreSQL

    U->>BE: POST /api/clusters/run
    BE->>PG: SELECT feedback có embedding
    BE->>CL: split_embedded() → cluster_embeddings()
    Note over CL: HDBSCAN · metric=cosine<br/>CLUSTER_MIN_SIZE · noise → cluster_id=NULL
    CL->>PG: DELETE Cluster cũ → INSERT Cluster mới → re-assign feedback.cluster_id (transaction)

    loop mỗi cụm
        CL->>LLM: build_naming_payload (≤5 snippet đã sanitize)
        LLM-->>CL: name + summary (fallback _fallback_name)
        CL->>CL: compute_trend(members):<br/>growth_ratio (cap 9.99)<br/>is_spike: current ≥ min & ratio ≥ ngưỡng<br/>is_emerging: mới xuất hiện & ≥ min<br/>suggested_priority = 0.5·size + 0.3·spike/emerging + 0.2·high-critical
        CL->>PG: UPDATE clusters
    end

    BE-->>U: ClusterRunOut
    U->>BE: GET /api/clusters?sort=feedback_count|growth_ratio|recent
```

## 3.4. Xác thực JWT cookie (điều kiện tiên quyết của mọi trình tự trên)

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng
    participant FE as Next.js (login page)
    participant BE as FastAPI (auth)
    participant PG as PostgreSQL

    U->>FE: POST email + password
    FE->>BE: POST /api/auth/token (OAuth2PasswordRequestForm)
    BE->>PG: lookup user, pwdlib[argon2] verify
    BE->>BE: create_access_token (HS256, TTL 12h, claims sub+iat+exp)
    BE-->>FE: 200 + Set-Cookie access_token (httpOnly, SameSite=Lax)
    FE->>BE: các request sau: cookie tự động kèm theo
    BE->>BE: get_current_user → 401 nếu token thiếu/sai/hết hạn<br/>mọi tài khoản dùng chung dữ liệu
    FE->>BE: DELETE /api/auth/logout khi 401 → chuyển /login
```
