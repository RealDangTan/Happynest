# UF-05 — Screen specs: Clusters · Insights · Reports · Dashboard

> **Phiên bản:** v1.0 · **Ngày:** 2026-08-25
> **Nguồn bám:** contract [`delivery-contracts.md`](delivery-contracts.md) C1/C2/C4/C5/C6 · công thức trend verify từ plan `14-clusters-api.md` §3 (window W, spike/emerging/priority) · [`../user-flows.md`](../user-flows.md) F7 · quy ước chung [UF-01](UF-01-information-architecture.md)
> **Pha mount:** `/clusters` P3 · `/insights` + `/reports` + dashboard đầy đủ P4 (FE-06). Trước đó các trang là placeholder Empty theo UF-01 §1.
> **Non-goals contract phải tôn trọng:** không CRUD cluster/insight; **không có API đổi `review_status` của insight** (chỉ hiển thị); không phân trang clusters/insights (dataset nhỏ).

---

## Từ điển cho người không kỹ thuật (nhúng vào UI dạng tooltip/help popover)

| Thuật ngữ trên màn | Nghĩa đời thường |
|---|---|
| Cluster (cụm) | Nhóm phản hồi nói về cùng một vấn đề, máy tự gộp theo ý nghĩa |
| Emerging (mới nổi) | Vấn đề **hoàn toàn mới** — kỳ trước chưa ai nhắc, kỳ này xuất hiện đủ nhiều |
| Spike (tăng đột biến) | Vấn đề đã có nhưng kỳ này **tăng vọt** so với kỳ trước |
| Tỷ lệ tăng (`growth_ratio`) | So sánh số phản hồi kỳ này với kỳ trước: 2.0 = gấp đôi; <1 = đang lắng |
| Mức ưu tiên đề xuất | Điểm 0–1 do hệ thống tính từ độ phổ biến + tăng trưởng + độ nghiêm trọng — chỉ là *gợi ý*, người quyết |
| Insight | Kết luận + hành động đề xuất, kèm bằng chứng trích dẫn feedback thật |

⚠️ **Cạm bẫy hiển thị:** khi cụm mới nổi (`previous == 0, current > 0`), server trả `growth_ratio = 9.99` làm giá trị chặn (không phải "tăng 999%"). UI **phải** hiển thị "Mới" thay vì con số này. `suggested_priority` có thể `null` — ẩn ô thay vì hiện "null".

## Màn 1 — Clusters

- **Route / Roles / Pha:** `/clusters` · pm | operations · P3 (FE-06)
- **Purpose:** xem các nhóm chủ đề đang có trong phản hồi, nhận diện cái gì mới nổi/tăng vọt để ưu tiên xử lý.
- **Data:** `GET /api/clusters?sort=growth_ratio|recent` (mặc định `feedback_count` giảm dần) → items: `{id, name, summary, feedback_count, first_seen, last_seen, current_count, previous_count, growth_ratio, is_emerging, is_spike, suggested_priority|null, sample_feedback_ids[≤5]}`. Chưa từng chạy → **200 `{"items": []}`**.
- **Components:** Select (sort) · Card grid · Badge (emerging/spike) · Button trigger · AlertDialog confirm · Skeleton · Empty · sonner toast.
- **Bố cục:**
  - Header: tiêu đề + help tooltip "từ điển" ở trên + Select sắp xếp ("Nhiều phản hồi nhất" mặc định · "Tăng nhanh nhất" · "Mới nhất") — sort nằm trên URL param `sort`.
  - Grid card mỗi cụm: `name` (h1 card) · `summary` (≤2 dòng) · Badge "Mới nổi" / "Tăng đột biến" · dòng số liệu: `feedback_count` tổng · kỳ này `current_count` vs kỳ trước `previous_count` · tỷ lệ tăng (định dạng theo cạm bẫy trên) · "Ưu tiên đề xuất: cao/trung bình/thấp" (map gợi ý 0–1: ≥0.66/≥0.33/còn lại — ngưỡng hiển thị thuần UI, FE chốt khi mount, không đụng công thức server; null → ẩn) · footer: ≤5 link sample → `/feedbacks/[id]` + `last_seen` (định dạng tương đối "3 ngày trước").
  - Nút "Chạy phân cụm" → AlertDialog cảnh báo: **rerun xoá TOÀN BỘ insights + clusters cũ rồi tạo lại** (idempotent kiểu rebuild — C5) → Confirm.
- **States:** loading skeleton cards; empty (chưa chạy) = Empty giải thích + CTA chính là nút chạy phân cụm; success sau run = toast `{clusters_upserted} cụm · {assigned_count} phản hồi được gán · {unassigned_count} chưa gán (nhiễu/chưa embed)` + invalidate list.
- **Edge cases:** `unassigned_count > 0` là bình thường (noise HDBSCAN −1 + row chưa embedding — server đã báo count); cụm có `feedback_count` nhỏ vẫn hiển thị; KHÔNG có pagination — render hết list nhận được.
- **Acceptance criteria:**
  - [ ] Trước khi chạy lần nào: trang hiện Empty thân thiện, không lỗi đỏ.
  - [ ] Cụm `is_emerging=true` hiển thị nhãn "Mới nổi", KHÔNG hiển thị "999%" hay "9.99×".
  - [ ] Rerun phân cụm → insights cũ biến mất (kiểm tra trang insights trống lại) — đúng cảnh báo confirm.
  - [ ] Sort đổi → URL param `sort` cập nhật; copy link tái tạo đúng thứ tự.

## Màn 2 — Insights

- **Route / Roles / Pha:** `/insights` · pm | operations · P4 (FE-06)
- **Purpose:** mỗi cụm quan trọng nhận 1 kết luận tóm tắt + hành động đề xuất, kèm bằng chứng trích nguyên văn (đã sanitize) — phần "AI đọc hộ" của hệ thống.
- **Data:** `GET /api/insights` → items: `{id, cluster_id|null, title, summary, suggested_action, evidence[{feedback_id, snippet, severity, created_at}] (≤5), review_status}`. Trigger: `POST /api/insights/run` → **409 nếu chưa có cluster** ("chạy POST /api/clusters/run trước") · 200 `{insights_generated, duration_ms}`; server cap số cụm mỗi lượt (`INSIGHT_MAX_CLUSTERS`, default 10).
- **Components:** Card list dọc (đọc như báo cáo) · Badge severity từng evidence · Blockquote snippet · Button trigger · Alert 409 · Skeleton · Empty.
- **Bố cục mỗi card:** `title` · `summary` · khối nổi bật "Hành động đề xuất": `suggested_action` · mục "Bằng chứng": từng evidence là 1 dòng — snippet (trích `sanitized_content`, link sang `/feedbacks/[feedback_id]`) + badge severity + ngày. Footer card: link sang cụm liên quan (`cluster_id` → `/clusters`). Badge `review_status` **ẨN trong v1** (OQ-11 resolved 2026-08-26: mọi insight mãi "unreviewed" vì chưa có API đổi — hiển thị gây hiểu nhầm là có việc phải làm; hiện lại khi có API).
- **States:** empty chưa chạy = Empty + CTA "Sinh insight"; bấm trigger khi chưa có cluster → Alert 409 đúng chữ server + link sang `/clusters`; loading skeleton cards (call LLM mất ~vài chục giây — hiện trạng thái đang sinh rõ ràng, disable nút); success toast `{insights_generated} insight · {duration_ms}s`.
- **Edge cases:** cap 10 cụm/lượt là hành vi server — nếu cụm nhiều hơn, chạy lại lần nữa sẽ sinh tiếp; insight `cluster_id=null` (ngoài cụm) vẫn hiển thị bình thường; evidence snippet là text đã sanitize — không bao giờ raw.
- **Acceptance criteria:**
  - [ ] Chưa chạy cluster mà bấm "Sinh insight" → thấy Alert 409 kèm hướng dẫn, không crash.
  - [ ] Mỗi evidence click được → sang detail feedback tương ứng.
  - [ ] Không có bất kỳ control nào hứa "duyệt insight" (API không tồn tại — tránh hứa suông trên UI).

## Màn 3 — Reports (báo cáo tổng hợp)

- **Route / Roles / Pha:** `/reports` · pm | operations · P4 (FE-06)
- **Purpose:** bức tranh tổng thể thuần số liệu cho PM — không gọi LLM nên mở là có ngay.
- **Data:** `GET /api/reports/summary?days=7|30|90` (default 30) → `{generated_at, window_days, totals{feedback_count, pending_review_count, pii_detected_count}, by_severity{low…critical}, by_sentiment{…}, top_categories[{category,count}]≤10, emerging[≤5 shape con của C1]}`.
- **Components:** Tabs hoặc Select chọn cửa sổ (7/30/90) · Stat tile · Chart (Bar/Pie — component chart thêm lúc cần) · Table/Badge · Skeleton · Empty.
- **Bố cục:**
  - Header: chọn khoảng thời gian (URL param `days`) + text "Cập nhật lúc {generated_at}".
  - Hàng stat tiles: Tổng phản hồi · Chờ duyệt (link → queue pending) · Phát hiện PII.
  - Chart mức độ nghiêm trọng (4 cột low→critical, màu theo map UF-01) + Chart cảm xúc.
  - Top chủ đề: bảng/cột ngang ≤10 hàng (`category`, `count`).
  - Khối "Đang mới nổi": ≤5 mini-card cụm (name + badge emerging/spike + count) → link `/clusters`.
- **States:** loading skeleton từng vùng độc lập; đổi `days` giữ URL share; mọi giá trị 0 hiển thị "0" bình thường (không coi là empty-state toàn trang — chỉ khi fetch lỗi mới báo).
- **Edge cases:** `by_sentiment` render theo key thực trả về (enum có `mixed` — không hardcode 3 ô); emerging rỗng → ẩn cả khối thay vì hiện khung trống.
- **Acceptance criteria:**
  - [ ] Đổi 7↔30↔90 → URL `?days=` đổi và số liệu thay đổi tương ứng.
  - [ ] Tile "Chờ duyệt" click được → thẳng `/feedbacks?review_status=pending`.

## Màn 4 — Dashboard (tổng quan PM)

- **Route / Roles / Pha:** `/dashboard` · pm | operations · P1 khung rỗng → **P4 đầy đủ** (FE-06)
- **Purpose:** landing page sau login: trong 5 giây biết hệ thống đang có gì, việc gì cần tay.
- **Data:** tái dùng **cùng endpoint C4** `GET /api/reports/summary` (không phát minh endpoint riêng cho dashboard) — chia sẻ query cache với `/reports` cùng `days` đang chọn.
- **Bố cục P4:** chào theo vai (email + role từ `useMe`) · stat tiles giống Reports (thu gọn) · mini chart severity · danh sách ≤3 cụm đang nổi · 2 shortcut hành động: "Xử lý {pending_review_count} mục chờ duyệt" (→ queue) và "Chạy phân tích mới" (→ `/analysis`). P1: chỉ placeholder Empty "Dashboard đầy đủ từ pha P4".
- **States/Edge:** giống Reports; nếu C4 lỗi → tiles skeleton + toast, phần còn lại của trang vẫn dùng được.
- **Acceptance criteria:**
  - [ ] Số liệu dashboard khớp 1:1 với `/reports` cùng `days` (cùng nguồn).
  - [ ] Shortcut queue chỉ hiện khi `pending_review_count > 0` (không mời làm việc khi không có việc).

---

## Rủi ro UX & câu hỏi mở

> **Trạng thái 2026-08-26:** OQ-10/11 đã chốt với owner (decisions.md cùng ngày).

- **OQ-10 — ✅ resolved:** không hiển thị con số ngưỡng trend lên UI; mô tả định tính ("so kỳ trước") vẫn đúng kể cả khi owner đổi env config.
- **OQ-11 — ✅ resolved:** ẨN badge review_status của insight trong v1 (đã cập nhật bố cục Màn 2); hiện lại khi có API đổi trạng thái.
- **Rủi ro chi phí:** nút "Chạy phân cụm" rebuild sạch dữ liệu cũ — người dùng bấm nghịch làm mất insight đã có. Giảm nhẹ: confirm dialog nêu rõ hậu quả + wording "Tạo lại" thay vì "Chạy".
- **Rủi ro đọc sai số liệu:** growth_ratio 9.99-sentinel và priority null đã có quy tắc hiển thị riêng — FE phải code theo đúng "Cạm bẫy hiển thị" đầu file, đưa vào checklist review màn P3/P4.
