# PLANS — ACTIVE BOARD

> Các series đã xong (01–29, FE-\*, UF-\*, delivery-\*) đã được dọn 2026-10-07 — tóm tắt tại [`../plan_report.md`](../plan_report.md); file gốc vẫn nằm trong git history.
> Quy tắc: lệch kế hoạch → entry dated [`../decisions.md`](../decisions.md) TRƯỚC khi làm tiếp. Không Docker · không subagent · PII boundary · endpoint đổi → `../api-checklist.md` cùng commit.

## Series Listen AI re-spec (30–34) — khai báo 2026-10-07 — ⚡ ACTIVE

> Nguồn: spec "AI trong Listen — Taxonomy Setup + JEV Enrichment" (owner 2026-10-07) + `decisions.md` cùng ngày.
> Nguyên tắc: **GPT discovers the label space · JEV applies the label space at scale · Human controls taxonomy evolution.**
> Supersede một phần plan 23 cũ (auto-emerging per-record); bảng taxonomies + governance giữ nguyên.

| # | File | Phạm vi | Blocked by | Status |
|---|---|---|---|---|
| 30 | [30-model-routing-env.md](30-model-routing-env.md) | `MODEL_*` routing mọi use case + `ENRICH_ENGINE`/`JEV_*` + health model map | — | ✅ 2026-10-07 |
| 31 | [31-taxonomy-generation-gpt.md](31-taxonomy-generation-gpt.md) | Migration 0016 + GPT generate proposal + human apply → Active Taxonomy v1 | 30 | ✅ 2026-10-07 (`736ac23`) |
| 32 | [32-jev-enrichment-engine.md](32-jev-enrichment-engine.md) | Enricher v3 (LLM backend) + UNCATEGORIZED + strip classifier/auto-emerging + re-enrich endpoint | 30, 31 | ✅ 2026-10-07 (`ea9b389`) |
| 33 | [33-spike-s7-jev.md](33-spike-s7-jev.md) | Spike S7: Jev (TypeSafe) vs LLM baseline — gate bật `ENRICH_ENGINE=jev` | 32 | 🔶 script xong (`168b3b4`), chờ `JEV_API_KEY` — siêu kỳ với jev-router qua OpenRouter thì không còn gate (decisions 2026-10-08) |
| 34 | [34-topic-recommendation-gpt.md](34-topic-recommendation-gpt.md) | Recommend topics + apply → Taxonomy v2 + re-enrich loop + e2e (+34B jev wiring nếu S7 PASS) | 32 (34B: +33) | ✅ 2026-10-07 (`86d5e22`) — 34B KHÔNG cần nữa: enrich dùng `typesafe/jev-router` qua OpenRouter (decisions 2026-10-08) |

Thứ tự cứng: **30 → 31 → 32 → 33 → 34**.

Checklist:

- [x] 30 Model routing env
- [x] 31 Taxonomy generation (GPT)
- [x] 32 JEV enrichment engine
- [ ] 33 Spike S7 JEV (script xong, chờ owner key — không còn chặn gì)
- [x] 34 Topic recommendation + e2e

## Series FE-14 — Taxonomy Setup UI — khai báo 2026-10-08 — ⚡ ACTIVE

> FE cho series 30–34 (Hard Rule 9: FE skill đã load). Chi tiết: [FE-14-taxonomy-setup-ui.md](FE-14-taxonomy-setup-ui.md).

| # | File | Phạm vi | Blocked by | Status |
|---|---|---|---|---|
| FE-14 | [FE-14-taxonomy-setup-ui.md](FE-14-taxonomy-setup-ui.md) | Trang /taxonomy (generate → review → apply, recommend, re-enrich) + feedback v3 chips + nav LISTEN | 30–34 | ✅ 2026-10-08 |

## ACT best practices — owner approved 2026-10-09

| # | File | Phạm vi | Status |
|---|---|---|---|
| 35 | [35-act-best-practices.md](35-act-best-practices.md) | 18 practice cards, act-v2 grounding, migration 0017, shared Matrix/Stakeholders analysis | ✅ 2026-10-09 — 107 unit + 10 integration + 49 FE tests; live 4/4; build passed |
