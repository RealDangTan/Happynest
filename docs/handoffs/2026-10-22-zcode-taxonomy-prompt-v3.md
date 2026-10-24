# Handoff: Taxonomy prompt v3 — phân công trục + guard chương trình (fix round 2)
- Date: 2026-10-22 (session chiều, sau handoff 2026-10-22-zcode-taxonomy-prompt-v2.md)
- From: zcode
- To: any
- Branch / worktree: codex/activity-center (working tree dùng chung, chưa commit)
- Milestone: Delivery — taxonomy generate/recommend production (plan 31/34)
- Status: done

## Done (supersedes phần prompt của handoff trước — cùng agent, correction theo protocol)
- Bổ sung nguyên tắc PHÂN CÔNG TRỤC vào `_GENERATE_SYSTEM` + `_RECOMMEND_SYSTEM` (bump "v3"): taxonomy chỉ là trục CHỦ ĐỀ dạng danh từ ("Đồng bộ ghi chú", "Quảng cáo"); "chậm/quá nhiều/lỗi" thuộc severity/sentiment/intent — các field enrichment đã có riêng. Bảng chuyển hoá nhãn + ví dụ hình thức đúng ở domain KHÁC (app giao đồ ăn) chống anchor vocabulary.
- Guard chương trình `sanitize_recommendations` (service layer): drop topic trùng hiện có (casefold/whitespace-normalize), drop trùng nhau, bỏ neo parent khi parent==name hoặc parent lạ. Model chạy là gpt-4o-mini — prompt text một mình KHÔNG đủ (bằng chứng: round 2 đề xuất "Sync note-taking chậm" con của "Sync note-taking chậm").
- `get_active_taxonomy_context`: payload generate/recommend giờ gửi cấu trúc {name, slug, description, parent} thay vì list tên phẳng.
- Test mới `test_recommend_sanitizes_llm_output`. Giữ nguyên rule owner tự thêm vào prompt v2: name tiếng Việt, giữ thuật ngữ EN phổ biến.

## Evidence
- `uv run pytest tests/test_taxonomy_generation.py tests/test_topic_recommendation.py -q -m integration` → **17 passed** (187s, real PG).
- `uv run pytest -q` (unit) → **137 passed, 0 failed** (7 failure jev/batch trong handoff trước đã được session khác fix song song).
- Smoke LLM THẬT trên product "test" (b58b5c28-…, stateless, không ghi DB): generate 30 samples → 6 gốc danh từ thuần (Onboarding, Voice mode, Thanh toán, Chất lượng đầu ra AI, Quảng cáo, UI/UX) đủ description gồm/trừ; recommend pool=35 → "Sync ghi chú", "Chế độ offline", "Quản lý tài khoản", "Quảng cáo trong app", "Tính năng export chat" — không trùng tên, không parent==name. Đúng yêu cầu owner ("sync note taking chậm là problem, topic phải là note sync").

## Not done / gaps
- **Governance gap**: KHÔNG có endpoint rename/deactivate cho node canonical (review approve/merge/reject chỉ cho emerging). Taxonomy rác v1/v2 đang active trên product "test" không thể dọn qua API — follow-up nên thêm PATCH /api/taxonomies/{id} (rename, slug giữ nguyên) + deactivate/retire; nhớ cập nhật api-checklist + FE cùng commit.
- `TopicRecommendation` vẫn không có `description`; enricher `_taxonomy_block` vẫn chỉ hiện `slug — name` (follow-up A/B nếu cần).

## Next steps
1. Owner: chạy "Đề xuất bộ taxonomy mới" (generate) → review → apply trên product thật; taxonomy mới sẽ đúng dạng danh từ chủ đề. Topic rác cũ cần đường dọn (xem Governance gap).
2. Người giữ flag jev: unit suite đang xanh toàn bộ 137 — giữ vậy khi merge.
3. (Optional) A/B prompt v2 vs v3 qua llm_call_logs (prompt_version) cho chương trình luận văn.
