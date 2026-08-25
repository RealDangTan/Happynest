# UF-01 — Information Architecture (sitemap · role · nav · trạng thái dùng chung)

> **Phiên bản:** v1.0 · **Ngày:** 2026-08-25
> **Nguồn bám:** [`delivery-design-spec.md`](delivery-design-spec.md) §2/§4 · contract [`delivery-contracts.md`](delivery-contracts.md) (C1–C6) · luồng API/pipeline [`../user-flows.md`](../user-flows.md) F1–F7 · **bản đồ endpoint thật [`../api-checklist.md`](../api-checklist.md)** (16/16, snapshot 2026-08-25)
> **Đối tượng đọc:** session FE (trước khi viết/mount bất kỳ màn nào), owner review UX.
> **Quy tắc:** file này KHÔNG phát minh endpoint/schema — mọi field trỏ về contract C-mục. Thấy thiếu → mục OPEN QUESTION cuối file.

---

## 1 · Sitemap route đầy đủ

Cấu trúc thư mục App Router trong `frontend/app/` — đối chiếu thực tế 2026-08-25:

```text
frontend/app/
├── login/page.tsx                    # P1 ✅ FE-02  | public, không nằm trong shell
├── page.tsx                          # ⚠️ vẫn là placeholder template shadcn — cần redirect (OQ-3)
└── (app)/
    ├── layout.tsx                    # P1 ✅ FE-02  | shell: Sidebar + user menu; middleware guard cookie
    ├── dashboard/page.tsx            # P1 khung rỗng → P4 đầy đủ (UF-05 §4)
    ├── feedbacks/page.tsx            # P1 ✅ FE-03  | list + filter URL params
    │   └── data-entry-dialog.tsx     #   (component, không phải route): tab nhập tay + tab import CSV
    ├── feedbacks/[id]/page.tsx       # P1 ✅ FE-03  | detail + panel similar
    ├── analysis/page.tsx             # P1 ⬜ FE-04  | trigger run + progress + results (UF-03)
    ├── clusters/page.tsx             # P3 ⬜ FE-06  | placeholder hiện tại (UF-05 §1)
    ├── insights/page.tsx             # P4 ⬜ FE-06  | placeholder hiện tại (UF-05 §2)
    └── reports/page.tsx              # P4 ⬜ FE-06  | placeholder hiện tại (UF-05 §3)
```

Trang chưa đến pha mount hiển thị **Empty** kèm nhãn pha ("Sắp có — pha P3"), KHÔNG xoá route.

### Quy tắc redirect/guard

| Tình huống | Hành vi |
|---|---|
| Truy cập route `(app)` khi thiếu cookie | Middleware → `/login` (đã ship FE-02; JWT xác minh vẫn phía FastAPI) |
| `/` root | Đích thiết kế: redirect `/dashboard` (hiện còn placeholder — OQ-3) |
| Sau login thành công | Về `/dashboard` (mặc định); nếu có trang gốc định đi trước đó → quay lại trang đó nếu cơ chế lưu sẵn có, không bắt buộc |
| 401 giữa phiên (cookie hết hạn) | Xoá cache query → redirect `/login` (inventory §5) |

## 2 · Ma trận role × screen

Hệ thống có đúng 2 role (`pm`, `operations` — enum `UserRole`). **v1: cả 6 màn dùng chung cho cả 2 role** — guard API ở tầng router là `pm|operations`, không có endpoint phân quyền sâu hơn (contract "Áp dụng chung"). Role chỉ *hiển thị* cạnh avatar (Badge secondary — đã ship).

| Screen | pm | operations | Lý do cho phép chung |
|---|---|---|---|
| `/login` | ✅ | ✅ | public |
| `/dashboard` | ✅ (người dùng chính) | ✅ (xem được) | C4 không phân role |
| `/feedbacks` (+detail) | ✅ | ✅ (người dùng chính) | feedback router guard `pm\|operations` |
| `/analysis` | ✅ | ✅ | runs guard `pm\|operations` |
| `/clusters` `/insights` `/reports` | ✅ (chính) | ✅ | C1/C2/C4 guard `pm\|operations` |

Không tạo UI ẩn/hiện theo role trong v1 — khai báo KHÔNG scale (spec §6). Nếu owner muốn chặn operations khỏi màn analytics → là thay đổi scope, phải qua decisions.md TRƯỚC.

## 3 · Ánh xạ F1–F7 → screen

| Flow ([user-flows.md](../user-flows.md)) | Nơi sống trên UI | Spec chi tiết |
|---|---|---|
| F1 Đăng nhập | `/login` → shell (`GET /api/auth/me`) | UF-02 §1–2 |
| F2 Nhập feedback (đơn lẻ / CSV / CLI) | Dialog nhập tay + CSV tại `/feedbacks`; CLI ngoài UI | UF-02 §5 |
| F3 Tra cứu & quản lý | List `/feedbacks` · Detail `/feedbacks/[id]` (+ similar) | UF-02 §3–4 |
| F4 Phân loại tự động + cờ HITL | Trigger/polling tại `/analysis`; hệ quả cờ `requires_human_review` thấy ở list/detail | UF-03 |
| F5 Embedding & similar | Chạy ngầm trong run (không có nút riêng); kết quả = panel Similar ở detail; 409 khi chưa embed | UF-02 §4 |
| F6 HITL review | Queue = filter `review_status=pending`; hành động tại detail | UF-04 |
| F7 Cluster → Insight → Report | `/clusters` · `/insights` · `/reports` · tổng hợp ở `/dashboard` | UF-05 |

Luồng ngang (cross-cutting): mọi screen đều tuân inventory trạng thái §5 và quy ước URL §4.

## 4 · Quy ước nav + URL params (toàn app)

**Nav:**
- Sidebar 6 mục cố định, thứ tự: Tổng quan · Phản hồi · Analysis · Clusters · Insights · Báo cáo (đã ship đúng — giữ nguyên).
- Mục active = `data-active=true` của SidebarMenuButton (shadcn); không thêm nhóm lồng nhau trong v1.
- Icon qua thuộc tính `data-icon` theo quy ước shadcn của repo.
- Logo/khối thương hiệu sidebar click → `/dashboard`.

**URL search params — nguồn sự thật (spec §2):**
1. **Tên param = tên query API** tương ứng: `review_status`, `severity`, `category`, `offset`, `limit`. Không đặt tên kiểu UI (`statusFilter`) trên URL.
2. Filter/pagination đổi → ghi URL ngay (`router.replace`, scroll false); share/copy link tái tạo đúng trạng thái.
3. Đổi BẤT KỲ filter nào → reset `offset=0` (giữ nguyên filter khác). Đổi `limit` → reset `offset=0`.
4. Giá trị rỗng/không hợp lệ trên URL → bỏ param đó (coi như mặc định), không lỗi trắng trang.
5. Trang detail không có params điều khiển (id nằm ở path); tham số phụ (nếu sau này cần) mới xét từng màn.

**Pagination mặc định:** server mặc định `limit=20`, tối đa 100 (contract feedback list). UI hiển thị tổng từ `total`, điều hướng bằng offset; không phát minh "page=N" riêng.

## 5 · Inventory trạng thái dùng chung

Mọi màn trong sitemap áp dụng thống nhất — FE không tự chế variant riêng:

### Loading
- Vùng dữ liệu chính: `Skeleton` đúng hình học nội dung (table → skeleton dòng; cards → skeleton card grid). Không spinner toàn trang, không layout shift khi data về.
- Nút action đang chạy mutation: disable + label giữ nguyên (hoặc Spinner nhỏ trong nút); không double-submit.

### Error (bộ lỗi chuẩn contract)
| Code | Ý nghĩa | UI bắt buộc |
|---|---|---|
| 401 | Thiếu/hết credentials | Xoá cache TanStack Query → redirect `/login`. Không hiện toast lỗi kỹ thuật |
| 403 | Sai role | Trong v1 hầu như không xảy ra (2 role cùng quyền); nếu tới: Empty/Alert "Không đủ quyền" |
| 404 | Row không tồn tại | Trang detail/list con: Empty "Không tìm thấy" + link về list cha |
| 409 | Trạng thái không hợp lệ | Alert destructive **kèm hướng dẫn hành động** lấy từ `detail` của API (vd "chưa có embedding — chạy analysis trước") — 409 luôn kèm cách thoát |
| 422 | Body sai schema | Lỗi validation inline dưới từng Field (form) hoặc toast (action không có form) |
| 5xx/network | Lỗi máy | Toast sonner destructive chung, giữ nguyên dữ liệu đang hiển thị |

### Empty
- Dùng component `Empty` (shadcn), 1 câu mô tả + 1 CTA duy nhất khi có hành động tự nhiên (vd: chưa có feedback → CTA mở dialog nhập liệu).
- Empty vì *filter không khớp*: CTA phụ "Xoá bộ lọc" (clear URL params).

### Success
- Toast sonner ngắn (< 1 dòng), mutation xong **invalidate query key tương ứng** (quy ước FE-00). Không modal chúc mừng.

### Badge ngữ nghĩa dùng chung (map một lần, dùng mọi nơi)

| Trường | Giá trị | Gợi ý variant |
|---|---|---|
| `severity` | low / medium / high / critical | outline → secondary → warning-ish (token gần nhất trong preset) → destructive |
| `sentiment` | positive / negative / neutral / mixed | secondary tông tích cực / tiêu cực / muted / outline |
| `review_status` | unreviewed / pending / approved / edited / rejected | outline / secondary nhấn / xanh-lành / amber / destructive |
| `pii_detected` | true | Badge destructive chữ "PII" (chỉ metadata, không bao giờ hiện raw) |

Preset token cụ thể (`vega/olive/lucide`) do FE chọn gần nhất; UF khóa **ý nghĩa tương đối** (thứ tự nghiêm trọng + màu destructive chỉ dành cho critical/rejected/PII).

## 6 · Acceptance criteria (kiểm chứng bởi người khác)

- [ ] Sitemap §1 khớp 1:1 với cây `frontend/app/` sau mỗi pha mount (soi glob `app/**/page.tsx`).
- [ ] Mọi filter/pagination trên UI đều nằm trên URL và tên param trùng query API.
- [ ] Đổi filter bất kỳ → `offset` về 0 (thử trên `/feedbacks` đã ship).
- [ ] Copy URL có filter → mở incognito (đăng nhập) → cùng trạng thái bảng.
- [ ] 401 (xoá cookie thủ công rồi refetch) → bị đưa về `/login`, không treo màn trắng.
- [ ] Không màn nào hiển thị `raw_content` (grep code FE không có `include_raw=true`).
- [ ] Badge severity/sentiment/review_status dùng đúng map §5 ở mọi màn có chúng.

## Rủi ro UX & câu hỏi mở

- **OQ-1 — `docs/api-notes.md` được trỏ ở README, design-spec, UF-00 nhưng KHÔNG tồn tại** (plan 12 định viết, chưa thực thi). Bản đồ endpoint thật hiện là [`../api-checklist.md`](../api-checklist.md). Owner chọn: (a) tạo api-notes theo plan 12, hoặc (b) cập nhật các link trỏ sang api-checklist. UF spec các phần sau bám api-checklist + contract.
- **OQ-2 — Không logout** (non-goal v1, contract ghi rõ): menu avatar chỉ có email + badge role. Người dùng demo cần hiểu cookie hết hạn theo tuổi thọ token (~12h) — nên ghi vào kịch bản demo để không bị hỏi "sao không đăng xuất được".
- **OQ-3 — Root `/` vẫn là placeholder template shadcn** ("Project ready!"): cần redirect về `/dashboard` (việc FE nhỏ, gợi ý gộp vào FE-04 hoặc polish FE-07).
- **Rủi ro:** cả 2 role thấy hết màn → người demo vai operations có thể lỡ trigger cluster/insight (tốn LLM credit). Giảm nhẹ: nút trigger dạng confirm (UF-03/UF-05), không ai vô tình bấm là chạy.
