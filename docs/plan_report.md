# PLAN REPORT — TL;DR

> Cập nhật: 2026-10-09. Tóm tắt trạng thái và nơi tìm bằng chứng sau khi dọn các plan đã hoàn tất.
> Các plan file đã xong đã bị XÓA khỏi `docs/plans/` (file nào đã commit vẫn lấy lại được từ git history: `git log --diff-filter=D -- docs/plans/`).

## Việc còn mở trong plans

Chỉ còn [plan 33 — Spike S7](plans/33-spike-s7-jev.md): script đã có (`168b3b4`), chưa chạy benchmark trực tiếp TypeSafe vì thiếu key. Đây là nghiên cứu **tùy chọn**, không chặn delivery; xem [`plans/00-index.md`](plans/00-index.md).

Quyết định 2026-10-08 dùng `MODEL_ENRICH=typesafe/jev-router` qua OpenRouter đã thay điều kiện tích hợp trực tiếp 34B. Các phần delivery của series 30–34 và FE-14 đều đã hoàn tất; không ghi S7 là PASS khi chưa có kết quả benchmark.

Nguyên tắc series: **GPT khám phá label space · JEV gán nhãn quy mô lớn · Người kiểm soát taxonomy.**

## ✅ Đã xong — đã xóa file plan (tóm tắt giữ lại)

| Series | Nội dung | Đóng khi |
|---|---|---|
| 01–12 | Backend foundation: env, spikes S1–S6, models/migrations, auth, ingestion, PII, LLM classify, embedder, analysis runner, test suite, DoD | 2026-08-25 |
| 13–16 | HITL LangGraph, clusters API, insights API, reports summary | 2026-08-25/26 |
| 17–20 | Agent module v1 — **superseded** bởi VoC OS rewrite | 2026-08-28 |
| 21–27 | VoC OS rewrite: LISTEN schema → taxonomy → analytics → UNDERSTAND → ACT → decision memory/KPIs (migrations 0008–0013, 115 test xanh) | 2026-08-28 |
| 28–29 | Navbar Activity Center + interactive agent terminal (3 gates + impact wizard) | 2026-08-31 / 09-07 |
| FE-01…13 | Toàn bộ frontend: scaffold, auth, feedback, analysis, HITL UI, clusters/insights/reports, register, landing, VoC OS prototype, 6 màn mới, shell topbar | 2026-09-15 |
| UF-01…05 | Screen specs (màn đã build xong, sau đó được thiết kế lại theo FE-12) | 2026-08-25 |
| delivery-\* | Execute plan + contracts + design spec của giai đoạn delivery (P0–P4 đóng, P6 superseded) | — |
| VoC OS plan (root) | Tài liệu thiết kế nguồn của series 21–27 | 2026-08-28 |
| 30–32 | Model routing (`2c02847`), taxonomy generation + migration 0016 (`736ac23`), enricher v3 (`ea9b389`); regression routing enrich sửa tại `7decb9e` | 2026-10-07/08 |
| 34 | Topic recommendation + apply + re-enrich + e2e (`86d5e22`); 34B bỏ theo quyết định dùng Jev qua OpenRouter | 2026-10-07/08 |
| FE-14 | Taxonomy Setup UI, review/apply, v3 chips và vòng re-enrich (`60aa7bf`) | 2026-10-08 |
| 35 | ACT v2: 18 practice cards / 7 lenses, evidence grounding, JSONB snapshot, Matrix/Stakeholders (`ea6535c`) | 2026-10-09 |

Bằng chứng thực thi (commit, verify, bài học) vẫn nằm nguyên trong [`handoffs/`](handoffs/) — không xóa.

ACT v2: 107 unit backend + 10 integration ACT/KPI + 49 frontend tests, typecheck/lint/build qua; walkthrough LLM thật 4/4 tình huống. Chi tiết và giới hạn ở [báo cáo ACT](act-best-practices-evaluation.md) và [handoff ACT](handoffs/2026-10-09-codex-act-best-practices.md). Migration development hiện ở `0017`.

## 📁 /docs sau dọn dẹp

```text
docs/
├── plan_report.md            ← file này — TL;DR trạng thái
├── api-checklist.md          ← bản đồ endpoint (cập nhật cùng mọi commit API)
├── decisions.md              ← decision log (mọi lệch kế hoạch ghi vào đây)
├── backend-foundation-report.md  ← bằng chứng chương luận văn
├── e2e_flow_report.md        ← kết quả e2e mới nhất (2026-10-05)
├── ai-agent-success-story.md ← narrative vision (tư liệu chương 1)
├── google-oauth-setup.md     ← hướng dẫn GCP khi làm Google login thật
├── sitemap-voc.md            ← bản đồ chức năng theo khung VoC
├── plans/                    ← 00-index + plan 33 nghiên cứu tùy chọn chưa chạy
├── handoffs/                 ← append-only, bắt buộc theo giao thức handoff
├── design/2026-09-15-ui-flow/ ← design source UI hiện tại
├── thesis/                   ← bản thảo luận văn (chương 0–9 + build docx)
├── evidence/                 ← sample dữ liệu bằng chứng (cluster sweep, HITL…)
├── e2e-screenshots/          ← ảnh bằng chứng e2e
├── feedback-mock/            ← dữ liệu mock cho e2e/demo
└── agent-control/            ← schema + editor luồng agent
```

## Việc còn mở ngoài plans

- Google OAuth thật (FE-08 để nút ghost — cần GCP credentials, xem `google-oauth-setup.md`)
- P5 delivery: data demo chuẩn bị bảo vệ + polish tùy chọn
- Luận văn: đang viết trong `thesis/`
