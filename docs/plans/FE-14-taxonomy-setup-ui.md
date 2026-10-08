# FE-14 — Taxonomy Setup UI (Listen AI re-spec)

> Nguồn: series BE 30–34 (specs 2026-10-07) · 1 phase duy nhất · FE skill đã load (frontend-design + shadcn) · design system shadcn token-only, PageHeader, sonner, react-query.

## Mục tiêu

Đưa 3 chức năng AI Listen mới lên UI: (1) GPT sinh taxonomy → human duyệt → Active v1, (2) GPT đề xuất topic từ pool uncategorized → human nhận → v2, (3) vòng re-enrich. Kèm hiển thị enrich v3 (emotions/intent/uncategorized) trên các mặt feedback.

## Tasks

- [x] Task 1 — Types + pure logic: `lib/types.ts` mở rộng `AiAnalysis` v3 (emotions, intent, topic_confidence, uncategorized, topic_scores, emotion_scores, taxonomy_version) + types Taxonomy/Proposal/Recommendation; `lib/taxonomy.ts` (gộp proposal phẳng → tree, đếm selected, merge rename) + `lib/taxonomy.test.ts` (vitest).
- [x] Task 2 — `hooks/use-taxonomy.ts`: useTaxonomy (tree GET), useGenerateProposal, useApplyProposal, useRecommendTopics, useApplyRecommendations, useReEnrichUncategorized (react-query + apiFetch, invalidate đúng khóa).
- [x] Task 3 — Trang `/taxonomy` (LISTEN group): PageHeader + thẻ taxonomy hiện tại (tree + slug mono + badge version) + dialog Generate (product_type/use_case/persona/sample_size, AlertDialog xác nhận tốn phí trước khi gọi) → bảng review proposal (checkbox chọn, sửa tên inline) → Áp dụng; thẻ Đề xuất chủ đề (evidence + ≤3 ví dụ trích nguyên văn, chọn + nhận); thẻ Uncategorized (count + nút "Xoá nhãn & enrich lại" + hướng dẫn sang /vault chạy analysis).
- [x] Task 4 — Nav: `lib/navigation.ts` thêm `{ href: "/taxonomy", label: "Taxonomy", icon: ListTree }` vào LISTEN.
- [x] Task 5 — Feedback v3: vault (badge UNCATEGORIZED ở ô Chủ đề + emotions/intent ở detail dialog) + `/feedbacks/[id]` (chips emotions/intent + uncategorized).
- [x] Task 6 — Verify: `pnpm typecheck` + `pnpm test` + `pnpm build`; walkthrough live /taxonomy với BE thật (generate → apply → recommend → re-enrich); api-checklist cột "Trên FE" cho 5 endpoint taxonomy + re-enrich.

## Kết quả verify (2026-10-08)

- typecheck sạch · vitest 45/45 · `pnpm build` OK (route /taxonomy vào build).
- Live walkthrough (agent-browser, product "Demo AI"): Generate (gpt-4o-mini) → 15 chủ đề review → Áp dụng → 12 canonical tạo (3 node GPT trùng tên cha tự dedupe) → badge v2 → nút Recommend + paid-gate → pool trống không tốn LLM → Re-enrich chạy. Screenshots: `docs/e2e-screenshots/fe14/`.
- Fix phát hiện khi walkthrough: BE `ProductOut` thiếu `taxonomy_version` (badge luôn v1) + FE chưa invalidate `products`; React key trùng khi GPT trả con trùng tên cha; thiếu nút trigger Recommend (đã thêm vào header card taxonomy).

## Verify

```bash
pnpm typecheck && pnpm test && pnpm build   # từ frontend/
```
