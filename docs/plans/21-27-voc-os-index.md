# VOC OS REWRITE — PHÂN RÃ THỰC THI SERIES 21–27

> **Nguồn thiết kế:** [`../VoC Agent Operating System — Technical Implementation Plan.md`](../VoC%20Agent%20Operating%20System%20—%20Technical%20Implementation%20Plan.md) (75 mục, LISTEN → UNDERSTAND → ACT) · Quyết định re-plan: [`../decisions.md`](../decisions.md) entry 2026-08-28.
> **Supersede:** series 17–20 (agent module) + delivery P5/P6. Series trước: [`00-index.md`](00-index.md).
> **Cách dùng:** mỗi lần thực thi = đúng 1 phase. Tick checkbox trong file phase + cập nhật bảng dưới. Lệch kế hoạch → entry dated vào decisions.md TRƯỜNG TRƯỚC khi làm tiếp.

---

## 0. Quyết định đã chốt với owner (2026-08-28)

1. **Fresh reshape** — migration destructive OK, demo data bỏ, không migrate row.
2. **Products only** — không bảng `workspaces`; product = workspace.
3. **Strip & rewrite agent** — xoá `backend/happynest_agent/`, dựng UNDERSTAND mới từ spec.
4. **Backend first** — FE IA mới (§63 tài liệu nguồn) là series riêng sau khi BE ổn.

## 1. Sống sót / chết

- **Sống sót nguyên vẹn:** `presidio_service` (PII boundary), `llm_client` (fallback chain + tracing kép), `embedder`, `tracing`, `clustering` (HDBSCAN), auth pm|operations, `analysis_runs`, pattern LangGraph checkpointer/interrupt/budget-cap, pattern idempotency replace-all.
- **Chết:** `hitl_graph.py` + `routes/review.py` (feedback-level HITL), `happynest_agent/`, models `human_reviews`/`correction_examples`/`action_drafts`/`impact_checks`/`sources`, bảng `insights` cũ, `sources` registry.
- **PII boundary mới:** chỉ `feedback.feedback_text` (sanitized) ra khỏi biên; `raw_content` không bao giờ expose (không còn `?include_raw` — toggle OQ-8 chết theo feedback-level review).

## 2. Bảng phase

| # | File | Phạm vi | Migration | Blocked by | Status |
|---|---|---|---|---|---|
| 21 | [21-voc-core-reshape.md](21-voc-core-reshape.md) | products + imports + feedback JSONB zones + strip code chết | 0008 (destructive) | — | ✅ 2026-08-28 |
| 22 | [22-listen-schema-intelligence.md](22-listen-schema-intelligence.md) | product_schemas + profiler + LLM mapper + Gate #1 | 0009 | 21 | ✅ 2026-08-28 |
| 23 | [23-taxonomy-semantic.md](23-taxonomy-semantic.md) | taxonomies + emerging themes + ai_analysis reshape + runner | 0010 | 21 | ✅ 2026-08-28 |
| 24 | [24-analytics-engine.md](24-analytics-engine.md) | 8 MVP tools + query compiler (tool 9 dời plan 25) | — | 22, 23 | ✅ 2026-08-28 |
| 25 | [25-understand-agent.md](25-understand-agent.md) | evidence + insights mới + UNDERSTAND graph + Gate #2 | 0011 | 24 | ✅ 2026-08-28 |
| 26 | [26-act-agent.md](26-act-agent.md) | actions + ACT agent + priority matrix + Gate #3 | 0012 | 25 | ✅ 2026-08-28 |
| 27 | [27-decision-memory-kpis.md](27-decision-memory-kpis.md) | decision_logs + KPIs 3 gate + DoD sweep | 0013 | 21–26 | ⬜ |

```text
21 ── 22 ─┬─ 24 ── 25 ── 26 ── 27
 └───────┴─ 23 ──┘
```

## 3. Quy tắc chung

1. Mỗi phase ≥ 1 conventional commit, sign `Assisted-by: claude-code`.
2. Không Docker, không subagent, thực thi inline.
3. PII boundary như §1; mọi call LLM qua `llm_client.chat_structured` (temperature=0) → Langfuse + `llm_call_logs`.
4. Endpoint đổi → `docs/api-checklist.md` cùng commit.
5. Migration destructive → review CASCADE trước khi chạy trên Supabase; checkpoint tables LangGraph vẫn excluded qua `env.py`.
6. Verify mỗi phase: `uv run pytest` (+ `-m integration` khi đụng DB) + `uv run alembic upgrade head`.
7. DoD cuối series: E2E demo CSV qua đủ LISTEN → UNDERSTAND → ACT → `GET /api/reports/kpis` đủ 3 gate metrics.

## 4. Checklist tiến độ tổng

- [x] 21 Core reshape
- [x] 22 LISTEN schema intelligence
- [x] 23 Taxonomy + semantic
- [x] 24 Analytics engine
- [x] 25 UNDERSTAND agent
- [x] 26 ACT agent
- [ ] 27 Decision memory + KPIs + DoD
