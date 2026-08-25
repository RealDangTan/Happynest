# FE-06 — Trang Clusters (P3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay placeholder `/clusters` bằng màn xem cụm chủ đề nối API THẬT (plan 14 đã ship): sort theo URL, card grid có nhãn mới nổi/tăng đột biến, trigger rebuild có confirm cảnh báo xoá sạch.

**Architecture:** GET `/api/clusters?sort=` + POST `/api/clusters/run` nằm trong `backend/app/api/routes/admin.py`, schema `schemas/cluster.py` (C1/C5). Sort là URL param `sort` (share được). Trigger = idempotent REBUILD (xoá insights + clusters cũ) → luôn qua AlertDialog. Insights/Reports/dashboard P4 CHƯA LÀM trong đợt này — BE vẫn stub 501 (plans 15–16), tách FE-06b khi BE sẵn sàng.

**Tech Stack:** Next.js App Router, TanStack Query v5, shadcn/ui (thêm `hovercard` cho từ điển thuật ngữ), sonner.

**Spec:** [UF-05-spec-clusters-insights-reports.md](UF-05-spec-clusters-insights-reports.md) Màn 1 · API thật: `admin.py` + `schemas/cluster.py`.

## Global Constraints

- **Cạm bẫy hiển thị (spec bắt buộc):** `is_emerging=true` với sentinel `growth_ratio=9.99` → hiển thị nhãn "Mới", TUYỆT ĐỐI không hiện "999%"/"9.99×"; `suggested_priority=null` → ẩn ô thay vì hiện null.
- Priority map thuần UI: ≥0.66 "cao" · ≥0.33 "trung bình" · còn lại "thấp".
- KHÔNG pagination — render hết list; chưa từng chạy → 200 `{"items":[]}` → Empty thân thiện, không lỗi đỏ.
- Confirm rebuild phải nói rõ: xoá TOÀN BỘ insights + clusters cũ rồi tạo lại; wording "Tạo lại" thay vì "Chạy".
- `unassigned_count > 0` là bình thường (noise HDBSCAN) — toast ghi rõ, không coi là lỗi.
- Data demo hiện ít nhóm chủ đề thật → kết quả có thể rỗng/noise cao (decisions 2026-08-26 dời evidence P5): empty state PHẢI đẹp.

---

### Task 1: Data layer + helper

**Files:** Create `frontend/hooks/use-clusters.ts`; Modify `frontend/lib/types.ts`; Modify `frontend/lib/format.ts`; CLI `pnpm dlx shadcn@latest add hovercard`

- [x] Types: `ClusterItem` đủ 15 field snake_case của ClusterOut; `ClusterRunResult {clusters_upserted, assigned_count, unassigned_count, duration_ms}`.
- [x] `useClusters(sort)` — GET `/api/clusters?sort=…`, queryKey `["clusters", sort]`, staleTime 30s.
- [x] `useRunClustering()` — POST `/api/clusters/run` mutation, onSuccess invalidate `["clusters"]`.
- [x] `formatRelative(iso)` vào lib/format — "hôm qua"/"n ngày trước"/"n giờ trước".

### Task 2: Trang `/clusters`

**Files:** Rewrite `frontend/app/(app)/clusters/page.tsx`

- [x] Header: tiêu đề + HoverCard "từ điển" (Cluster/Emerging/Spike/Tỷ lệ tăng/Mức ưu tiên — copy y hệt bảng spec) + Select sort 3 giá trị gắn URL param `sort` (`feedback_count` mặc định | `growth_ratio` | `recent`) qua `router.replace`.
- [x] Grid card mỗi cụm: name · summary line-clamp-2 · Badge "Mới nổi"/"Tăng đột biến" · dòng số liệu tổng/kỳ này/kỳ trước · tỷ lệ tăng (emerging → chữ "Mới"; ngược lại `${ratio.toFixed(1)}×`) · ưu tiên đề xuất map trên (null → ẩn) · footer ≤5 link sample `/feedbacks/{id}` + `last_seen` formatRelative.
- [x] Nút "Tạo lại phân cụm" (destructive outline) → AlertDialog cảnh báo rebuild → confirm gọi mutation; loading disable + Spinner.
- [x] States: Skeleton cards khi pending; items rỗng → Empty giải thích + CTA chính là nút tạo lại; thành công toast `{clusters_upserted} cụm · {assigned_count} phản hồi được gán · {unassigned_count} chưa gán (nhiễu/chưa embed)`.

### Task 3: Verify + đóng bài

- [x] Build xanh; vitest xanh.
- [x] Live: GET trước khi chạy → items rỗng đẹp; POST run thật → toast số liệu đúng response C5; list render card (hoặc rỗng nếu data demo noise — ghi rõ bằng chứng thô); sort đổi URL param.
- [x] api-checklist 2 dòng clusters ⬜→✅; board tick FE-06 (+ thêm dòng FE-06b cho Insights/Reports/dashboard P4 khi BE 15–16 ship); commit từng task.
