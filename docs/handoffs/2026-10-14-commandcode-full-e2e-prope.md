# Handoff — Full E2E trên acc zombiepoker55 + product "Prope" (agent CommandCode)

**Ngày:** 2026-10-14 · **Agent:** CommandCode (Claude) · **Mục đích:** chạy full pipeline LISTEN → UNDERSTAND → ACT qua API backend thật, datas mock `docs/feedback-mock/`, product **Prope** (`2dfd1e09-ec96-4fed-b15c-f90104cd4796`), reviewer = acc `zombiepoker55@gmail.com` (`6915ef96-…` — token tự ký bằng cùng SECRET_KEY như `/api/auth/token`, không đổi password).

## Kết quả E2E (đã verify bằng DB, không phải mock)

| Stage | Kết quả |
|---|---|
| Import (Gate #1) | **131/131 imported, 0 lỗi** — app-store 32 (tận dụng import treo từ 2026-10-11), google-play 35, facebook 32, twitter 32. Prope bootstrap **product schema v1**: `app_version, country, device, os_version, rating` (promote) |
| Analysis (classify+embed, jev-router) | **131/131 completed** — trước đó 2 run parallel làm cạn DB pool làm server treo (bài học: chạy tuần tự) |
| Clustering | **27 cụm, 170 assigned, 149 unassigned, 14 no-embedding** (hum toàn DB, không chỉ Prope) |
| UNDERSTAND | Run `2f684a1c` completed ~7 phút, 19 LLM calls (mistral — hết lỗi 400 sau khi đổi model). Insight **"Lỗi đăng nhập và xác thực"** (Apple-login loop 2.4.1, conf 0.8) → **Gate #2 APPROVED** (`d007e137`) |
| ACT + Gate #3 | 4 actions (ENGINEERING 7.8, SUPPORT 7.0, MARKETING 6.2, SALES 6.0) từ 18 curated practices `act-practices-v1`. Override impact ENGINEERING 8→6 (score 7.8→7.0, `status=edited`) + **accept** action SUPPORT → `accepted` |
| Reports | `/api/reports/summary?days=90` 200 OK (totals: 333 feedback Prope, 35 pii_detected) |

## Code/config đổi trong session này

1. **BUG FIX (uncommitted) — `backend/app/services/clustering.py`:** regression branch activity-center — `DELETE FROM clusters` chạy TRƯỚC `UPDATE feedback SET cluster_id=NULL` → FK `fk_feedback_cluster_id_clusters` violation; hoán đổi thứ tự. Cần chạy lại `pytest` và commit riêng.
2. **`backend/.env` (nhắc lại, từ session trước):** `MODEL_UNDERSTAND` + `MODEL_ACT` → `mistralai/mistral-small-24b-instruct-2501`.

## Vấn đề còn mở

- Insight cũ `2f68352b` (stale, `pending`, từ run cũ `40d68b4f` status=running mãi) của product này — chủ sở hữu quyết approve/reject/xoá.
- 3 action còn `proposed` — chờ Gate #3 của owner.
- Hiện tượng server-treo do parallel analysis runs (DB pool) — chưa có fix code; nên chạy 1 run/lần như FE.
- Chỗ understand vẫn lặp 8 iterations khi tool params sai (aggregate_feedback `{}` ×4 là evidence trong Gate #2) — 3 fix đã đề xuất trong session trước (enriched tool catalog / skip LLM call khi force / honor sufficient_evidence) chưa implement.

Assisted-by: CommandCode (Claude)
