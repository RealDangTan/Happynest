# Handoff: Agent module plans 17–20 viết xong vào docs/plans (docs-only session)
- Date: 2026-08-26 (buổi tối, giờ local)
- From: claude-code
- To: any
- Branch / worktree: main (root — theo quy ước repo, không worktree)
- Milestone: docs/plans/17–20 (series Agent module) + đăng ký P6 trong delivery-execute-plan
- Status: done (planning only — KHÔNG có code backend/frontend nào bị đụng)

## Done
- 4 plan mới đúng khuôn nhà (§1 bối cảnh/verify · §2 mục tiêu+non-goals · §3 tasks checkbox · §4 acceptance+evidence · §5 blocker):
  `17-agent-substrate-demo-data.md` (migration 0007 + dataset demo ~650 row),
  `18-agent-toolbox.md` (5 tool + registry + backfill insight embeddings),
  `19-agent-graph-hitl.md` (graph fully LLM-routed + budget/critic/risk-gate/interrupt + `/api/agent/*`),
  `20-closed-loop-kpis-demo.md` (impact check + `/api/reports/kpis` + demo script).
- `00-index.md`: thêm §5 bảng series 17–20 + dependency graph.
- `delivery-execute-plan.md`: hàng **P6** ở §1, lãnh thổ lane AGENT ở §2, checklist §4.
- `AGENTS.md`: bullet in-scope "Agent module series 17–20" trong CURRENT PHASE (không thay mission delivery).
- `decisions.md`: entry dated 2026-08-26 ghi toàn bộ quyết định + các lệch so với brainstorm 25/08.

## Evidence
- Recon thật trước khi viết: đọc 00-index, 13–16, FE/UF indexes, delivery spec/execute-plan, decisions (đủ), models enums/analysis_run/cluster/feedback/insight, `git log -12`, `git status`.
- Số 13–16 ĐÃ BỊ CHIẾM bởi series delivery → agent đánh số 17–20 (đây là chỗ "index hơi lệch" owner nêu).
- Phase 09 đã ship (không superseded như brainstorm tưởng) → thiết kế co-exist: agent run dùng `pipeline_version='agent-router-v1'`.

## Not done / gaps
- Chưa sửa `docs/ai-agent-success-story.md` / tạo `demo-script.md` — đó là Task 3 của plan 20 khi thực thi, không phải việc của phiên planning.
- Cố tình KHÔNG đụng (thuộc lane khác): `frontend/app/favicon.ico`, `skills-lock.json`, `.agents/skills/caveman/`, `docs/.obsidian/`, `docs/user-flows.*`.

## Blocked / risks
- Deadline ~2026-10-22 siết vì thêm P6: nếu trễ, hy sinh P5 polish trước (đã ghi trong hàng P6).
- Migration 0007 chain xuống head thật lúc mở phase (hiện dự kiến 0006).
- Phase 14 ĐÃ XONG (commit `3c03206`) nhưng data 22 row ra 100% noise (decisions 2026-08-26) — dataset planted của plan 17 là điều kiện để evidence clusters sống lại; executor 17 lưu ý mục Đồng bộ ở §1.

## Next steps
1. ~~Owner duyệt plans 17–20~~ ✅ owner duyệt 3 điểm 2026-08-26 (dataset ~650 row · budget 24 calls/run · auto-path không ghi insight_reviews); commit 8 path tường minh ngay sau đó (decisions.md đã lọt vào HEAD trước đó qua commit của lane khác — kiểm tra `git log` trước khi thắc mắc thiếu).
2. Kích hoạt plan 17 (migration 0007 + generator + import + classify + clusters/run) — giờ làm được NGAY vì phase 14 đã đóng.
3. Tuần tự 18 → 19 → 20; mỗi phase một session inline, tick index §5 sau mỗi phase.
4. Sau P6: roadmap FE màn approval agent (chưa có plan — cần UF spec bổ sung nếu owner muốn UI).
