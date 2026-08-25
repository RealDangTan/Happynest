# FE-04 — Màn Analysis (trigger · polling · results) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay placeholder `/analysis` bằng màn chạy batch phân loại: trigger có confirm, progress poll theo `?run=<uuid>`, bảng kết quả từng item.

**Architecture:** 3 khối dọc theo [UF-03](UF-03-spec-analysis-runs.md): trigger Card → progress block (chỉ khi có `?run=`) → results Table của run. Polling = TanStack Query `refetchInterval` trả `false` khi hết `running`. BE đã ship Phase 09 — KHÔNG đụng backend.

**Tech Stack:** Next.js App Router, TanStack Query v5, shadcn/ui (bổ sung `alert-dialog`, `progress`), sonner.

**Spec:** [UF-03-spec-analysis-runs.md](UF-03-spec-analysis-runs.md) · routes thật đã verify: `backend/app/api/routes/analysis.py` + `schemas/analysis.py`.

## Global Constraints

- Ranh giới PII như mọi màn (chỉ `sanitized_content`).
- Trigger tốn LLM credit → LUÔN qua AlertDialog confirm; nút disable khi run đang theo dõi ở trạng thái running.
- Trạng thái sống trên URL `?run=` — refresh/share giữ nguyên; KHÔNG tự đổi URL ngoài lúc nhận `{run_id}` và bấm "Chạy lại".
- "Chạy lại phần còn lại" = tạo run MỚI (copy nút nói "Chạy lại", không phải resume).
- Poll lỗi mạng giữa chừng: giữ progress cuối + toast chung; TanStack Query tự retry.
- Item nhãn null → hiển thị "…đang xử lý", không bao giờ hiện chữ "null".

---

### Task 1: Data layer — types + hooks

**Files:** Create `frontend/hooks/use-analysis.ts`; Modify `frontend/lib/types.ts`; CLI `pnpm dlx shadcn@latest add alert-dialog progress`

- [ ] Types: `RunProgress { id, status: "running"|"completed"|"failed", processedCount?…}` — bám snake_case BE: `{id, status, processed_count, total_count, error, started_at, completed_at}`; `TriggerRunResult { run_id }`.
- [ ] Hooks:
  - `useRunProgress(runId)` — queryKey `["analysis","run",runId]`, `refetchInterval: (q)=> q.state.data?.status === "running" ? 4000 : false`, staleTime 0.
  - `useRunResults(runId, page)` — PAGE_SIZE 20, envelope FeedbackListResponse, `keepPreviousData`.
  - `useTriggerRun()` — mutation POST `/api/analysis/runs` → `{run_id}`; onSuccess invalidate `["analysis"]`.

### Task 2: Trang `/analysis`

**Files:** Modify `frontend/app/(app)/analysis/page.tsx` (thay placeholder)

- [ ] Landing không `?run=`: Empty giải thích + CTA mở AlertDialog confirm → Confirm → POST → `router.replace("/analysis?run="+run_id)`.
- [ ] Khối progress khi có `?run=`: Badge trạng thái + Progress `%` + "x/y đã xử lý"; completed → toast xanh 1 lần; failed → Alert destructive kèm `error` + nút "Chạy lại phần còn lại" (POST mới → thay `?run=`).
- [ ] Results table: Nội dung/Nguồn/Mức độ/Duyệt/Cảm xúc/Confidence; nhãn null → "…đang xử lý"; row link `/feedbacks/{id}`; phân trang Trước/Sau.
- [ ] Nút trigger disable khi `status==="running"`; Suspense bọc vì dùng `useSearchParams`.

### Task 3: Verify + đóng bài

- [ ] Build xanh; vitest xanh.
- [ ] Live: POST run thật với row chưa classify còn lại từ FE-03b (đúng 1 item) → thấy progress → completed → results có nhãn; api-checklist cập nhật 3 dòng analysis ⬜→✅.
- [ ] Board FE-00 tick FE-04 + log tiến độ; commit từng task.
