# Handoff: Chuẩn hóa taxonomy tiếng Anh canonical + name_vi hiển thị (đảo quyết định 2026-10-22)
- Date: 2026-10-23
- From: zcode
- To: any
- Branch / worktree: codex/activity-center (KHÔNG commit — working tree dùng chung)
- Milestone: Delivery — taxonomy language consistency (owner directive 2026-10-23: "taxonomy lúc Anh lúc Việt trông đần — chuẩn hóa tiếng Anh hết, UI vẫn tiếng Việt")
- Status: done

## Done
- Contract MỚI: `taxonomies.name` = tiếng Anh canonical (codebook cho classifier), cột mới `taxonomies.name_vi` = tiếng Việt hiển thị; mọi display dùng `name_vi ?? name`.
- Migration `0023_english_canonical_names.py` (đã apply DB dev thật): thêm `name_vi`; mọi row cũ `name_vi = name` (hiển thị không đổi); 5 root seed đổi `name` về bộ EN gốc migration 0010 (AI Quality/Search/Account/Performance/Other), `name_vi` giữ tên Việt. Slug KHÔNG đụng (plan 31). Idempotent + downgrade khôi phục.
- BE `taxonomy_service.py`: `DEFAULT_ROOTS` → cặp (EN, VI); seed ghi cả 2; `apply_proposal` + `create_manual_node` lưu `name_vi` (bỏ trống → fallback `name`); `update_manual_node` nhận `name_vi` (None = giữ nguyên); `get_taxonomy_labels` trả `(slug, name, name_vi)`; `get_active_taxonomy_context` gửi kèm `name_vi` cho prompt; `sanitize_recommendations` không còn làm rơi `name_vi`; prompt generate + recommend lên **v4** (`name` danh từ tiếng Anh bắt buộc + `name_vi` bắt buộc khớp nghĩa; nguyên tắc PHÂN CÔNG TRỤC v3 giữ nguyên).
- BE schemas/routes: `ProposedTopic.name_vi`, `TopicRecommendation.name_vi`, `TaxonomyOut.name_vi`, `TaxonomyNodeCreateIn/UpdateIn.name_vi`; recommend/apply + nodes CRUD truyền `name_vi`; PATCH chấp nhận name_vi-only (422 khi thiếu cả 3 trường).
- BE enricher: llm block dòng `- slug — Name (vi: …)`; JEV `build_questions` nhận 3-tuple, câu hỏi topic nêu cả tên EN + VI (id trả về vẫn CHỈ slug — closed-set giữ nguyên).
- FE: `types.ts` (`name_vi` trên TaxonomyNode/ProposedTopic/TopicRecommendation), `hooks/use-taxonomy.ts` (create/update nhận name_vi), `lib/graph.ts` `topicLabeler` → `name_vi ?? name`, `lib/taxonomy.ts` `selectedProposalPayload` gửi name_vi (fallback name), `/taxonomy` (row hiển thị VI chính + EN mono phụ; form thêm/sửa 2 trường tên; proposal review 2 input EN/VI; select cha hiển thị VI), `/feedbacks` list + `[id]` detail chip chủ đề giờ qua labeler (hết hiện slug thô; title giữ slug), `/vault` filter Topic + sort theo tên VI.
- Tests: backend `test_taxonomy_governance` (DEFAULT_ROOTS EN + name_vi), `test_taxonomy_crud` (create với name_vi + labels 3-tuple + patch name_vi-only không bump), `test_enricher_unit`/`test_jev_client_unit` (fixture 3-tuple, assert gloss VI trong prompt), mới thêm case fallback name_vi null ở `lib/graph.test.ts` + payload name_vi ở `lib/taxonomy.test.ts`.
- Docs: `docs/decisions.md` entry 2026-10-23 (đảo quyết định 2026-10-22); `docs/api-checklist.md` cập nhật 5 row taxonomy (name_vi + FE vị trí).

## Evidence
- `uv run alembic upgrade head` → 0023; query DB thật: root `chat_luong_ai` → ("AI Quality", "Chất lượng AI"); node custom giữ nguyên hiển thị (name_vi = name).
- `uv run pytest -q -m "not integration"` → 163 passed; integration `test_taxonomy_governance + test_taxonomy_crud + test_taxonomy_generation + test_topic_recommendation` → 28 passed.
- FE: `npx tsc --noEmit` sạch; `npx vitest run` → 58 passed; eslint 0 error trên mọi file đổi.

## Not done / gaps
- Node custom tạo TRƯỚC 2026-10-23 vẫn có `name` tiếng Việt/lẫn lộn ở cả 2 trường (hiển thị đúng nguyên trạng, nhưng canonical chưa EN) — human sửa qua dialog sửa tên trên /taxonomy, hoặc regenerate taxonomy.
- `merge_theme` vẫn match topics theo NAME (trong khi `ai_analysis.topics` lưu slug từ plan 31) — bug tiền tồn tại, không thuộc phạm vi ngôn ngữ, chưa đụng.
- Chưa re-benchmark chất lượng classify sau khi đổi nhãn codebook sang EN+gloss VI (kỳ vọng ngang bằng hoặc tốt hơn).
- Vault editor (drawer sửa feedback) vẫn nhập topics dạng slug thô — giữ nguyên vì đó là dữ liệu cấp slug.

## Follow-up 2026-10-24 — prompt v5 + stratified sampling (cùng session, tiếp chỉ đạo owner)
- `_stratified_samples` (taxonomy_service): generate không còn lấy "N feedback mới nhất" — pool ≤1000 rows → gộp trùng văn bản (casefold) → ≤10 bucket thời gian đều → round-robin oldest→newest; trả kèm `corpus_stats` (pool/unique/duplicates/date_range/sources/buckets) vào payload prompt.
- Prompt generate **v5**: giải thích corpus_stats ("kiểm tra độ phủ, KHÔNG suy tần suất"), sample đã phân tầng (wave sự cố gần đây = MỘT chủ đề), chạy khi context TRỐNG (tự suy luận loại sản phẩm), quy tắc thuật ngữ nhất quán (name EN Title Case chuẩn ngành; name_vi không dịch word-by-word thuật ngữ phổ biến), checklist rà toàn bộ sample + thêm chiều "hỗ trợ khách hàng".
- `/api/taxonomies/generate` **422** "Chưa có phản hồi…" khi corpus rỗng (không đốt LLM). Recommend flow (`find_unclassified_pool`) giữ nguyên order desc — không đổi.
- FE: copy dialog generate + aside cập nhật (mẫu phân tầng/gộp trùng; context tùy chọn).
- Test: test_taxonomy_generation.py 13 passed (3 test mới: stratify+dedup+stats, 422 corpus rỗng trên product riêng). Docs: decisions.md 2026-10-24, api-checklist row /generate.

## Next steps
1. Owner regenerate taxonomy cho product thật để thấy bộ nhãn EN canonical + VI hiển thị mới (prompt v5 — stratified).
2. Nếu node cũ muốn chuẩn hóa: sửa trực tiếp trên /taxonomy (dialog sửa có đủ 2 trường) — không cần migrate lại.
