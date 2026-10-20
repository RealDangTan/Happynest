# Architecture UML diagram set (PlantUML) delivered to docs/architecture

- **Date:** 2026-10-20
- **From:** zcode
- **To:** any
- **Branch/worktree:** `codex/activity-center` (working tree, NOT committed)
- **Milestone:** user request (no plan file) — "viết sơ đồ thiết kế hệ thống … tất cả dùng plantuml, xuất ảnh, để trong /docs/architecture"
- **Status:** done (superseded same day by the 41-diagram decomposition — see Update 2)

## Done

- Inspected repo via 3 parallel read-only explorations (backend models/routes/services/jobs, frontend routes/API calls, spikes/infra/docs contract) — diagrams match current code, not the pre-2026-10 docs that were deleted from the working tree.
- Created 18 PlantUML sources in `docs/architecture/plantuml/` + 18 rendered PNGs in `docs/architecture/image-asset/` + index `docs/architecture/README.md`:
  - Use case: tổng quát (01) + phần rã (02 tài khoản, 03 LISTEN/Gate#1, 04 phân tích/clustering, 05 UNDERSTAND/Gate#2, 06 ACT/Gate#3, 07 báo cáo/quan sát).
  - Hoạt động: 08 LISTEN pipeline (upload→Gate#1→batch classify+embed→HDBSCAN+trend), 09 UNDERSTAND (LangGraph loop + interrupt Gate#2) & ACT (Gate#3 + impact).
  - Lớp: 10 (15 models + PG enums + relationships, PII boundary note).
  - Trình tự: 11 đăng nhập, 12 import Gate#1, 13 batch phân tích + clusters, 14 agent UNDERSTAND Gate#2, 15 ACT Gate#3 + impact + reports.
  - Gói: 16 (backend/frontend packages + dependencies). Thành phần: 17. Triển khai: 18 (dev hiện tại + VPS mục tiêu systemd/Caddy, no-Docker).
- Diagram content is grounded in code: exact endpoint paths, model fields, LangGraph node names, budgets (8 iterations / 18 LLM calls), thresholds (HDBSCAN min 10, spike ≥2.0x, ACT weights 0.4/0.3/0.2/0.1).

## Evidence

- `java -jar plantuml-1.2024.8.jar -charset UTF-8 -checkonly *.puml` → `ALL OK` (exit 0) after 3 fixes (multi-line `[]` elements in 16; forward-ref usecase + guillemets in 05/10).
- Render: `java -DPLANTUML_LIMIT_SIZE=16384 -jar ... -Playout=smetana -o ../image-asset *.puml` → 18/18 PNG, exit 0. Toolchain: Java 1.8.0_371, jar at `D:\ATEMP\plantuml\plantuml-1.2024.8.jar` (outside repo), Smetana layout (no Graphviz on machine).
- Visual acceptance: 2 parallel visual-judge agents reviewed all 18 PNGs → 15 pass, 3 fail (10/16/17 clipped at right edge — PlantUML default 4096px canvas limit). Re-rendered with `-DPLANTUML_LIMIT_SIZE=16384`, re-judged the 3 → all pass (borders closed, sizes 4224/5426/5787 px).

## Not done / gaps

- Nothing committed — user did not ask for a commit; 36 files await `git add` under `docs/architecture/`.
- Deployment diagram marks the VPS side as "planned" (infra/systemd/ is only .gitkeep) and follows the locked Caddy decision; root README's nginx mention is stale (noted in diagram note + README).
- Minor cosmetic (judge-noted, non-blocking): long note connectors crossing dashed arrows in 01/04; bundled loop-back lines in 09.

## Blocked / risks

- None. If PNGs are regenerated without `-DPLANTUML_LIMIT_SIZE=16384`, diagrams 10/16/17 will clip again — the render command in `docs/architecture/README.md` includes the flag.

## Next steps

1. Review diagrams (start at `docs/architecture/README.md`); commit if satisfied — suggested: `docs(architecture): add PlantUML UML diagram set (18 diagrams)`.
2. If any diagram needs content changes, edit the matching `.puml` in `docs/architecture/plantuml/` and re-render (command in README).

## Update (same day, user request): all note boxes removed

- Removed all 14 `note ... end note` blocks from 12 sources (01–07, 10, 12, 14, 17, 18) and re-rendered with the same command (`-DPLANTUML_LIMIT_SIZE=16384 -Playout=smetana`). README updated accordingly (no PII-note / stale-nginx note references on diagrams; PII boundary stays documented in api-checklist/decisions).
- Visual re-check of the 12 affected PNGs: 11 pass immediately; `03-usecase-phanra-listen` initially clipped two actor-association arc crests at the top edge (Smetana bounding-box quirk, `nodesep`/`ranksep` did not help) — fixed by dropping `left to right direction` for that one diagram (default top-to-bottom layout, 3938x898); re-judged pass. Final state: 18/18 note-free PNGs pass.

## Update 2 (same day, user request): decomposition into 41 smaller diagrams

- User asked to decompose the 18-diagram set into smaller diagrams ("càng nhiều ảnh càng tốt"). Old files replaced/renamed; set is now **41 sources + 41 PNGs**, renumbered 01–41 grouped by diagram type (use case 01–13, activity 14–19, class 20–24, sequence 25–33, package 34–35, component 36–39, deployment 40–41). README table fully rewritten for the new numbering.
- Splits: use case by feature group (import/Gate#1, feedback, taxonomy, analysis runs, clusters, agent, Gate#2, ACT, Gate#3+impact, reports, observability); activity & sequence split per phase (import 1/2+2/2, analysis 1/2+2/2, understand 1/2+2/2, act 1/2+2/2); class split into tổng hợp + 4 domain parts with «từ sơ đồ NN» stub classes; package split backend/frontend; component into tổng quan + LISTEN + agents + observability; deployment into dev / VPS.
- Evidence: `grep note` clean across 41 files; `-checkonly` → `SYNTAX OK`; render `-DPLANTUML_LIMIT_SIZE=16384 -Playout=smetana` → 41 PNGs exit 0; visual judges (4 parallel + 2 repair rounds) → 41/41 pass. Repairs: 06 (boundary/label collisions → boundary declared before actors + includes routed sideways), 40/41 (arrow-text collisions + cloud-scallop barb artifacts → removed nested cloud containers, standalone database cylinder, actor connects upward from bottom).
- Still nothing committed (user has not asked).
