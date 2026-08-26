# FE-06b — Insights + Reports + Dashboard (P4) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. UI work bắt buộc invoke FE skill trước khi code (AGENTS.md hard rule 9).

**Goal:** Mount trọn bộ pha P4: thay 3 placeholder bằng màn Insights (C2/C6), Reports (C4) và Dashboard PM đầy đủ — số liệu thật, chart thuần tokens, mọi trạng thái rỗng/409 đều có hướng dẫn chứ không lỗi đỏ.

**Architecture:** BE vừa ship đủ: `GET/POST /api/insights(/run)` (`admin.py` + `schemas/insight.py`, engine `services/insight.py`) và `GET /api/reports/summary?days=` (`services/reports.py`). Dashboard TÁI DÙNG endpoint C4 của Reports (spec Màn 4 cấm phát minh endpoint riêng) — queryKey `["reports","summary",days]` dùng chung để cache share. Trigger insights là replace-all + call LLM vài chục giây → nút disable rõ ràng.

**Tech Stack:** Next.js App Router, TanStack Query v5, shadcn/ui — **KHÔNG thêm component/thư viện mới**: tabs/table/badge/card/skeleton/empty/sonner/hovercard đã đủ; chart vẽ bar thuần `div` + semantic tokens (8GB RAM, giữ bundle gọn — quyết định này thay dòng "component chart thêm lúc cần" trong spec).

**Spec:** [UF-05-spec-clusters-insights-reports.md](UF-05-spec-clusters-insights-reports.md) Màn 2–4 (đã resolve OQ-10/11) · API thật: `backend/app/api/routes/admin.py`, `schemas/insight.py`, `schemas/report.py`. Lệch kế hoạch → decisions trước khi làm tiếp.

## Global Constraints

- **`by_sentiment` render theo key THỰC TRẢ VỀ** (4 key gồm `mixed` — decisions 2026-08-26). Cấm hardcode 3 ô cảm xúc.
- **Sentinel 9.99** (`growth_ratio` cụm mới nổi) → chữ "Mới", không hiện "999%"/"9.99×" (giống `/clusters`); `suggested_priority=null` → ẩn ô.
- **Không control "duyệt insight"** trên UI — API đổi `review_status` insight không tồn tại (non-goal freeze; OQ-11: ẨN badge review_status).
- Evidence snippet là text ĐÃ sanitize, link sang `/feedbacks/{id}`; không hiển thị `raw_content`.
- Empty states phải thân thiện: chưa từng run insights → Empty + CTA; POST 409 → Alert đúng CHỮ SERVER + link `/clusters`; C4 lỗi → skeleton vùng đó + toast, phần còn lại vẫn dùng được.
- Mọi giá trị 0 hiển thị "0" bình thường — không coi là empty-state toàn trang.
- `days`/sort nằm URL search params qua `router.replace`; mutation xong invalidate đúng queryKey.
- Data demo có thể còn 0 cụm (phiên khác đang nạp demo dataset — kiểm tra git status/handoffs trước khi verify): kịch bản rỗng PHẢI verify được độc lập với dữ liệu.

---

### Task 1: Data layer

**Files:** Modify `frontend/lib/types.ts`; Create `frontend/hooks/use-insights.ts`; Create `frontend/hooks/use-reports.ts`

- [x] Types mới: `EvidenceItem {feedback_id, snippet, severity: Severity|null, created_at}` · `InsightItem {id, cluster_id: string|null, title, summary, suggested_action, evidence: EvidenceItem[], review_status}` · `InsightsRunResult {insights_generated, duration_ms, skipped}` · `ReportSummary {generated_at, window_days, totals{feedback_count, pending_review_count, pii_detected_count}, by_severity: Partial<Record<Severity,number>>, by_sentiment: Partial<Record<string,number>>, top_categories: {category,count}[], emerging: EmergingClusterItem[]}` với `EmergingClusterItem = Omit<ClusterItem, never>` (BE trả đủ shape C1 con, gồm `sample_feedback_ids`). *(thực thi: type alias trực tiếp `= ClusterItem`)*
- [x] `useInsights()` — GET `/api/insights`, queryKey `["insights"]`, staleTime 30s.
- [x] `useRunInsights()` — POST `/api/insights/run` mutation, onSuccess invalidate `["insights"]` + `["reports"]` (run mới đổi số liệu tổng hợp); KHÔNG tự nuốt error — caller đọc `ApiError.status===409` để render Alert.
- [x] `useReportSummary(days: 7|30|90)` — GET `/api/reports/summary?days=…`, queryKey `["reports","summary",days]`, staleTime 60s (cache share dashboard↔reports cùng `days`).
- [x] Extract helper label/priority đã lặp ở `/clusters` sang `lib/labels.ts` nếu Task 2–4 cần tái dùng (priority map ≥0.66 cao / ≥0.33 trung bình / còn lại thấp; null → null). *(thực thi: TDD RED→GREEN labels.test.ts, vitest 10/10)*

### Task 2: Trang `/insights`

**Files:** Rewrite `frontend/app/(app)/insights/page.tsx`

- [x] Header: tiêu đề + HoverCard "từ điển" (Insight = kết luận + hành động đề xuất kèm bằng chứng; Bằng chứng = trích dẫn nguyên văn ĐÃ ẩn danh từ feedback thật — copy bảng spec). *(thực thi: Popover như /clusters — hovercard không có trong registry shadcn vega, bài học FE-06)*
- [x] Empty chưa từng chạy: giải thích "cần phân cụm trước khi sinh insight" + CTA "Sinh insight".
- [x] Nút "Sinh insight" (destructive-outline như rebuild clusters vì replace-all): loading disable + Spinner + text "Đang sinh (có thể mất khoảng một phút)".
- [x] **409** (`ApiError.status===409`) → `Alert` variant destructive hiển thị ĐÚNG `detail` server ("Chưa có cụm nào. Chạy POST /api/clusters/run trước.") + Button link `/clusters`. Lỗi khác → toast lỗi chuẩn. *(verify live: POST qua proxy trả đúng 409)*
- [x] Card list dọc mỗi insight: `title` (h3) · `summary` · khối nổi bật "Hành động đề xuất" (`border-l-2 border-primary bg-muted/50 rounded-r-md px-4 py-3` — signature element của màn) · mục "Bằng chứng": mỗi evidence 1 hàng — Blockquote-style snippet (line-clamp-3, link `/feedbacks/{feedback_id}`, hover underline) + Badge severity (map màu UF-01 hiện hành) + `created_at` formatRelative · footer: `cluster_id` có → link "Xem cụm liên quan" `/clusters`; **KHÔNG** render `review_status` (OQ-11).
- [x] Success toast `{insights_generated} insight · {(duration_ms/1000).toFixed(0)}s` (+ `skipped>0` → đính " · bỏ qua {skipped} cụm").

### Task 3: Trang `/reports`

**Files:** Create `frontend/components/report-tiles.tsx`; Rewrite `frontend/app/(app)/reports/page.tsx`

- [x] Header: Select cửa sổ `days=7|30|90` (default 30) gắn URL param qua `router.replace` + text "Cập nhật lúc {generated_at} ({window_days} ngày gần nhất)".
- [x] `report-tiles.tsx`: 3 stat tile dùng chung (Card) — Tổng phản hồi · Chờ duyệt (toàn tile là link `/feedbacks?review_status=pending`) · Phát hiện PII. Props nhận `ReportSummary["totals"]` — dashboard import y nguyên (AC khớp 1:1).
- [x] Hai bar chart thuần div cạnh nhau (grid md:grid-cols-2): Mức độ nghiêm trọng 4 cột low→critical (bar height ∝ count/max, màu map severity UF-01, giá trị trên đầu cột, label dưới) · Cảm xúc **render theo Object.entries(by_sentiment) thứ tự server trả** (positive/neutral/negative/mixed). Count 0 vẫn vẽ cột tối thiểu + "0". *(thực thi: màu từ token `--chart-1..5` sẵn có — severity đậm dần low→high, critical dùng destructive; sentiment một hue bg-chart-3 vì phân bố không phải thứ bậc; verify live days=7 vs 30 số liệu khác nhau, sentiment đủ 4 key)*
- [x] Top chủ đề: Table ≤10 hàng (`category` · `count`), rỗng → Empty nhỏ nội tuyến. *(live: "hiệu năng" 5, "dịch thuật" 3…)*
- [x] Khối "Đang mới nổi": ≤5 mini-card (name + Badge "Mới nổi"/"Tăng đột biến" + feedback_count) → link `/clusters`; mảng rỗng → **ẩn cả khối** (spec edge case). *(live: DB 0 cụm → khối ẩn đúng)*
- [x] States: skeleton từng vùng độc lập (tiles/chart/table riêng); fetch lỗi vùng nào skeleton+toast vùng đó. *(điều chỉnh khi thực thi: C4 là 1 query duy nhất cho cả trang nên skeleton/Empty áp toàn trang — tách vùng chỉ có ý nghĩa nếu tách fetch, không làm)*

### Task 4: Dashboard đầy đủ

**Files:** Rewrite `frontend/app/(app)/dashboard/page.tsx`

- [x] Chào theo vai: "Xin chào, {email}" + Badge role (từ `useMe`) — role map tiếng Việt (pm → "Quản trị sản phẩm", operations → "Vận hành").
- [x] Dùng lại `report-tiles.tsx` + `useReportSummary(days)` (days mặc định 30, KHÔNG cần selector trên dashboard) — cùng queryKey nên chuyển sang `/reports` là có ngay số liệu (AC khớp 1:1).
- [x] Mini bar chart severity (tái dùng markup Task 3, extract component `components/severity-bars.tsx` nếu lặp). *(component đã extract từ T3 nên dashboard import trực tiếp)*
- [x] "Đang nổi" ≤3 cụm từ `emerging[0..2]` (name + badge + count → `/clusters`); rỗng → ẩn.
- [x] Shortcut hành động: "Xử lý {pending_review_count} mục chờ duyệt" → `/feedbacks?review_status=pending` — **CHỈ hiện khi pending > 0** (AC: không mời làm việc khi không có việc); "Chạy phân tích mới" → `/analysis` (luôn hiện).

### Task 5: Verify + đóng bài

- [x] `pnpm build` xanh; vitest xanh (thêm test cho helper mới nếu extract — priority map, sentiment key order). *(build xanh 10 route, TS pass; vitest 10/10)*
- [x] Live qua proxy :3000 (backend :8000 phải chạy code mới): `/insights` GET trước run → Empty đẹp; POST run khi chưa có cụm → Alert 409 đúng chữ; nếu tree DB đã có cụm (phiên demo-data có thể đã seed) → run thật chụp toast + card evidence; `/reports` đổi 7↔30↔90 → URL + số liệu đổi; `/dashboard` số liệu khớp `/reports` cùng days; shortcut pending chỉ hiện khi >0. *(thực thi 2026-08-26: GET insights `items:[]` + POST run 409 đúng chữ + C4 7-vs-30 khác biệt + 3 trang render 200 đúng h1; DB vẫn 0 cụm nên nhánh "run thật sinh card" dời mốc P5 cùng evidence LLM của plan 15 — phiên demo-data đang nạp dataset sẽ chạy clustering rồi mới run insights được; shortcut pending=1 đang hiện trên dashboard live)*
- [x] api-checklist: 2 dòng insights + dòng reports/summary cột "Trên FE" ⬜→✅ cùng commit; board FE-00-index tick FE-06b + progress log append; delivery-execute-plan §checklist tick P4 khi đủ cả 3 màn. *(tick trong chính commit đóng bài này; checklist delivery-execute-plan thuộc file chung đang bị phiên phase-17–20 sửa — để owner/session đó tự tick theo protocol append+re-read)*
