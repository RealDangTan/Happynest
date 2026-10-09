# Plan 33 — Spike S7: Jev (TypeSafe) vs LLM baseline

> Nguồn: thoả thuận spike-first (taste/decisions 2026-10-07) · Blocked by: 32 (baseline = enricher v3). **App code KHÔNG đổi.**

> **Trạng thái 2026-10-09:** script đã viết, spike chưa chạy. Đây là nghiên cứu tùy chọn, không còn chặn delivery: quyết định 2026-10-08 dùng `typesafe/jev-router` qua OpenRouter, bỏ tích hợp trực tiếp 34B. Baseline plan 32 đã hoàn tất; xem [tóm tắt](../plan_report.md) và [decision log](../decisions.md).

## PASS criteria (chốt trước, không đổi khi chạy)

1. Per-split accuracy (topic/sentiment/emotion/intent/severity) lệch ≤ 5 điểm % vs LLM baseline.
2. Calibration gap ≤ 0.10 (prob trung bình vs accuracy thực).
3. 0 unrecovered 429 (retry/backoff hoạt động).
4. p95 latency < 2s.
5. Cost ước tính ở quy mô batch (100 feedback/run) nằm trong ngân sách credit.

## Tasks

- [x] Task 1 — Pin vendor docs firsthand: `docs.typesafe.ai/api` + `/models` (`POST /v1/systemone`, model `jev-latest`; shape Noul/Choice/Score). Lệch thực tế → correction dated vào spike report + decisions.
- [x] Task 2 — `scripts/spikes/s7_jev_parity.py` theo convention S1–S6 (`_common.py`, docstring PASS criteria, results vào `scripts/spikes/results/` gitignored).
- [x] Task 3 — Thiết kế: **per-emotion binary Noul song song**; rỗng → `neutral`; **threshold sweep {0.5, 0.6, 0.7}**; metrics **micro-F1 + precision (+ accuracy)**; ground truth gán tay 1–2 label/record gồm mixed-emotion cases; data = `docs/feedback-mock/` + sample enrich thật; baseline = enricher v3 cùng bộ.
- [ ] Task 4 — Chạy spike (cần `JEV_API_BASE/JEV_API_KEY` owner điền); outcome (kể cả flat reject) → entry dated `decisions.md`. PASS → mở Phase 34B.

## Verify

```bash
uv run python ../../scripts/spikes/s7_jev_parity.py   # từ backend/, hoặc path tương đối repo root
```

Kết quả in bảng per-split + ghi file results; KHÔNG commit số liệu nhạy cảm.
