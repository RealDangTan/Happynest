# Plan 26 — ACT Agent + Priority Matrix + Gate #3

> Nguồn thiết kế: VoC OS plan §44–52, §61 · Migration **0012** · Blocked by: 25.
>
> **Lệch thực thi 2026-08-28:** routing + generate + estimate GỘP 1 call LLM duy nhất (`act_generate`, service `act_agent.py`) thay vì 3 node riêng — kiềm chế tín dụng, trách nhiệm vẫn tách bạch trong output schema (relevance/recommendation/estimates). Formula §49 vẫn 100% deterministic server-side.

## Mục tiêu

Từ insight đã approved sinh candidate actions theo 8 business functions, chấm điểm impact/effort/urgency/confidence, tính priority bằng công thức deterministic (LLM không tự tính priority), vẽ priority matrix, human override (Gate #3) với logging.

## Tasks

### Task 1 — Migration 0012
- [x] Enum `business_function` (MARKETING, LEGAL, DESIGN, FINANCE, ENGINEERING, OPERATION, SALES, SUPPORT — §45).
- [x] `actions` (id, insight_id FK CASCADE, function business_function, recommendation TEXT, rationale TEXT, impact int 1–10, effort int 1–10, urgency int 1–10, confidence float, priority_score float, human_impact/human_effort/human_urgency nullable, override_reason TEXT nullable, status proposed|edited|accepted|rejected, created_at).

### Task 2 — Package `backend/act_agent/`
- [x] `router.py`: LLM function relevance routing (call_type='act_route') — relevance ≥ 0.5 → generate; skip không force đủ 8 functions (§47).
- [x] `recommender.py`: per relevant function sinh candidate action (call_type='act_generate') — action + rationale; KHÔNG re-read feedback rows, chỉ consume approved insight (§46).
- [x] `scorer.py`: LLM estimate impact/effort/urgency/confidence (call_type='act_estimate') → **priority_score deterministic** `impact*0.4 + urgency*0.3 + confidence*10*0.2 + (10-effort)*0.1` — weights configurable trong config.py (`PRIORITY_WEIGHTS`) (§49).
- [x] Run một lần per insight, idempotent (rerun replace-all proposed actions chưa bị human chạm).

### Task 3 — Routes (Gate #3)
- [x] `POST /api/insights/{id}/actions/generate` — 409 nếu insight chưa approved/edited (ACT chỉ chạy trên approved insight §44).
- [x] `GET /api/insights/{id}/actions` — list + matrix grouping: quadrant theo X=effort, Y=impact (quick_wins | strategic | low_priority | reconsider, ngưỡng 5/5 §50).
- [x] `PATCH /api/actions/{id}` — edit text/scores; human_* columns ghi vị trí override (giữ agent value nguyên); recompute priority_score dùng human values nếu có; status edited (§51–52).
- [x] `POST /api/insights/{id}/actions` — human tự thêm action.
- [x] Mọi override + accept/reject → `decision_logs` hook (bảng tạo phase 27 — chờ phase 27, tạm log vào insight_reviews-style table? KHÔNG: phase 27 backfill; phase 26 chỉ ghi human_* + override_reason).

### Task 4 — Tests + DoD
- [x] Unit (LLM mock): routing skip irrelevant; priority formula đúng + weights config; override giữ agent value + recompute từ human value; 409 trên insight pending; matrix quadrant đúng.
- [x] DoD §72 Phase-6: approved insight → candidates đúng function, irrelevant skipped, human đổi scores/actions, portfolio saved.

## Verify

```bash
uv run pytest && uv run pytest -m integration
uv run alembic upgrade head
```
