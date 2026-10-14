# 5. Sơ đồ máy trạng thái (State Machine)

## 5.1. Graph LangGraph UNDERSTAND — luồng điều khiển

```mermaid
stateDiagram-v2
    direction TB
    [*] --> load_context: start_understand_run<br/>(thread_id=understand-{run_id})

    load_context --> planner

    state "Vòng điều tra (budget cap: ≤8 vòng, ≤18 LLM calls)" as loop {
        planner --> dispatch: action = tool
        dispatch --> evaluator: ToolSpec từ TOOLS registry
        evaluator --> planner: evidence → đủ chưa?
    }

    planner --> synthesizer: action = synthesize<br/>(hoặc bị ép bởi budget/iteration cap)
    synthesizer --> persist_insight: InsightDraft<br/>(whitelist evidence phía server)

    persist_insight --> WAITING: ✂ interrupt()<br/>status=pending
    WAITING --> apply_decision: Command(resume) từ POST /decision

    apply_decision --> planner: investigate_more<br/>(final_status=investigating → vòng lặp điều chỉnh)
    apply_decision --> DONE: approve | edit | reject
    DONE --> [*]: run completed

    note right of WAITING
        CỔNG HITL #2
        Trạng thái graph được persist trong
        4 bảng checkpoint (AsyncPostgresSaver)
        → server có thể restart, quyết định đến sau
        vẫn resume được
    end note
```

## 5.2. Trạng thái Insight (Cổng #2)

```mermaid
stateDiagram-v2
    direction LR
    [*] --> pending: persist_insight (graph tạo)

    pending --> approved: approve
    pending --> edited: edit<br/>(re-sanitize text người dùng)
    pending --> rejected: reject
    pending --> investigating: investigate_more

    investigating --> pending: synthesizer tạo insight mới<br/>(cùng run, idempotent run_id+title)

    approved --> edited: PATCH /api/insights/{id}<br/>→ insight_reviews action=edit
    approved --> [*]
    edited --> [*]
    rejected --> [*]

    note right of investigating
        Mọi chuyển tiếp ghi 1 dòng insight_reviews
        + decision_logs (subject=insight)
    end note
```

## 5.3. Trạng thái Action (Cổng #3)

```mermaid
stateDiagram-v2
    direction LR
    [*] --> proposed: act_agent act-v2<br/>(priority_score tất định)

    proposed --> edited: PATCH human_* override<br/>+ recompute_priority
    proposed --> accepted: PATCH (chấp nhận nguyên vẹn)
    proposed --> rejected: PATCH

    edited --> [*]
    accepted --> [*]
    rejected --> [*]

    note right of proposed
        decision_support JSONB bất biến (snapshot AI),
        giá trị AI giữ nguyên khi người dùng override
        + log_decision(subject=action)
    end note
```

## 5.4. Trạng thái Import (Cổng #1)

```mermaid
stateDiagram-v2
    direction LR
    [*] --> pending: upload CSV

    pending --> profile_ready: profile_csv_for_import
    profile_ready --> mapping_generating: POST mapping/proposal
    mapping_generating --> mapping_review: LLM mapping_proposal<br/>(✂ CỔNG #1 chờ duyệt)
    mapping_generating --> failed: LLM lỗi

    mapping_review --> importing: POST mapping/decision
    importing --> imported: execute_import_background<br/>(rows đã sanitize)
    importing --> failed: lỗi import
    profile_ready --> cancelled: POST cancel
    mapping_review --> cancelled: POST cancel

    imported --> [*]
    failed --> [*]
    cancelled --> [*]
```

## 5.5. Trạng thái AnalysisRun

```mermaid
stateDiagram-v2
    direction LR
    [*] --> running: POST /api/analysis/runs
    running --> completed: hết rows pending
    running --> failed: >50% item lỗi
    running --> cancelled: cancel_requested_at
    completed --> [*]
    failed --> [*]
    cancelled --> [*]

    note right of running
        Commit theo chunk · processed_count tăng đơn điệu
        · item lỗi được trả lại (analysis_run_id=NULL)
    end note
```

## 5.6. Trạng thái ProductSchema & Taxonomy

```mermaid
stateDiagram-v2
    direction LR
    state ProductSchema {
        [*] --> draft
        draft --> active: PROMOTE (Cổng #1 duyệt mapping)
        active --> superseded: phiên bản mới
    }
    state Taxonomy {
        [*] --> tr_active: canonical · đang dùng
        [*] --> pending_review: emerging (AI phát hiện)
        pending_review --> tr_active: approve
        pending_review --> merged: merge
        pending_review --> rejected: reject
    }
```

## 5.7. Trạng thái phiên làm việc FE (Activity Center)

```mermaid
stateDiagram-v2
    direction LR
    [*] --> idle
    idle --> running: import/analysis đang chạy
    running --> completed
    running --> needs_attention: Cổng #1 chờ duyệt mapping
    running --> failed
    completed --> idle
    failed --> idle
    needs_attention --> idle
```
