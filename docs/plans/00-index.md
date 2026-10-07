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
| 31 | [31-taxonomy-generation-gpt.md](31-taxonomy-generation-gpt.md) | Migration 0016 + GPT generate proposal + human apply → Active Taxonomy v1 | 30 | ⬜ |
| 32 | [32-jev-enrichment-engine.md](32-jev-enrichment-engine.md) | Enricher v3 (LLM backend) + UNCATEGORIZED + strip classifier/auto-emerging + re-enrich endpoint | 30, 31 | ⬜ |
| 33 | [33-spike-s7-jev.md](33-spike-s7-jev.md) | Spike S7: Jev (TypeSafe) vs LLM baseline — gate bật `ENRICH_ENGINE=jev` | 32 | ⬜ |
| 34 | [34-topic-recommendation-gpt.md](34-topic-recommendation-gpt.md) | Recommend topics + apply → Taxonomy v2 + re-enrich loop + e2e (+34B jev wiring nếu S7 PASS) | 32 (34B: +33) | ⬜ |

Thứ tự cứng: **30 → 31 → 32 → 33 → 34**.

Checklist:

- [ ] 30 Model routing env
- [ ] 31 Taxonomy generation (GPT)
- [ ] 32 JEV enrichment engine
- [ ] 33 Spike S7 JEV
- [ ] 34 Topic recommendation + e2e
