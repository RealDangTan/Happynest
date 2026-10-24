# Handoff: Taxonomy generate/recommend prompt v2 — topic = thể loại tái sử dụng
- Date: 2026-10-22 (session chiều)
- From: zcode
- To: any
- Branch / worktree: codex/activity-center (working tree dùng chung, KHÔNG commit — nhiều WIP của session khác đang nằm lộn xộn)
- Milestone: Delivery — 4 nhóm route production (taxonomy generate/recommend, plan 31/34)
- Status: done

## Done
- Viết lại `_GENERATE_SYSTEM` + `_RECOMMEND_SYSTEM` trong `backend/app/services/taxonomy_service.py`, bump `PROMPT_VERSION_TAXONOMY`/`PROMPT_VERSION_RECOMMEND` lên "v2".
- Nguyên tắc codebook (thematic analysis/MECE/card sorting/ISO 25010/Maalej & Nabil): topic là thể loại tái sử dụng cho run phân loại TƯƠNG LAI; name = cụm danh từ ≤ 5 từ, cấm từ đánh giá; MECE phủ ≥ 90% sample; description bắt buộc = tiêu chí gồm/trừ; recommend ưu tiên gắn parent vào taxonomy hiện có.
- Payload generate thêm `existing_taxonomy` (names node active) — đề xuất bổ sung thay vì tạo nhánh trùng.
- Decision entry dated 2026-10-22 trong `docs/decisions.md` (gồm alternatives rejected + consequence).

## Evidence
- `uv run pytest tests/test_taxonomy_generation.py tests/test_topic_recommendation.py -q -m integration` → **16 passed** (210s, real PG).
- `uv run pytest -q` (unit) → 131 passed, **7 failed — PRE-EXISTING, không do thay đổi này**: `test_jev_client_unit.py` (5) + `test_enricher_unit.py::test_active_prompt_version_follows_engine` + `test_analysis_budget_unit.py::test_batch_receipt_chunks_23_items_into_three_provider_requests`. Nguyên nhân: WIP dang dở của session khác — `app/services/jev_client.py` + `tests/test_jev_client_unit.py` là file untracked chưa hoàn chỉnh, và enricher v4 (bỏ batch, owner 2026-10-22) làm vỡ test batch/jev-dispatch. Tôi không đụng các file này.
- Không đổi endpoint/schema/auth → api-checklist không cần cập nhật.

## Not done / gaps
- Taxonomy v1 xấu đang active trên product thực KHÔNG tự sửa (proposal stateless) — cần chạy generate → review → apply lại trên UI.
- `TopicRecommendation` vẫn không có `description` (recommend-apply drop description) — follow-up nếu muốn codebook đầy đủ ở đường recommend.
- Enricher `_taxonomy_block` vẫn chỉ hiện `slug — name`, không đọc description — follow-up A/B nếu muốn classifier nhìn tiêu chí gồm/trừ.

## Blocked / risks
- ⚠️ **`.pyc` stale**: working tree này có 889 thư mục `__pycache__` cũ gây traceback ảo (ImportError `enrich_feedback_batch` / NameError `strict_enrichment_schema` trỏ SAI dòng — nội dung file trên disk là đúng). Đã xoá toàn bộ bằng `uv run python -c "import pathlib, shutil; [shutil.rmtree(d, ignore_errors=True) for d in pathlib.Path('.').rglob('__pycache__')]"`. Nếu gặp traceback không khớp nội dung file → xoá `__pycache__` trước khi debug.
- Unit suite chưa xanh do WIP jev_client/batch của session khác — xem Evidence; đừng nhận là regression của thay đổi này.

## Next steps
1. Owner chạy `POST /api/taxonomies/generate` + review + `POST /api/taxonomies/apply` lại trên product thực để thay taxonomy v1.
2. Session đang làm jev_client hoàn thiện 7 unit test đang đỏ (xem Evidence).
3. (Optional) A/B: cho enricher đọc description trong `_taxonomy_block`; thêm `description` vào `TopicRecommendation`.
