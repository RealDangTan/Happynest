# 4. Sơ đồ trình tự — Agent UNDERSTAND (Cổng #2) & ACT (Cổng #3)

## 4.1. UNDERSTAND agent — LangGraph + interrupt Cổng #2

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng (FE data-graph/reports)
    participant BE as FastAPI (agent)
    participant RT as graph_runtime
    participant G as LangGraph UNDERSTAND<br/>(AsyncPostgresSaver)
    participant TL as ToolBox (9 tools)
    participant LLM as LLM (plan/evaluate/synthesize)
    participant PG as PostgreSQL

    U->>BE: POST /api/agent/runs (question)
    BE->>BE: sanitize(question) (ranh giới PII)
    BE->>PG: INSERT analysis_runs (pipeline=understand-v1)
    BE->>RT: daemon thread · thread_id="understand-{run_id}"
    RT->>G: ainvoke(state)

    G->>G: load_context (product, schema_registry,<br/>field_coverage, taxonomy, top-5 clusters) — tất định
    loop investigation (budget cap: max 8 vòng / 18 lần gọi LLM)
        G->>LLM: planner → PlannerOut (action=tool|synthesize)
        alt action=tool
            G->>TL: dispatch ToolSpec (get_schema, profile_field, aggregate_feedback,<br/>compare_periods, segment_feedback, semantic_search (pgvector kNN),<br/>representative_feedback, inspect_cluster, search_similar_cases)
            TL->>PG: SELECT (query_compiler.base_query, MAX_RAW_FEEDBACK_PER_TOOL=30)
            TL-->>G: observation → INSERT evidence (type=tool_result)
            G->>LLM: evaluator → EvaluateOut (supports/contradictions/<br/>new_questions/sufficient_evidence)
            G->>G: quay lại planner
        else action=synthesize
            G->>LLM: synthesizer → InsightDraft<br/>(whitelist evidence phía server)
        end
    end

    G->>PG: persist_insight: INSERT insights (status=pending, idempotent theo run_id+title)
    G -->> G: ✂ interrupt(payload: insight_id, evidence,<br/>options: approve|edit|investigate_more|reject)
    note over G: Trạng thái graph lưu trong 4 bảng checkpoint<br/>— graph dừng, chờ con người

    loop FE poll
        U->>BE: GET /api/agent/runs/{id}
        BE->>PG: get_run_snapshot → pending_approval payload
        BE-->>U: insight draft + evidence + progress
    end

    U->>BE: POST /api/agent/runs/{id}/decision (option + reason)
    BE->>BE: sanitize(reason / edited_insight.title·finding)
    BE->>RT: resume_with_decision → ainvoke(Command(resume))
    G->>G: apply_decision
    alt edit
        G->>PG: insight.status=edited · re-sanitize text người dùng
    else investigate_more
        G->>G: final_status=investigating → quay lại planner (vòng lặp điều tra)
    else approve / reject
        G->>PG: insight.status=approved|rejected
    end
    G->>PG: INSERT insight_reviews · log_decision(subject=insight)
    G-->>BE: run completed → BE-->>U: {final_status, insights_created}
    U->>BE: GET /api/agent/runs/{id}/trace (chỉ metadata)
```

## 4.2. ACT agent — đề xuất hành động + Cổng #3

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng (FE matrix/stakeholders)
    participant BE as FastAPI (actions)
    participant ACT as act_agent (act-v2)
    participant LIB as act_practices<br/>(18 best practices)
    participant LLM as LLM (act_generate)
    participant PG as PostgreSQL

    Note over BE: Insight phải ở trạng thái approved/edited (đã qua Cổng #2)

    U->>BE: POST /api/insights/{id}/actions/generate
    BE->>ACT: generate_actions(db, insight)
    ACT->>LIB: load_act_evidence + build_decision_support
    LIB-->>ACT: catalog_for_prompt (LIBRARY_VERSION)
    ACT->>LLM: 1 structured call (call_type=act_generate)<br/>routing theo 8 BusinessFunction, ACT_RELEVANCE_THRESHOLD=0.5
    LLM-->>ACT: recommendations (impact/effort/urgency estimates)
    ACT->>ACT: priority_score() — CÔNG THỨC TẤT ĐỊNH,<br/>không bao giờ để LLM tính
    ACT->>PG: INSERT actions (status=proposed, decision_support JSONB bất biến)
    BE-->>U: ActionGenerateOut (kèm quadrant impact/effort)

    U->>BE: GET /api/insights/{id}/actions (priority matrix)
    note over U: ✂ CỔNG #3 — con người điều chỉnh

    U->>BE: PATCH /api/actions/{id} (human_impact/human_effort/human_urgency)
    BE->>BE: effective_scores() + recompute_priority()
    BE->>PG: UPDATE actions (giữ nguyên giá trị AI,<br/>override_reason, status=edited|accepted|rejected)
    BE->>PG: log_decision(subject=action, agent_value, human_value)
```

## 4.3. Đo tác động (vòng lặp đóng)

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng (FE reports)
    participant BE as FastAPI (impact-checks)
    participant PG as PostgreSQL

    U->>BE: POST /api/impact-checks/run (window_days)
    BE->>PG: đếm feedback liên quan trước/sau thời điểm hành động<br/>(insight → cluster → feedback)
    BE->>PG: INSERT impact_checks (before_count, after_count, delta_ratio)
    BE-->>U: ImpactRunOut (không gọi LLM)
    Note over U,BE: delta_ratio là KPI vòng lặp đóng:<br/>hành động đã đưa → vấn đề giảm chưa?
```
