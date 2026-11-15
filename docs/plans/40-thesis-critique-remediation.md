# Phản biện khóa luận HappyNest và kế hoạch xử lý trong dưới 1 tuần

## Context

Bạn nhờ phản biện logic, methodology và đặc biệt là UX của khóa luận. Mình đã đọc bản AutoRecovery 30/10 (bản chính, Chương 4 đang tạm gỡ), Chương 4 trong `adfdfsdf.docx`, dữ liệu khảo sát thô, decision log, các báo cáo đánh giá, backend, frontend và ảnh E2E 13/10.

**Kết luận chung:** phần kỹ thuật tốt và thái độ trung thực về giới hạn rất đáng khen. Điểm yếu lớn nhất là đề tài xây nhiều hơn hẳn những gì nó đo. Bản thảo tự đặt tiêu chí đánh giá ở Mục 2.4.5 rồi tự nhận chưa đo ở 4.4, nên hội đồng có thể hỏi: "Vậy em đã chứng minh được gì?". Ngoài ra, một số mô tả trong bản thảo không còn khớp với code.

**Mức độ xác minh:**
- ✅ code: đã đọc trực tiếp trong code.
- 📄 tài liệu: lấy từ decisions hoặc báo cáo trong repo.
- 📷 ảnh: từ ảnh 13/10, cũ hơn đợt sửa 24/10 và chụp khổ hẹp.
- Chưa đo trên app đang chạy: Vercel bị khóa, local đang tắt. Vì vậy mục UX chưa có số contrast, focus hay tap target.

## A. Năm điểm dễ bị bác nhất khi bảo vệ

| # | Vấn đề | Bằng chứng | Cách xử lý |
|---|---|---|---|
| 1 | Model đang chạy là model đã thua trong benchmark, và bản thảo không nói. S7 kết luận FAIL và ghi "không đổi production". Ngày 22/10 quyết định bị đảo sang Jev với lý do "fixture mơ hồ tự tạo". Phần thân bản thảo có 0 lần nhắc Jev hoặc S7; Chương 4 còn ghi S7 "chưa có kết quả". | 📄 `decisions.md:369-373, 442-446`; ✅ `backend/.env` có `ENRICH_ENGINE=jev` | Công khai quyết định và lý do tốc độ/chi phí, rồi đo lại (mục D1). `s7-jev-evaluation.md` và `00-index.md` cũng cần cập nhật. |
| 2 | Luật chuyển review cho con người không tồn tại. Mục 3.3 viết "Quy tắc review hiện là severity=critical hoặc safety_issue...". Grep `requires_human_review` trong `backend/app` và frontend ra 0 kết quả; chỉ còn trong migration cũ. `safety_issue` chỉ hiện ở trang `/feedbacks/[id]`, nơi giao diện chính không dẫn tới. Nhận xét "floor + HITL là lớp chịu lỗi" ở `decisions.md:446` vì thế không đúng. | ✅ | Nên làm lại (mục C1) vì đây là mục tiêu 7 ở 1.3.2. Nếu không kịp thì phải xóa khỏi mục tiêu và thiết kế. |
| 3 | Phân cụm không theo product, trái với "Product là ranh giới xuyên suốt" (3.1). `run_clustering` đọc toàn bộ feedback. Bảng cluster không có `product_id`. Bất kỳ tài khoản nào cũng xóa và tạo lại được cụm của mọi tài khoản. Tên cụm do LLM đặt có thể trộn dữ liệu nhiều công ty. | ✅ `clustering.py:188,221-228`; 📄 ghi nhận tại `decisions.md:425` | Sửa theo mục C2. Đây cũng là lỗi cô lập dữ liệu. |
| 4 | Thiếu Chương 4, mở đầu và 1.7 mâu thuẫn. Quy định của khoa có chương Kết quả. Mở đầu viết "Bốn chương", 1.7 viết "ba chương". | ✅ | Viết lại Chương 4 từ kết quả đo mới (mục D). |
| 5 | Công thức ưu tiên trong bản chính sai so với code. Bản thảo: `0,2 × C`, P = 6,16, khoảng 0,7–8,1. Code: `C × 10 × 0,2`, nên P = 7,6, khoảng 0,7–9,9. Slide lại đúng code, nên slide và bản thảo mâu thuẫn. | ✅ `act_agent.py:117-122` | Sửa Mục 3.5 và Công thức 3.1. |

## B. Phản biện logic và methodology

### B1. Khảo sát không đủ sức đỡ các trụ của đề tài

Bạn xác nhận dữ liệu là thật và có một phiếu của chính bạn.

- **Phiếu của tác giả.** Nên loại khỏi mẫu, hoặc ít nhất công bố. Bỏ phiếu đó thì n = 35 và các số đổi như sau:
  - Phản hồi phân tán mức 4–5: 23.
  - Khó nhận ra chủ đề mới mức 4–5: 24.
  - Phát hiện muộn: 35 (20 thỉnh thoảng, 15 thường xuyên).
  - Gom phản hồi tương tự mức 4: 26.
  - Sentiment/severity mức 2: 32.
- **Tổng thể bị báo cáo sai.** Câu sàng lọc hỏi về "sản phẩm số **có tính năng AI**", nhưng Mục 1.2 viết "sản phẩm số" rồi suy rộng sang "nhiều loại sản phẩm". Khảo sát không chứng minh được nhu cầu ngoài sản phẩm AI.
- **Đối tượng không khớp.** Mục 1.5.1 nêu PM, CSM và vận hành tại SME, "dựa trên kết quả khảo sát". Thực tế chỉ 7 PM và 5 Support/Ops trong 36 phiếu, nhóm lớn nhất là Dev/QA (10). Khảo sát không hỏi quy mô công ty, nên chữ SME không có căn cứ.
- **ACT không có bằng chứng nhu cầu.** "Khó xác định ưu tiên" không có phiếu nào ở mức 4–5 (31 mức 3, 5 mức 2). Khảo sát cũng không hỏi về đề xuất hành động, Agent hay thư viện best practices. Trong khi đó ACT là một trong ba trụ. Mục 1.2.1 đã thừa nhận một phần, nhưng kết luận "củng cố HITL" là suy diễn thêm.
- **Ưu tiên kỹ thuật ngược với dữ liệu.**
  - Export/tích hợp được 21/36 chọn, nhưng hệ thống không có chức năng export (✅ grep 0 kết quả).
  - Bảo vệ PII chỉ 8/36 chọn, nhưng tốn ~1 GB RAM. Vẫn nên giữ vì lý do pháp lý và đạo đức, chỉ đừng nói là do khảo sát định hướng.
  - Sentiment/severity bị đánh giá thấp, nhưng severity vẫn nằm trong công thức ưu tiên cụm.
- **Bỏ phí dữ liệu định tính tốt nhất.** 24 câu trả lời tự do đều nói về tính năng AI, và bản thảo không dùng.
  - Theo mã hóa nhanh của mình (một người, cần kiểm lại): khoảng 13/24 than thiếu ngữ cảnh tái hiện lỗi (prompt, version, query, log); khoảng 8/24 than auto-tag sai hoặc quá chung; chỉ 3/24 nói về nguồn phân tán.
  - Nhiều câu hỏi "lỗi do UI hay do model?", và HappyNest không trả lời được vì chỉ nhận text từ CSV.
  - Khoảng 3 câu trách "tool auto tag", trong khi chỉ 1/36 chọn "Công cụ AI/LLM" ở câu hỏi công cụ. Hội đồng có thể hỏi mâu thuẫn này. Cũng lưu ý HappyNest chính là một công cụ auto-tag.
- **Phân bố đáng chú ý.** Độ lệch chuẩn 0,28–0,58, không có điểm 1, rất ít điểm 5, 36/36 chọn cùng hai lựa chọn. Hãy mang theo log gốc của Google Form và nêu mẫu đồng nhất như một giới hạn. Không tính trung bình hoặc suy luận thống kê từ mẫu này.

### B2. Thiếu khung nghiên cứu

- Mục 1.3.2 là danh sách tính năng, không phải mục tiêu nghiên cứu. Bản thảo không có câu hỏi nghiên cứu (RQ) hay tiêu chí thành công đặt trước.
- **Đề xuất:** dùng Design Science Research (Hevner 2004; Peffers 2007), với HappyNest là artefact và Chương 4 là bước đánh giá. Cần kiểm lại trích dẫn trước khi đưa vào.
- **Ba câu hỏi nghiên cứu vừa sức:**
  - RQ1: Phân loại Việt–Anh có đủ tốt trên một tập nhãn độc lập không?
  - RQ2: Agent có tạo nhận định được bằng chứng hỗ trợ tốt hơn một baseline đơn giản không?
  - RQ3: Người dùng có kiểm tra và quyết định được dựa trên bằng chứng không?
- Mục 1.3.2 cam kết ghi nhận "độ chính xác, thời gian, chi phí, khối lượng kiểm duyệt", nhưng `/api/reports/kpis` chưa nối UI (📄 api-checklist) và không theo account.

### B3. Chưa chứng minh được cần Agent

- Bản thảo dẫn Anthropic: chỉ tăng độ phức tạp khi cần. Nhưng không có so sánh nào giữa graph 7 node và một baseline đơn giản.
- Bằng chứng hiện có không ủng hộ mạnh:
  - Insight E2E 02/10 là "Chưa thể xác định vấn đề tăng nhanh nhất sau import" (📄).
  - Một run mất ~12,5 phút với 26 lời gọi LLM (14 validate-retry), vượt ngân sách logic 18 (📄).
  - E2E 13/10 ra kết luận từ "ít nhất một phản hồi", confidence 0,50 (📷).
- Một kết quả trung thực "Agent không hơn baseline ở câu hỏi đếm, nhưng hơn ở câu hỏi mở" vẫn là kết quả tốt.

### B4. Phát hiện xu hướng có lỗi logic

Đây là nhu cầu được đánh giá cao trong khảo sát, nhưng phần cài đặt có 5 vấn đề (✅ `clustering.py`):

1. **Không chuẩn hóa mẫu số.** `growth_ratio = current/previous` là số đếm thô. Mục 2.4.2.3 lại viết phải xét tổng phản hồi cùng kỳ, nên code trái với lý thuyết của chính bản thảo.
2. **Cửa sổ neo theo `now`.** Mock data có ngày 02/08–05/09/2026, nên vào ngày 31/10 cả hai cửa sổ 30 ngày gần như trống. Spike và emerging gần như không thể bật trong demo bảo vệ. Dữ liệu CSV lịch sử cũng gặp vấn đề này.
3. **Cụm không ổn định giữa các lần chạy.** Mỗi lần chạy xóa cụm cũ, nên không có định danh cụm để theo dõi "chủ đề mới" theo thời gian.
4. **HDBSCAN trên vector 1536 chiều không giảm chiều.** Sweep 25 dòng cho 100% nhiễu. Với 121 dòng, mặc định 10 cho 0 cụm, chỉnh xuống 4 mới được 2 cụm (35/121). Bản thảo ghi 10, còn `.env` là 4 và thiếu entry decisions (📄 đã tự nhận ở `e2e_flow_report.md:56`).
5. **Giá trị và trọng số tự đặt.** `9.99` là giá trị thay thế khi kỳ trước bằng 0, và `suggested_priority` dùng trọng số chưa kiểm chứng.

### B5. "Closed-loop" và impact check là tên gọi quá mức

- Mốc đo là `action.created_at`, không phải ngày triển khai thật (✅ `impact_service.py:70`). Chỉ số là số lượng phản hồi, không phải chất lượng hay tác động.
- Khi `affected_context` rỗng, câu lệnh đếm toàn product. Với nguồn CSV theo lô, cửa sổ sau có thể không có dữ liệu. Chức năng này cũng chưa nối UI.
- Bản thảo đã thừa nhận giới hạn nhân quả, nhưng vẫn gọi "KPI vòng kín", còn landing ghi "Impact checks close the loop". Nên đổi tên thành "quan sát trước/sau", hoặc thêm trường ngày triển khai.

### B6. Confidence và chất lượng dữ liệu

- `confidence` không được hiệu chuẩn nhưng hiện dạng %. Ở `verification.json` 13/10, insight bị từ chối vì bằng chứng sai phạm vi có confidence **1,0**, còn insight hợp lệ được duyệt chỉ **0,50**. Ví dụ này (n = 2, không đủ để khái quát) cho thấy hiển thị con số có thể phản tác dụng. Với S7, gap của intent là 0,309.
- Không có guard kiểm tra slug thuộc taxonomy (✅ `enricher.py:79-92`). Bản thảo tự nhận, nhưng sửa chỉ mất vài dòng, nên để lại sẽ khó giải thích. Prompt còn viết cố định "sản phẩm có tính năng AI", mâu thuẫn với "nhiều loại sản phẩm".
- Toàn bộ dữ liệu đánh giá là synthetic, chính bạn tạo; tập S7 chỉ 16 mẫu. Không gán nhãn độc lập, không chia theo Việt/Anh/code-switching, chưa đo PII miss rate dù PII là "điều kiện xuyên suốt". Câu "mọi sản phẩm" không có căn cứ.
- **Mâu thuẫn định vị.** Bản thảo nói "nhiều loại sản phẩm", prompt enricher và landing nói "AI product teams", AGENTS.md nói "về sản phẩm AI". **Quyết định của mình: thu hẹp lại về sản phẩm có tính năng AI**, vì khớp khảo sát, prompt và dữ liệu. Tên đề tài chính thức không cần đổi; chỉ đổi phạm vi ở 1.5.

### B7. Bản thảo lạc hậu so với code

- Mục 3.1 viết "Mọi tài khoản dùng chung workspace". Code hiện cô lập theo tài khoản từ 22/10. `docs/README.md` và `sitemap-voc.md` cũng lạc hậu.
- Mục 3.7.2.2 và UC16–18 viết "lô 10 mục". Code hiện xử lý từng mục, tối đa 3 worker.
- Mục 3.6 và 3.7.9.2 viết Gate 2 ở Reports. Từ 24/10, Gate 2 nằm ở Data Graph và Chat.
- Mục 3.7 lặp ý rất nhiều, chiếm khoảng 25 trang chủ yếu mô tả sơ đồ. Số kiểm thử 9/10 đã cũ: 45 FE so với 71 FE và 48 BE focused ở 24/10.
- 11/37 tài liệu chưa được trích dẫn: [11, 12, 15, 16, 17, 29, 30, 32–35], trái quy định "chỉ gồm tài liệu được trích dẫn".
- `MODEL_ACT` hiện là Mistral Small, nhưng đánh giá ACT chạy trên `gpt-4o-mini`. Kết quả đó không gán được cho cấu hình hiện tại.
- 78 file handoff đang bị xóa trong working tree (chưa commit). Chúng vẫn nằm trong Git, nhưng `e2e_flow_report.md` dựng 100% từ chúng, và ảnh `e2e-01…30` đã mất. Đừng commit việc xóa này trước khi chốt bằng chứng.

## C. Phản biện UX

**Căn cứ:** Nielsen 10 heuristics, Amershi et al. 2019, checklist của `ux-validate` và phương pháp reading pass của `ux-ui-audit`. **Xếp hạng bằng lập luận, không dùng điểm tổng.** Repo không có tài liệu persona, JTBD hay journey (`docs/ux-discovery/` không tồn tại) và cũng chưa có buổi usability test nào, nên bản thân việc đề tài "lấy người dùng làm trung tâm" (2.3.2) chưa có bằng chứng.

**Câu hỏi kiểm chứng UX:** "PM mở app vào sáng thứ Hai có biết ngay tuần này có gì nghiêm trọng không?" → Hiện tại **không**. Mức đánh giá theo `ux-validate`: **Partial** (quy trình rất có kiểm soát, nhưng chưa phục vụ công việc lặp lại).

### Nghiêm trọng

1. **Chức năng được khảo sát ủng hộ nhất bị giấu.** Gom phản hồi được 27/36 chọn mức 4 và đó là căn cứ cho clustering, nhưng `/clusters` không có trong menu chính (`navigation.ts`). Chỉ `/dashboard` và `/reports/summary` link tới nó, và hai trang đó cũng gần như không được dẫn tới. Không có trang nào dẫn tới `/dashboard` (✅). `/insights` cũng không có link nào.
2. **Không truy được về phản hồi gốc, dù đó là lời hứa trung tâm.** 36/36 phiếu cần "hiển thị feedback gốc làm bằng chứng", còn bản thảo nói có khả năng truy vết. Trong `InvestigationCard`, bằng chứng chỉ là đoạn `<p>`; `readableEvidence` còn cố tình xóa ID và đổi UUID thành "[tham chiếu]". Toàn bộ `app/` và `components/` không có link nào từ bằng chứng sang feedback (✅ grep 0 kết quả).
3. **Gate 2 dễ thành bấm cho qua.** "Duyệt kết luận" là nút chính đứng đầu. Chỉ 2 bằng chứng được hiện và bị cắt 4 dòng. Khi không có bằng chứng, giao diện ghi "Chưa có bằng chứng..." nhưng nút Duyệt vẫn bấm được (✅ `investigation-card.tsx:42,114,116`). Lý do duyệt không bắt buộc và không có dữ liệu thời gian review, trong khi Field note 03 ở landing nói một gate tốt phải ghi "time spent". Đây chính là rủi ro automation bias mà Mục 2.4.3.2 nêu.
4. **Hướng dẫn lần đầu mô tả sai sản phẩm.** `FirstRunGuide` và `WelcomeTour` viết "The agent clusters feedback and proposes insights" và dẫn tới `/analysis`. Thực tế `/analysis` chỉ làm giàu dữ liệu; Agent ở `/data-graph`, cụm ở `/clusters`. Bước 3 chỉ hoàn thành khi có insight, nên chạy xong phân tích vẫn hiện 2/3, dù code ghi chú "the guide can't lie". Luồng này còn bỏ qua Taxonomy, bước đứng thứ hai trong menu. `Button asChild disabled` bọc `Link` có thể không chặn được điều hướng (cần kiểm trên app). Đây là phần chạm người dùng mới đầu tiên.

### Lớn

5. **Không có màn hình chính.** Mọi lần đăng nhập đều vào `/importer` (✅ `middleware.ts:13`). App thiết kế theo các bước của một lần đi qua pipeline, không theo công việc lặp lại: không có việc đang chờ duyệt, tín hiệu mới hay cảnh báo nghiêm trọng khi mở app.
6. **Không có cảnh báo an toàn.** Phản hồi critical hoặc safety không được đẩy lên ở đâu, chỉ có thể sắp xếp bảng theo severity (✅). Ảnh 07 có dòng "Bot bịa nguồn trích... Nghiêm trọng" nằm lẫn trong bảng.
7. **Quá nhiều ma sát trên quy mô bình thường.** Mỗi run tối đa 100 mục, nên 25/36 nhóm có 101–500 phản hồi/tháng phải chạy và xác nhận nhiều lần. Tính từ CSV đến action cần khoảng 10 bước và ít nhất 3–4 lần xác nhận chi phí. Xác nhận chi phí là tốt cho kiểm soát, nhưng chưa có phép đo nào cho thấy tổng công sức thấp hơn đọc thủ công.
8. **Stakeholders không tới được stakeholder.** Trang được mô tả là "bản tin cho từng phòng ban", nhưng mỗi workspace chỉ có một tài khoản, không có export, chia sẻ hay gán người phụ trách. Mục tiêu "phối hợp giữa các bộ phận" (1.4) vì vậy dừng ở việc PM tự đọc.
9. **Nội dung ACT mỏng nhưng trông chắc chắn.** Trong ảnh 15, một lỗi đăng nhập dẫn tới hai thẻ tham khảo cùng từ Google SRE (canary), tiêu chí "dưới 5%" không có baseline, và action được chấp nhận chỉ với insight confidence 0,50. Báo cáo ACT cũng ghi nhận một tiền đề không có trong đầu vào. Giao diện làm nội dung này trông đầy đủ, dễ khiến người duyệt tin hơn mức nên tin.
10. **Tên gọi theo hệ thống, không theo công việc.** Data Graph (nơi hỏi Agent), Vault, Matrix, Stakeholders, G1/G2/G3 và "Chi tiết kỹ thuật" đều đòi hỏi người dùng phải học. Người mới khó biết "hỏi Agent" nằm ở đâu.
11. **Song ngữ không hoàn chỉnh.** `investigation-card.tsx` viết cứng tiếng Việt, còn `first-run-guide.tsx` và `welcome-tour.tsx` viết cứng tiếng Anh (✅). Đổi ngôn ngữ sẽ không đổi các phần này, và ảnh 13/10 cũng cho thấy trộn ngôn ngữ trên cùng màn hình.
12. **Hai bộ màn hình song song.** `/feedbacks` và `/vault`, `/insights` và `/reports`, `/reports/summary` và `/reports` cùng tồn tại, nên nguy cơ lệch hành vi cao và đề tài khó mô tả rõ. Vault 1.565 dòng và Taxonomy 1.265 dòng là dấu hiệu màn hình quá tải (cần xác nhận trên app).

### Lời hứa vượt thực tế

- Landing: "Impact checks close the loop" (chưa có UI), "emerging-theme governance" (`/taxonomies/review` đã là legacy, chưa nối FE), "what happened next" (không có dữ liệu triển khai).
- Bản Vercel bị khóa, frontend trên đó chưa có backend công khai. Hội đồng không vào xem được; cần quay video hoặc chạy local.

### Điểm tốt nên giữ và nói rõ khi bảo vệ

- Tách finding, hypothesis, limitations; cho phép "Điều tra thêm" là thiết kế HITL hay.
- Xác nhận chi phí trước khi chạy; upload và preview không gọi LLM, đề xuất mapping bằng AI là thao tác riêng.
- Giữ cả giá trị AI và giá trị người chỉnh; trạng thái lỗi có giải thích và thử lại.
- Thái độ tự phê bình ("không suy rộng", "accepted không có nghĩa đã triển khai") tốt hơn nhiều khóa luận tương tự.

## D. Kế hoạch dưới 1 tuần

Mục tiêu: làm thật ít việc nhưng để Chương 4 có kết quả thật, và không còn câu nào trong bản thảo trái với code. Đúng quy tắc AGENTS.md: thực hiện inline, không thêm thư viện, mỗi đổi lệch ghi `decisions.md`, đổi API thì cập nhật `api-checklist.md`, đụng UI thì nạp skill frontend trước.

### Ngày 1: Audit UX trên app thật (bạn tự đăng nhập)

Chạy `frontend` và `backend` local (cần `.claude/launch.json`), mình đo bằng probe của `ux-ui-audit`. Không gọi LLM tốn phí nếu chưa hỏi bạn. Kết quả thay các mục "cần xác nhận" ở trên bằng số đo thật.

### Ngày 1–3: Sửa nhỏ làm đúng lời hứa của đề tài

| # | Việc | File chính |
|---|---|---|
| C1 | Tính cờ review theo luật đã công bố, lưu vào `ai_analysis`, thêm bộ lọc "Cần duyệt" ở Vault | `analysis_runner.py`, `enricher.py`, `jev_client.py`, `routes/feedback.py`, `vault/page.tsx` |
| C2 | Phân cụm theo product: thêm `clusters.product_id` (migration), `run_clustering(product_id)`, kiểm tra quyền sở hữu | `clustering.py`, model `cluster.py`, route `admin.py`, `clusters/page.tsx` |
| C3 | Kiểm tra slug thuộc taxonomy hiện hành | `enricher.py` (dùng lại `finalize_enrichment`), `jev_client.py` |
| C4 | Trend: neo cửa sổ theo `max(occurred_at)` của product, trả thêm tỷ trọng trên tổng cùng kỳ; ghi `CLUSTER_MIN_SIZE=4` vào decisions | `clustering.py::compute_trend` |
| C5 | Liên kết bằng chứng → feedback gốc, chặn Duyệt khi không có bằng chứng, đặt Duyệt sau bằng chứng | `lib/investigation.ts`, `investigation-card.tsx`, `vault/page.tsx` |
| C6 | Đưa Clusters vào menu UNDERSTAND; sửa `FirstRunGuide`/`WelcomeTour` đúng luồng (thêm Taxonomy, dẫn Agent tới Data Graph) | `lib/navigation.ts`, `first-run-guide.tsx`, `welcome-tour.tsx` |

**Nếu thiếu thời gian, cắt theo thứ tự:** giữ C5, C6, C3 và C2. C1 có thể thay bằng việc xóa mục tiêu 7. C4 có thể thay bằng công bố giới hạn và làm demo với ngày dữ liệu mới.

**Không làm:** export, màn hình chính mới, dọn màn hình cũ, đổi tên toàn bộ. Những mục này chuyển vào Hướng phát triển.

### Ngày 3–5: Đánh giá nhỏ cho Chương 4 (phần giá trị nhất)

Ước tính chi phí LLM dưới ~$1 theo giá S7; sẽ hỏi bạn trước khi chạy. Mọi mục đều công bố mẫu nhỏ và dùng dữ liệu synthetic.

- **D1. Phân loại.** Bạn gán nhãn khoảng 100–131 dòng mock theo codebook **trước khi** xem kết quả; nên nhờ thêm một người gán 30 dòng để tính agreement. So sánh Jev với Qwen trên topic micro/macro-F1, severity và tỷ lệ UNCATEGORIZED, chia theo VI/EN/code-switching, ghi chi phí và độ trễ. Đây cũng là căn cứ công khai cho quyết định ở điểm A1.
- **D2. PII.** Đếm PII đã biết trong mock và tính tỷ lệ bỏ sót hoặc che nhầm theo loại. Ghi rõ dữ liệu tự cấy.
- **D3. Clustering.** Quét `min_cluster_size` 3–10 trên 121 dòng, báo tỷ lệ nhiễu, độ ổn định và độ nhất quán của cụm qua đọc tay.
- **D4. Agent so với baseline.** 5–6 câu hỏi có đáp án biết trước (dạng đếm, so sánh kỳ, nguyên nhân mở). So sánh Agent với baseline SQL/semantic search một lượt. Chấm từng finding: nguồn có hỗ trợ không, phép đếm có đúng không; ghi số lời gọi, token, thời gian.
- **D5. UX.** Cognitive walkthrough cho 3 tác vụ chính, dùng kết quả Ngày 1. Nếu có thể, mời 2–3 người thử 20 phút theo phương pháp think-aloud, chỉ báo cáo định tính, không tuyên bố SUS có ý nghĩa thống kê.

### Ngày 5–6: Sửa bản thảo (bạn là tác giả, mình hỗ trợ)

- Thêm RQ và khung DSR vào Chương 1 và Mở đầu; sửa "ba/bốn chương".
- Sửa 1.2 theo n = 35 và đúng "sản phẩm có tính năng AI"; dùng thêm dữ liệu định tính; thu hẹp 1.5.
- Sửa A1, A2, A5 và B7; giảm lặp ở 3.7 (nếu vẫn đủ 50 trang).
- Chương 4 gồm: đối chiếu mục tiêu–kết quả, kiểm thử chạy lại, D1–D5, thảo luận, giới hạn.
- Làm sạch tài liệu tham khảo; cập nhật slide 2, 10 và phụ lục; chạy Turnitin theo checklist khoa.

## Files sẽ không đụng

`docs/thesis/*.docx` là file của bạn. Mình chỉ đề xuất nội dung để bạn đưa vào, trừ khi bạn yêu cầu. Khảo sát có email người tham gia, không đưa vào phụ lục hay file zip nộp khoa.

## Verification

- Backend: `uv run pytest -m "not integration"`, cùng integration cho clustering, isolation, enrich trên PG thật; thêm test cho C1–C4 (viết test trước theo `test-driven-development`).
- Frontend: `vitest run`, `tsc --noEmit`, `next build`.
- E2E: bằng tài khoản test trên local với `docs/feedback-mock/`: hai tài khoản không thấy cụm của nhau; bấm từ evidence ra đúng feedback; không duyệt được khi không có bằng chứng; đi đúng hướng dẫn lần đầu.
- Đánh giá: script và số liệu tổng hợp nằm trong `docs/evidence/`, kèm commit, model, prompt và taxonomy version; nhãn được chốt trước khi chạy và không sửa sau khi xem kết quả (như quy tắc của S7).
- Cuối cùng: rà từng tuyên bố trong bản thảo so với code; viết handoff theo `agent-handoff`.
