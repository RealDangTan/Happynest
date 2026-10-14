# 2. Sơ đồ luồng dữ liệu (Data Flow)

## 2.1. DFD mức 0 — Bối cảnh

```mermaid
flowchart LR
    NGUON(["Nguồn: CSV phản hồi<br/>+ nhập tay"])
    USR(["Người dùng"])
    H0(["Hệ thống AI Feedback Agent<br/>0. Thu thập · phân loại · phát hiện vấn đề"])
    DB[("Kho dữ liệu<br/>Supabase PG + pgvector")]
    LLM(["Dịch vụ LLM/Embeddings"])

    NGUON -->|"file CSV / record"| H0
    USR -->|"tham số, quyết định HITL"| H0
    H0 -->|"insight, báo cáo, cụm, hành động"| USR
    H0 <--> DB
    H0 <-->|"prompt đã sanitize / vector"| LLM
```

## 2.2. DFD mức 1 — Các tiến trình chính

```mermaid
flowchart TB
    USR(["Người dùng"])

    P1["1.1 Profile CSV<br/>(import_service + profiler)"]
    P2["1.2 LLM mapping proposal<br/>(llm_mapper · call_type=schema_map)"]
    P3["1.3 Import rows<br/>(sanitize Presidio)"]
    P4["1.4 Nhập tay<br/>(ingest_service)"]

    P5["2.1 Chạy phân tích<br/>(analysis_runner · BackgroundTasks)"]
    P6["2.2 Enrich LLM closed-set<br/>(enricher v3 · taxonomy)"]
    P7["2.3 Embedding<br/>(embedder · 1536d)"]
    P8["2.4 Phân cụm + naming<br/>(clustering · HDBSCAN cosine)"]
    P9["2.5 Trend/Spike/Emerging<br/>(compute_trend)"]

    P10["3.1 Agent UNDERSTAND<br/>(LangGraph planner→tools→evaluator→synthesizer)"]
    P11["3.2 Cổng #2 duyệt insight<br/>(interrupt)"]

    P12["4.1 act_agent act-v2<br/>+ 18 best practices"]
    P13["4.2 Cổng #3 điều chỉnh"]
    P14["4.3 Impact check"]

    T1[("D1: feedback<br/>raw_content + feedback_text<br/>ai_analysis + embedding")]
    T2[("D2: clusters")]
    T3[("D3: insights + evidence")]
    T4[("D4: actions + impact_checks")]
    T5[("D5: decision_logs<br/>bộ nhớ quyết định")]
    T6[("D6: llm_call_logs<br/>+ Langfuse trace")]

    USR --> P1 --> P2 -->|"✂ Cổng #1"| P3
    USR --> P4
    P3 --> T1
    P4 --> T1
    T1 --> P5 --> P6 --> P7 --> T1
    T1 --> P8 --> T2
    P8 --> P9 --> T2
    T1 --> P10 --> T3
    P10 --> P11 -->|"✂"| T3
    T3 --> P12 --> T4
    P12 --> P13 --> T4
    T4 --> P14 --> T4
    P13 --> T5
    P11 --> T5
    P6 & P7 & P8 & P10 & P12 & P2 -.->|"metadata gọi LLM"| T6
```

## 2.3. Ranh giới PII (PII boundary)

Nguyên tắc khóa luận: **nội dung thô không bao giờ ra khỏi ranh giới sanitize**.

```mermaid
flowchart LR
    subgraph RAW["Vùng dữ liệu thô — chỉ trong DB"]
        RAWC["raw_content<br/>(không bao giờ xuất hiện ở<br/>API response, prompt, log, trace)"]
    end

    SAN["presidio_service.sanitize()<br/>Presidio + StanzaNlpEngine(vi)<br/>+ regex email/url/ip/phone-VN/CCCD<br/>→ placeholder <TYPE>"]

    subgraph SAFE["Vùng dữ liệu đã sanitize — được phép đi ra"]
        TXT["feedback_text / sanitized_content"]
        PROMPT["Prompt LLM"]
        TRACE["Langfuse trace (≤2000 ký tự)"]
        APIR["API response"]
        LOG["llm_call_logs (chỉ metadata,<br/>không bao giờ có nội dung)"]
    end

    RAWC --> SAN --> TXT
    TXT --> PROMPT
    TXT --> TRACE
    TXT --> APIR
    SAN -.->|"pii_detected + pii_entities<br/>ghi nhận vào feedback"| RAWC
```

- Prompt do con người cung cấp (lý do duyệt/sửa tại Cổng #2, text chỉnh insight) cũng **bắt buộc re-sanitize** trước khi persist (`apply_decision`, `resume_with_decision`).
- `llm_call_logs` chỉ lưu `call_type, prompt_version, model, latency_ms, tokens, error` — không bao giờ lưu prompt/response.
