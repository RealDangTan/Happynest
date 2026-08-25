# UF WORKSTREAM — INDEX & STATUS BOARD (user flow specs)

> **Owner:** Session UF (planning/docs) · **Spec:** [`delivery-design-spec.md`](delivery-design-spec.md) §2/§4
> **Lãnh thổ:** CHỈ viết `docs/plans/UF-*`. Được đọc mọi thứ. Cấm `frontend/`, `backend/`, `FE-*`, `13–16-*`.
> **Nguồn sự thật:** tầng API/pipeline = [`user-flows.md`](../user-flows.md) (F1–F7) + [`api-checklist.md`](../api-checklist.md) + contract [`delivery-contracts.md`](delivery-contracts.md). UF spec **không phát minh schema/endpoint** — mọi data field phải trỏ về contract; phát hiện thiếu → ghi mục "OPEN QUESTION" cuối file, KHÔNG tự chế.

## Khuôn mẫu screen-spec (áp cho mọi deliverable dưới)

```markdown
### <Tên màn>
- Route / Roles / Pha mount (P1..P5)
- Purpose: 1–2 câu
- Data: endpoint + fields (trỏ contract C-mục)
- Components: tên shadcn cụ thể
- States: loading (Skeleton gì) / error (401/403/409/422 hiện thế nào) / empty (Empty component) / success
- Edge cases + Acceptance criteria (checkbox, kiểm chứng được bởi người khác)
```

## Bảng deliverable

| # | File nội dung | Phạm vi | Due (đi trước FE 1 pha) | Status |
|---|---|---|---|---|
| UF-01 | `UF-01-information-architecture.md` | Sitemap route đầy đủ; ma trận role×screen; ánh xạ F1–F7 → screen; quy ước nav + URL params; inventory trạng thái dùng chung | ngay (nền cho UF-02..05) | ✅ xong 2026-08-25 |
| UF-02 | `UF-02-specs-auth-feedback.md` | Login · Shell/Sidebar · Feedback list · Detail (+similar) · Import CSV — theo khuôn mẫu trên | trước giữa P1 | ✅ xong 2026-08-25 |
| UF-03 | `UF-03-spec-analysis-runs.md` | Trang analysis: trigger, progress polling UX (interval, trạng thái failed/resume), results table | trước khi FE viết FE-04 | ✅ xong 2026-08-25 |
| UF-04 | `UF-04-spec-hitl-review.md` | Queue pending; luồng approve/edit/reject; correction UI; ~~trạng thái mock "DEMO"~~ (hết hiệu lực — plan 13 BE xong 2026-08-25, spec bám API thật); limitation không logout | TRƯỚC CUỐI T2 (chặn P2) | ✅ xong 2026-08-25 |
| UF-05 | `UF-05-spec-clusters-insights-reports.md` | 3 trang analytics + dashboard PM; cách đọc emerging/spike/growth cho người không kỹ thuật | TRƯỚC CUỐI T4 (chặn P3/P4) | ✅ xong 2026-08-25 (sớm ~3 tuần) |

## Quy tắc làm việc

1. Mỗi deliverable xong → tick bảng + commit `docs(uf): …` + báo session FE biết file nào sẵn sàng (mục tiêu: FE không bao giờ phải tự chế flow).
2. Ghi đầu mỗi file: phiên bản + ngày + nguồn contract đang bám (C-mục).
3. Phản biện bắt buộc: cuối mỗi spec có mục "Rủi ro UX & câu hỏi mở" — liệt kê điều chưa chắc chắn thay vì im lặng chọn giúp owner.

## Tiến độ log (append-only)

- 2026-08-25 — tạo board + khuôn mẫu (đợt 1). — claude-code
- 2026-08-25 — UF-01 xong (v1.0): sitemap khớp thực tế `frontend/app/`, role matrix chung 2 role, quy ước URL param = tên query API, inventory trạng thái + map badge. Lệch ghi nhận: `api-notes.md` KHÔNG tồn tại → UF bám `../api-checklist.md` (OQ-1 trong UF-01); root `/` còn placeholder template (OQ-3). — claude-code (session UF)
- 2026-08-25 — UF-02 xong (v1.0): 5 màn auth+feedback theo khuôn mẫu; verify code BE 2026-08-25 — không filter `source`, sort cứng created_at DESC, `category` = containment chính xác trong JSONB. OQ mới: created_at picker (OQ-4), back-giữ-filter (OQ-5). — claude-code (session UF)
- 2026-08-25 — UF-03 xong (v1.0): verify shape thật 3 endpoint analysis (`{run_id}` 201 ngay · RunProgressOut · results = FeedbackListOut lọc theo run); polling 4s chỉ khi running; run_id sống trên URL vì KHÔNG có endpoint list runs (OQ-6) + snapshot config không trả về (OQ-7). — claude-code (session UF)
- 2026-08-25 — UF-04 xong (v1.0): queue = filter pending, hành động tại detail, correction dialog; verify `schemas/hitl.py` — ReviewIn có `reason?`, CorrectionIn chỉ cập nhật field gửi khác null (không xoá nhãn về null được — OQ-9); yêu cầu mock DEMO của board bỏ vì plan 13 BE đã xong. OQ-8: có cho reviewer xem raw không. — claude-code (session UF)
- 2026-08-25 — UF-05 xong (v1.0, sớm so hạn T4): 4 màn (clusters/insights/reports/dashboard) bám C1/C2/C4/C5/C6 + công thức trend plan 14; quy tắc hiển thị sentinel growth_ratio=9.99 → "Mới", priority null → ẩn; dashboard tái dùng C4 không phát minh endpoint; insight review_status display-only. OQ-10/11. — claude-code (session UF)
- 2026-08-25 — **Board UF-01→05 HOÀN TẤT trong 1 phiên.** Session FE có thể dựa: FE-04 ← UF-03 · FE-05 ← UF-04 · FE-06 ← UF-05. Danh sách OPEN QUESTION gom về UF-01 (OQ-1..3), UF-02 (4–5), UF-03 (6–7), UF-04 (8–9), UF-05 (10–11). — claude-code (session UF)
- 2026-08-25 — Pass phản biện chéo 5 spec (owner yêu cầu): 5 trục — nhất quán nội bộ ↔ UF-01, bám contract/code, AC kiểm chứng được, lãnh thổ, khớp hiện trạng mới. Vá 4 điểm: UF-01 sitemap detail ✅ (FE-03 ship `9f60c3b`); UF-02 header hiện trạng; UF-03 thêm edge backend-restart-giữa-polling + dedupe cột results; UF-05 priority bucket đánh dấu ngưỡng thuần UI. Xác minh thêm: shape `/similar` `{id,score,source,snippet}` đúng code (`routes/feedback.py` truncate sanitized). Không tìm thấy lệch contract nào khác. — claude-code (session UF)
- 2026-08-26 — **UF-02 v1.1** theo báo FE-03b (đã verify code): field Nguồn = Select từ `/api/sources` + wizard đăng ký; menu "Hiện thị cột" persist localStorage (bộ cột spec = mặc định); CSV wizard 3 bước map cột → preview → BE nhận canonical như cũ. OQ-4 + OQ-5 resolved theo hiện thực (không input created_at trên UI; back = list mặc định). Nhắc FE: `/api/sources` chưa được sync vào api-checklist (hard rule #10). — claude-code (session UF)
- 2026-08-26 — **Chốt đủ 11/11 OPEN QUESTION với owner** (2 vòng AskUserQuestion; phê duyệt = entry dated 2026-08-26 trong decisions.md): OQ-8 mở toggle raw cho reviewer (ngoại lệ DUY NHẤT của `include_raw`, scope FE-05) · OQ-7 BE bổ sung 4 field snapshot vào RunProgressOut (llm_model/prompt_version/pipeline_version/embedding_model) · OQ-1 bỏ `api-notes.md` chuẩn hoá link sang `api-checklist.md` (README + design-spec + board sửa trong đợt này) · OQ-3 redirect `/` gộp vào FE-04 · OQ-2 logout giữ lịch P1.5/FE-08 · OQ-6/9 chấp nhận giới hạn v1 · OQ-10 informational · OQ-11 ẩn badge `review_status` của insight trong v1. Cả 5 spec đã cập nhật trạng thái ✅ + nội dung tương ứng, cùng commit với decisions.md. — claude-code (session UF)
- 2026-08-26 — Cập nhật hiện thực theo báo session FE (đã verify git): `/api/sources` HOÁ RA đã sync api-checklist từ `50dccc3` (dòng 25–27) — lời nhắc ở dòng log trên là stale, rút; redirect `/` → `/dashboard` đã ship `36faa21` (UF-01 sitemap sửa ✅). Việc code còn mở duy nhất: BE RunProgressOut +4 snapshot field (OQ-7) — đang làm rõ owner với session FE (theo decisions.md, territory `backend/` thuộc họ). — claude-code (session UF)
- 2026-08-26 — Session FE **xác nhận nhận việc** BE RunProgressOut +4 snapshot field (OQ-7): backlog sau FE-05/06, sync api-checklist cùng commit đúng hard rule #10; UI feature-detect nên field chưa ship không vỡ gì. Vụ "commit lạ" clustering `664812e` có lời giải: entry mới cùng ngày trong decisions.md khai báo **lane AGENT** (series plans 17–20 = pha P6, gốc từ phiên brainstorm agent-module 25/08 với owner) — delivery giờ có **3 lane UF / FE / AGENT** chia lãnh thổ tường minh tại `delivery-execute-plan.md` §2; UF giữ kỷ luật không đụng file nào của 2 lane kia (kể cả uncommitted working tree của họ). — claude-code (session UF)
- 2026-08-26 — **OQ-7 SHIPPED `c0b07d0`** (lane FE, đã verify git + schema + checklist): RunProgressOut trả đủ 4 snapshot field, test assert đủ, api-checklist đồng bộ cùng commit. **Workstream UF chính thức không còn mục mở nào** — specs ↔ code ↔ checklist thẳng hàng. Ghi nhận nhỏ: FE nhầm các edit admin.py/clustering.py/reports (plans 15–16) là của UF — thực ra là lane BE 13–16; UF không hề đụng backend/. — claude-code (session UF)
