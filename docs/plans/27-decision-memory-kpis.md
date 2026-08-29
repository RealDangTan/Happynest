# Plan 27 — Decision Memory, Evaluation KPIs, DoD Sweep

> Nguồn thiết kế: VoC OS plan §52–53, §65–67 · Migration **0013** · Blocked by: 21–26.
>
> **Lệch thực thi 2026-08-28:** (1) E2E script `scripts/e2e_voc_flow.py` ĐÃ VIẾT nhưng chạy full-flow tốn LLM thật (mapping + classify + synthesize) — dành cho buổi demo với key còn tín dụng, KHÔNG chạy trong session tự động (quy tắc tín dụng §1). (2) KPI `mapping_accepted` đo từ decision_logs Gate #1 (mọi import qua gate đều human-approved → direct acceptance phản ánh qua tỷ lệ import vào đúng schema ở phase sau nếu cần chi tiết hơn).

## Mục tiêu

Thống nhất mọi quyết định human vào `decision_logs` (precedent/evaluation data, KHÔNG fine-tune sớm §53); KPIs đo đủ 3 HITL gate; đóng docs + sweep cuối series.

## Tasks

### Task 1 — Migration 0013 + decision_logs
- [ ] `decision_logs` (id, product_id FK, subject_type enum schema_mapping|taxonomy|insight|action, subject_id UUID, agent_value JSONB, human_value JSONB, reason TEXT, reviewer_id FK users nullable, created_at).
- [ ] Hooks ghi log tại: Gate #1 mapping decision (phase 22), taxonomy review (23), insight decision (25), action override/accept/reject (26).

### Task 2 — Closed-loop impact check (tái dựng)
- [ ] `services/impact.py` mới: action accepted (ticket-like ENGINEERING/SUPPORT recommendation) aged ≥ IMPACT_WINDOW_DAYS → đo volume feedback (cluster/topic) trước/sau → `impact_checks` tái tạo trong migration này (shape cũ 95c59dd làm tham khảo) + trigger: script CLI `scripts/run_impact_checks.py` (điền gap "no trigger" cũ).

### Task 3 — KPIs thuần SQL (build lại `reports.py`)
- [ ] Latency: time_to_listen (import→analysis), time_to_insight (run start→insight), time_to_action (insight approved→actions generate).
- [ ] LISTEN (§65): mapping direct-acceptance rate, edit rate (từ decision_logs subject_type=schema_mapping).
- [ ] UNDERSTAND (§66): insight approval rate, edit rate, rejection rate, evidence-grounding rate (insight có evidence refs non-empty), time-to-insight.
- [ ] ACT (§67): action acceptance/edit/rejection rate, impact agreement, effort agreement, matrix displacement (distance agent vs human vị trí — §67).
- [ ] Pattern giữ: thuần SQL, percentile_cont, 200 với null khi chưa đủ data (commit 95c59dd shape tham khảo).

### Task 4 — Docs sweep + DoD series
- [ ] `docs/api-checklist.md` viết lại TOÀN BỘ bảng endpoint theo surface mới (products, imports, mapping, taxonomies, feedback, clusters, agent, insights, actions, reports).
- [ ] README quickstart cập nhật flow LISTEN→UNDERSTAND→ACT; `docs/plans/21-27-voc-os-index.md` tick đủ; entry decisions.md đóng series.
- [ ] Handoff entry mới + FE rewrite series note (FE IA §63 — series riêng, out of scope).

### Task 5 — E2E acceptance
- [ ] Script `scripts/e2e_voc_flow.py`: seed product → upload demo CSV → Gate #1 approve → analysis run → clusters → understand run (question) → Gate #2 approve → actions generate → Gate #3 override → `GET /api/reports/kpis` đủ metrics non-zero.
- [ ] `uv run pytest` (unit + integration) xanh toàn bộ.

## Verify

```bash
uv run pytest && uv run pytest -m integration
uv run alembic upgrade head
uv run python scripts/e2e_voc_flow.py
```
