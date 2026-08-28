# Plan 26 — ACT Agent + Priority Matrix + Gate #3

> Nguồn thiết kế: VoC OS plan §44–52, §61 · Migration **0012** · Blocked by: 25.

## Mục tiêu

Từ insight đã approved sinh candidate actions theo 8 business functions, chấm điểm impact/effort/urgency/confidence, tính priority bằng công thức deterministic (LLM không tự tính priority), vẽ priority matrix, human override (Gate #3) với logging.

## Tasks

### Task 1 — Migration 0012
- [ ] Enum `business_function` (MARKETING, LEGAL, DESIGN, FINANCE, ENGINEERING, OPERATION, SALES, SUPPORT — §45).
- [ ] `actions` (id, insight_id FK CASCADE, function business_function, recommendation TEXT, rationale TEXT, impact int 1–10, effort int 1–10, urgency int 1–10, confidence float, priority_score float, human_impact/human_effort/human_urgency nullable, override_reason TEXT nullable, status proposed|edited|accepted|rejected, created_at).

### Task 2 — Package `backend/act_agent/`
- [ ] `router.py`: LLM function relevance routing (call_type='act_route') — relevance ≥ 0.5 → generate; skip không force đủ 8 functions (§47).
- [ ] `recommender.py`: per relevant function sinh candidate action (call_type='act_generate') — action + rationale; KHÔNG re-read feedback rows, chỉ consume approved insight (§46).
- [ ] `scorer.py`: LLM estimate impact/effort/urgency/confidence (call_type='act_estimate') → **priority_score deterministic** `impact*0.4 + urgency*0.3 + confidence*10*0.2 + (10-effort)*0.1` — weights configurable trong config.py (`PRIORITY_WEIGHTS`) (§49).
- [ ] Run một lần per insight, idempotent (rerun replace-all proposed actions chưa bị human chạm).

### Task 3 — Routes (Gate #3)
- [ ] `POST /api/insights/{id}/actions/generate` — 409 nếu insight chưa approved/edited (ACT chỉ chạy trên approved insight §44).
- [ ] `GET /api/insights/{id}/actions` — list + matrix grouping: quadrant theo X=effort, Y=impact (quick_wins | strategic | low_priority | reconsider, ngưỡng 5/5 §50).
- [ ] `PATCH /api/actions/{id}` — edit text/scores; human_* columns ghi vị trí override (giữ agent value nguyên); recompute priority_score dùng human values nếu có; status edited (§51–52).
- [ ] `POST /api/insights/{id}/actions` — human tự thêm action.
- [ ] Mọi override + accept/reject → `decision_logs` hook (bảng tạo phase 27 — chờ phase 27, tạm log vào insight_reviews-style table? KHÔNG: phase 27 backfill; phase 26 chỉ ghi human_* + override_reason).

### Task 4 — Tests + DoD
- [ ] Unit (LLM mock): routing skip irrelevant; priority formula đúng + weights config; override giữ agent value + recompute từ human value; 409 trên insight pending; matrix quadrant đúng.
- [ ] DoD §72 Phase-6: approved insight → candidates đúng function, irrelevant skipped, human đổi scores/actions, portfolio saved.

## Verify

```bash
uv run pytest && uv run pytest -m integration
uv run alembic upgrade head
```
