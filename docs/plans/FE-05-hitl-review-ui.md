# FE-05 — HITL review UI (queue · approve/edit/reject · corrections) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nối HITL thật (plan 13 đã ship): shortcut vào hàng đợi `pending`, thanh hành động duyệt/sửa/từ chối + toggle raw trên trang detail, dialog sửa nhãn nuôi few-shot.

**Architecture:** Queue = tái dùng màn list với filter URL sẵn có (`?review_status=pending`) + nút shortcut. Hành động nằm ở `/feedbacks/[id]` (không đặt nút trên row — tránh duyệt bừa). Toggle raw là NGOẠI LỆ DUY NHẤT gọi `include_raw=true` (decisions 2026-08-26, OQ-8 resolved). Corrections áp cho mọi item đã classify bất kể review_status.

**Tech Stack:** Next.js App Router, TanStack Query v5, shadcn/ui (dialog + alert-dialog đã có), sonner.

**Spec:** [UF-04-spec-hitl-review.md](UF-04-spec-hitl-review.md) v1.0 · API thật: `backend/app/api/routes/review.py` + `schemas/hitl.py` (ReviewIn `{action, edited_content?, reason?}` · CorrectionIn chỉ field gửi mới cập nhật, ≥1 nhãn).

## Global Constraints

- PII boundary: chỉ toggle trong vùng review của detail-pending được gọi `include_raw=true` — grep toàn repo phải ra ĐÚNG 1 call site; mặc định TẮT mỗi lần mở trang; bật → Alert destructive cảnh báo; edit textarea luôn prefill bằng sanitized.
- Không undo review — copy confirm phải nói rõ không hoàn tác.
- Edit textarea rỗng client chặn trước (server cũng 422); 409 (đã xử lý / chưa classify) hiển thị Alert + invalidate, không crash.
- Mutation loading disable cả nhóm nút hành động (chống double-submit).
- Sau mutation thành công invalidate `["feedback", id]` + `["feedbacks"]`.

---

### Task 1: Data layer — hooks + types

**Files:** Create `frontend/hooks/use-review.ts`; Modify `frontend/lib/types.ts`

- [x] Type `CorrectionResponse = Feedback & { correction_recorded: boolean }`.
- [x] `useSubmitReview(id)` — POST `/api/reviews/{id}` body `{action, edited_content?, reason?}` → FeedbackOut; onSuccess invalidate `["feedback", id]`, `["feedbacks"]`, `["analysis"]`.
- [x] `useSubmitCorrection(id)` — POST `/api/corrections/{id}` body chỉ field khác null → CorrectionResponse; invalidate cùng cụm.
- [x] `useFeedbackRaw(id, enabled)` — GET `/api/feedbacks/{id}?include_raw=true`, `enabled` gate bởi toggle; queryKey riêng `["feedback-raw", id]`; **call site include_raw duy nhất của app**.
- [x] `usePendingNeighbors(id)` — GET list `review_status=pending&limit=50`, trả id kế tiếp sau `id` hiện tại (cho offer "Xem mục tiếp theo"); staleTime 15s.

### Task 2: Review bar + toggle raw tại `/feedbacks/[id]`

**Files:** Create `frontend/app/(app)/feedbacks/[id]/review-actions.tsx`; Modify `[id]/page.tsx` (gắn component khi `d.review_status === "pending"`)

- [x] Bar 3 nút: `Duyệt` primary 1-click (toast "Đã duyệt."), `Sửa nội dung` outline mở Dialog (Textarea prefill sanitized + Field reason tuỳ chọn; chặn submit rỗng), `Từ chối` destructive outline mở AlertDialog confirm kèm Field reason (copy nói rõ không hoàn tác).
- [x] Toggle "Hiện bản gốc" (Switch) trong bar, mặc định tắt; bật → Alert destructive "Đang hiển thị dữ liệu gốc chưa che PII — tắt trước khi share màn hình" + render `raw_content` từ `useFeedbackRaw`.
- [x] 409 → Alert "Mục này đã được xử lý trước đó." + tự invalidate detail; loading disable cả 3 nút.
- [x] Sau thành công: nếu `usePendingNeighbors(id)` có item kế → toast action "Xem mục chờ duyệt tiếp theo" (`router.push`).

### Task 3: Dialog sửa nhãn (correction)

**Files:** Create `frontend/app/(app)/feedbacks/[id]/correction-dialog.tsx`; Modify `[id]/page.tsx` (nút "Sửa nhãn" khi `d.categories != null`)

- [x] Form: categories chip editor (Input + Enter/Nút thêm → Badge xoá được; gợi ý = categories gom từ cache TanStack Query các list đã load); ai_issue/severity/sentiment Select enum + option "__keep__" = giữ nguyên; note Textarea tuỳ chọn.
- [x] Lưu disable đến khi ≥1 nhãn khác giá trị gốc; gửi body CHỈ gồm field đã đổi (+ note nếu có).
- [x] Toast thành công "Đã ghi nhận chỉnh sửa — sẽ giúp phân loại sau chính xác hơn."; lỗi 409 chưa classify → Alert hướng dẫn chạy Analysis.

### Task 4: Shortcut queue + Empty tích cực

**Files:** Modify `frontend/app/(app)/feedbacks/page.tsx`

- [x] Header thêm Button outline icon ShieldCheck "Chờ duyệt" → link `/feedbacks?review_status=pending`.
- [x] Khi filter `review_status=pending` đang bật và list rỗng → Empty tích cực "Không có mục nào chờ duyệt." + CTA "Xem tất cả phản hồi" xoá filter.

### Task 5: Verify + đóng bài

- [x] Build xanh; vitest xanh; `grep -r "include_raw" frontend/` ra đúng 1 call site.
- [x] Live: ingest 1 feedback chứa PII rõ (email + SDT) → chạy Analysis (pipeline detect PII → `requires_human_review` → `pending`) → thấy item trong queue; approve 1 mục; edit mục khác với nội dung chứa email giả → response hiển thị bản ĐÃ che; correction severity trên 1 mục đã classify; POST lại mục đã duyệt → thấy Alert 409.
- [x] api-checklist: 2 dòng reviews/corrections ⬜→✅; board tick FE-05 + log; commit từng task.
