# Mobbin layout refresh — UX/UI plan

> **For agentic workers:** execute INLINE; no subagents. FE-only, no new dependencies, no endpoint change. Load `frontend-design` + `shadcn` skills before touching UI (AGENTS.md rule 9). Validation is run by the owner, never by the agent.

**Goal:** Người dùng theo được cùng một kết luận từ phản hồi gốc → bước duyệt → hành động được ưu tiên, trên mọi màn, với bố cục học từ các sản phẩm tham chiếu trên Mobbin.
**Spec:** Owner request 2026-11-16, danh sách tham chiếu Mobbin do Codex đề xuất cho 29 màn web + 404.
**Ràng buộc:** giữ khung điều hướng 3 chặng (Lắng nghe / Hiểu / Hành động), token màu pastel trong `app/globals.css`, Fraunces + Inter; chỉ dùng component shadcn đã cài.

## Đợt 1 — luồng chính (đã làm 2026-11-16, chờ owner kiểm tra)

| Màn | Tham chiếu | Thay đổi |
|---|---|---|
| `/data-graph` · thẻ điều tra (`components/ai/investigation-card.tsx`) | ChatGPT Activity & Sources, Grammarly duyệt cạnh nội dung | Kết luận và khung duyệt đặt cạnh nhau (container ≥ 44rem), khung duyệt dính khi cuộn. Thanh độ tin cậy. Chip trích dẫn dưới kết luận mở ngăn **Nguồn** đúng bằng chứng. Ngăn **Hoạt động** thay nút "Chi tiết kỹ thuật" (mã phiên + AiTrace). Giới hạn gấp lại. |
| `/data-graph` · chủ đề | Dovetail Themes | Bấm chủ đề → panel bên phải (xl) liệt kê phản hồi gốc mới nhất, cảm xúc, mức độ, ngày; mỗi dòng mở `/feedbacks/[id]`. Nút "Hỏi AI về chủ đề này" điền sẵn câu hỏi. Chủ đề đang chọn được làm nổi, các chủ đề khác mờ đi. |
| `/reports` | Elicit báo cáo kèm nguồn | Kết luận lên đầu trong khối nhấn, chip số nguồn nhảy tới bằng chứng tương ứng; hàng số liệu (độ tin cậy, số bằng chứng, số ảnh hưởng). Thao tác gom vào header: một nút chính theo trạng thái + menu "…" (Sửa / Xoá). "Phương pháp và giới hạn" gấp lại. Bỏ thẻ "Trạng thái gần đây" trùng danh sách. Việt hoá toàn bộ chữ Anh còn sót. |
| `/matrix` | TheyDo Table/Matrix, Searchable action queue | Toggle Ma trận/Bảng (ToggleGroup) cạnh bộ lọc. Hàng chờ quyết định đặt cạnh ma trận (xl), rê chuột vào dòng thì chấm tương ứng nổi lên và ngược lại. Nhãn ô kèm số đếm; chấm chờ duyệt có viền nét đứt. Ngăn chi tiết có **ma trận thu nhỏ** cho xem trước hành động sẽ sang ô nào khi chỉnh Tác động/Nỗ lực; nút quyết định dính đáy ngăn. Việt hoá hộp thoại thêm hành động. |

Thành phần mới: `components/ai/confidence-meter.tsx` (dùng chung Điều tra + Báo cáo).

### Owner kiểm tra đợt 1

- [ ] `pnpm test` (đặc biệt `components/ai/investigation-card.test.tsx` — 4 nút duyệt, 4 `disabled` khi busy) + `pnpm lint` + `pnpm build`.
- [ ] `/data-graph?run=<id>` ở trạng thái chờ duyệt: khung duyệt nằm cạnh kết luận ở màn rộng, xếp dưới ở màn hẹp và trong Chat panel.
- [ ] Bấm chip trích dẫn → ngăn Nguồn mở và cuộn tới đúng bằng chứng.
- [ ] Bấm chủ đề trong đám mây → panel phản hồi gốc; bấm một dòng → `/feedbacks/[id]`.
- [ ] `/reports`: chip nguồn cuộn tới bằng chứng; menu "…" sửa/xoá; báo cáo bị từ chối hiện cảnh báo.
- [ ] `/matrix`: rê chuột hàng chờ ↔ chấm; kéo thả chấm → ngăn chi tiết hiện ma trận thu nhỏ với vị trí cũ (nét đứt) và mới.

## Đợt 2 — màn dữ liệu và thành phần dùng chung (đã làm 2026-11-16, chờ owner kiểm tra)

| Màn | Tham chiếu | Thay đổi |
|---|---|---|
| `/vault` | Productboard Feedback detail | Dòng đang mở nằm trong URL (`?item=`) nên refresh/back giữ nguyên; panel chi tiết rộng 22rem với trích dẫn, nhãn, thuộc tính, nút trước/sau + phím ↑/↓ (j/k); phản hồi tương tự bấm được để chuyển panel; Việt hoá. Bộ lọc/cuộn giữ vì panel không điều hướng trang. |
| `/feedbacks/[id]` | Productboard Feedback detail | Hai cột: nội dung + phản hồi tương tự | cột thuộc tính dính (Nhãn AI, Nguồn, Dữ liệu sản phẩm). Nút quay về Kho mở đúng dòng. |
| `/feedbacks` | Featurebase list | Ô nội dung có dòng phụ nguồn · ngày (cột Nguồn/Thời điểm mặc định tắt, key lưu cột đổi sang v3); bấm cả dòng để mở; bảng cuộn trong khung, header dính. |
| `/importer` · mapping | Unify Map fields, Clay | Mỗi dòng: cột + giá trị mẫu → trường đích + quyết định ngay dưới; dòng bỏ qua mờ đi, dòng trùng tô đỏ nhạt. Thanh tóm tắt dính đầu (số Đồng ý/Đổi/Bỏ qua, lỗi chặn, nút Xác nhận). |
| `/taxonomy` | Midday tree, Searchable review | Cây đã có sẵn; thêm Chọn/Bỏ chọn tất cả + đếm đã chọn cho đề xuất AI, chân thẻ "Áp dụng" dính, mô tả hiện dưới tên. |
| `/stakeholders` | Motion grouped list | Bảng phẳng → danh sách nhóm theo phòng ban (chấm màu, số việc, số đã nhận); mỗi dòng có ưu tiên + trạng thái; panel "Việc cần làm" dính. |
| `/clusters` | Dovetail Themes | Lưới thẻ → danh sách cụm có thanh Kỳ trước/Kỳ này + panel cụm đang chọn (`?cluster=`) với số liệu, xu hướng và 5 phản hồi mẫu đọc được nội dung. |
| `/insights` | Chronicle VoC | Ba phần: dải phạm vi (số kết luận, đã/chờ duyệt, khoảng thời gian) → phát hiện chính xếp theo độ tin cậy → "Tiếng nói người dùng" trích từ bằng chứng. |
| `/dashboard`, `/reports/summary` | Productboard Trends | `components/time-range-toggle.tsx` dùng chung `?days=` 7/30/90 cho cả hai màn. Top chủ đề thành thanh ngang + tỉ trọng. Sửa lỗi đổi cửa sổ trên trang tổng hợp nhảy sang `/reports`. Nút tắt Tổng quan trỏ tới Nhập phản hồi / Hỏi AI. |
| `/analysis`, Trung tâm hoạt động | Databricks Job runs, Attio | Bảng lịch sử lượt chạy (trạng thái, bắt đầu, thời lượng, kết quả) cạnh chi tiết lượt; dòng lượt trong Trung tâm hoạt động thêm thời lượng + thời điểm. Helper `lib/run-format.ts`. |
| Command palette | Vapi | Nhóm "Gần đây" (localStorage, try/catch), thanh gợi ý phím, ARIA combobox/listbox, trạng thái báo cáo tiếng Việt, kết quả phản hồi mở đúng dòng trong Kho. |

### Owner kiểm tra đợt 2

- [ ] `/vault`: mở một dòng → URL có `?item=`; ↑/↓ chuyển dòng; bấm phản hồi tương tự; refresh vẫn mở panel.
- [ ] `/importer` bước mapping: thanh tóm tắt dính khi cuộn, nút Xác nhận bị chặn khi có cột trùng.
- [ ] `/clusters?cluster=<id>`, `/stakeholders`, `/insights`, `/analysis?run=<id>` hiển thị đúng ở màn hẹp (một cột) và rộng.
- [ ] `/dashboard?days=7` ↔ `/reports/summary?days=7` giữ cùng cửa sổ.
- [ ] Ctrl/⌘+K: nhóm Gần đây xuất hiện sau khi mở vài mục.

## Đợt 3 — tài khoản, hỗ trợ, trang public (đã làm 2026-11-16, chờ owner kiểm tra)

| Màn | Tham chiếu | Thay đổi |
|---|---|---|
| `/login`, `/register` | Causal, Outseta | Khung chung `components/auth-shell.tsx`: cùng một cột, Google là nút viền riêng phía trên đường chia, ô mật khẩu có nút hiện/ẩn, chân thẻ chuyển qua lại, nút về Trang chủ. Lỗi đăng ký chỉ tô đúng ô sai. |
| `/onboarding` | Attio Create workspace | Form bên trái + sidebar thu nhỏ bên phải hiện tên/mô tả workspace khi gõ, với ba chặng thật; Enter để tạo. |
| `/settings`, `/settings/workspace`, `/profile`, `/help`, `/contact` | Twenty, Cohere | `components/settings/settings-shell.tsx`: mục lục trái nhóm Tài khoản · Workspace · Hỗ trợ (hàng ngang ở màn hẹp). Bỏ lưới lối tắt trùng mục lục. Vùng nguy hiểm và Đăng xuất dạng hàng (mô tả trái, nút phải). Việt hoá "Workspace settings/Profile/Sign out/Danger zone". |
| `/help` | Slack Help | Ô tìm lọc cả câu hỏi thường gặp lẫn màn hình theo chủ đề; câu khớp tự mở; nút Liên hệ ở header. |
| `/contact` | Aave contact | Form cạnh cột "Nên chọn chủ đề nào?" + lối sang Trợ giúp. |
| `/landing`, `/product` | Sprig hero, Intercom features | `app/landing/product-visuals.tsx`: khung UI dựng bằng markup (map cột, kết luận + độ tin cậy + nút duyệt, ma trận). Hero landing đặt khung "Finding · Gate 2"; Product ghép mỗi mục LISTEN/UNDERSTAND/ACT với khung tương ứng. |
| `/docs`, `/legal` | Slite Docs, TIDAL Privacy | `PublicPageShell layout="guide"`: mục lục dính bên trái (Docs đánh số vì là trình tự; Legal không đánh số). |
| `/qna` | Mixpanel FAQ | `layout="faq"` + `app/landing/faq-list.tsx`: accordion, `/qna#review` tự mở đúng câu. |
| `/blog` | monday.com Blog | `layout="notes"`: lưới thẻ bài viết. |
| `/company` | TheyDo About | Giữ bố cục câu chuyện (mục lục hero + dải từng nguyên tắc). |
| 404 | Coinbase 404 | Nút về trang chủ + mở workspace, thêm liên kết Docs / Q&A / Help. |
| Mọi trang public | — | Khối cuối thêm nút "Create a workspace" cạnh nút về landing. |

### Owner kiểm tra đợt 3

- [ ] `/login`, `/register`: nút hiện/ẩn mật khẩu, lỗi Google `?google_error=` vẫn hiện, đăng ký xong vào `/onboarding`.
- [ ] `/onboarding`: preview cập nhật khi gõ, ẩn ở màn hẹp.
- [ ] Mục lục cài đặt đánh dấu đúng trang trên `/settings`, `/settings/workspace`, `/profile`, `/help`, `/contact`.
- [ ] `/docs`, `/legal` mục lục dính; `/qna#privacy` mở đúng câu; `/blog` lưới 2 cột; `/product` khung UI cạnh LISTEN/UNDERSTAND/ACT.
- [ ] Một URL không tồn tại → trang 404 mới.

Mỗi đợt: một phiên thực thi, commit nhỏ theo màn, owner kiểm tra trước khi sang đợt kế.
