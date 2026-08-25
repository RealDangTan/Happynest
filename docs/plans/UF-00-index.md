# UF WORKSTREAM — INDEX & STATUS BOARD (user flow specs)

> **Owner:** Session UF (planning/docs) · **Spec:** [`delivery-design-spec.md`](delivery-design-spec.md) §2/§4
> **Lãnh thổ:** CHỈ viết `docs/plans/UF-*`. Được đọc mọi thứ. Cấm `frontend/`, `backend/`, `FE-*`, `13–16-*`.
> **Nguồn sự thật:** tầng API/pipeline = [`user-flows.md`](../user-flows.md) (F1–F7) + [`api-notes.md`](../api-notes.md) + contract [`delivery-contracts.md`](delivery-contracts.md). UF spec **không phát minh schema/endpoint** — mọi data field phải trỏ về contract; phát hiện thiếu → ghi mục "OPEN QUESTION" cuối file, KHÔNG tự chế.

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
| UF-05 | `UF-05-spec-clusters-insights-reports.md` | 3 trang analytics + dashboard PM; cách đọc emerging/spike/growth cho người không kỹ thuật | TRƯỚC CUỐI T4 (chặn P3/P4) | ☐ |

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
