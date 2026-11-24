# Khung slide bảo vệ HappyNest trong 10 phút

Nguồn nội dung: `Khoa-luan-Le-Dang-Tan-11236199-VoC.docx` do người dùng chỉ định. Khung gồm 12 slide chính, thời lượng dự kiến 9 phút 40 giây và 20 giây dự phòng. Phụ lục phục vụ hỏi đáp, không tính vào phần trình bày. Đây là dàn ý, chưa phải tệp PowerPoint.

Thông điệp xuyên suốt: HappyNest kết nối phản hồi với nhận định có bằng chứng và đề xuất cải tiến, đồng thời giữ quyền phê duyệt của con người.

## Slide 1 Giới thiệu đề tài

**Thời lượng: 20 giây. Nguồn: trang bìa.**

- Giữ tên đề tài chính thức: “Thiết kế và phát triển hệ thống AI Agent hỗ trợ thu thập, phân tích phản hồi người dùng và đề xuất cải tiến – HappyNest”.
- Sinh viên: Lê Đăng Tấn, mã số 11236199.
- Giảng viên hướng dẫn: TS. Lê Hoài Thu.

Hình thức: bìa tối giản, tên trường và thông tin theo mẫu bảo vệ của trường. Không thêm đoạn giới thiệu dài.

Lời dẫn gợi ý: “Kính thưa Hội đồng, em xin trình bày hệ thống HappyNest, hỗ trợ xử lý phản hồi người dùng và đề xuất cải tiến có căn cứ, với các quyết định quan trọng do con người phê duyệt.”

## Slide 2 Bài toán và căn cứ khảo sát

**Thời lượng: 45 giây. Nguồn: mục 1.1–1.2, Bảng 1.1.**

- Phản hồi phân tán, khác cấu trúc, có nội dung Việt–Anh.
- 24/36 người đánh giá khó khăn do phản hồi phân tán ở mức 4–5.
- 25/36 người đánh giá khó nhận ra chủ đề mới ở mức 4–5.
- 36/36 người từng phát hiện muộn vấn đề lặp lại, ít nhất ở mức “thỉnh thoảng”.

Hình thức: ba số liệu lớn kèm nhãn đầy đủ. Ghi chân slide “Khảo sát định hướng yêu cầu, n = 36, 10–20/8/2026, mẫu thuận tiện”. Không dùng các câu trả lời có thang đo khác nhau như các cột của cùng một đại lượng.

Điểm nói: khảo sát cung cấp căn cứ xác định yêu cầu, chưa đo hiệu quả HappyNest.

## Slide 3 Mục tiêu và đóng góp của đề tài

**Thời lượng: 40 giây. Nguồn: mục 1.3, 1.6, 2.5.**

- Đối tượng sử dụng: người quản lý sản phẩm và nhân sự vận hành; hướng tới nhóm nhỏ/SMEs.
- Mục tiêu: tổ chức phản hồi, điều tra vấn đề và hỗ trợ quyết định cải tiến có thể truy vết.
- Đóng góp của nguyên mẫu: kết nối taxonomy có phiên bản, điều tra bằng công cụ, evidence và lịch sử phê duyệt trong cùng ứng dụng.

Hình thức: một sơ đồ liên kết phản hồi, nhận định, phương án và quyết định, kèm một dòng về người sử dụng.

Điểm nói: đóng góp tập trung vào tích hợp và kiểm soát quy trình. Khóa luận vận dụng các phương pháp sẵn có; chưa có đối chứng để khẳng định vượt các nền tảng thương mại.

## Slide 4 Quy trình LISTEN UNDERSTAND ACT và các điểm duyệt

**Thời lượng: 50 giây. Nguồn: mục 2.6, 3.1, Hình 3.1.**

- LISTEN: nhập dữ liệu, che PII, chuẩn hóa, quản trị nhãn và làm giàu.
- UNDERSTAND: Agent chọn công cụ điều tra và tạo nhận định gắn evidence.
- ACT: đề xuất phương án dựa trên insight đã duyệt và thực hành có nguồn.
- Gate 1 duyệt ánh xạ trước import. Gate 2 duyệt nhận định. Gate 3 duyệt phương án. Duyệt taxonomy là thao tác quản trị bổ sung ở LISTEN.

Hình thức: sơ đồ nghiệp vụ theo Hình 3.1, làm nổi rõ vị trí con người tham gia.

Điểm nói: LISTEN–UNDERSTAND–ACT là khung VoC trong CX/XM được vận dụng vào đề tài. Taxonomy có phiên bản, giới hạn Agent và cách đặt các gate là lựa chọn hiện thực của HappyNest.

## Slide 5 Kiến trúc và chuỗi truy vết

**Thời lượng: 40 giây. Nguồn: mục 3.2, Hình 3.2.**

- Next.js cung cấp giao diện; FastAPI xử lý nghiệp vụ và quyền truy cập.
- PostgreSQL/Supabase và pgvector lưu dữ liệu cùng vector; LangGraph điều phối điều tra và checkpoint.
- Dịch vụ LLM/embedding hỗ trợ diễn giải và biểu diễn ngữ nghĩa.
- Chuỗi truy vết nối product, feedback, run, evidence, insight, action và decision log.

Hình thức: kiến trúc rút gọn từ Hình 3.2, kèm chuỗi truy vết. Chỉ giải thích vai trò thành phần, không đọc danh sách thư viện.

Điểm nói: chỉ nội dung đã che đi vào pipeline AI. Product là ranh giới dữ liệu xuyên suốt. Đây là kiến trúc nguyên mẫu, chưa có kết quả xác nhận triển khai VPS production.

## Slide 6 LISTEN và quản trị taxonomy

**Thời lượng: 50 giây. Nguồn: mục 3.3.**

- CSV được lập hồ sơ cột, đề xuất mapping và chờ Gate 1 trước import.
- Nội dung đi qua bước che PII trước khi dùng cho AI.
- AI đề xuất taxonomy; người phụ trách rà soát rồi apply phiên bản.
- Enrichment áp dụng nhãn hiện hành. Trường hợp không còn topic đạt ngưỡng vào UNCATEGORIZED để xem xét tiếp.

Hình thức: một ví dụ giả lập về các cột CSV và cây nhãn đã duyệt. Nếu có ảnh ứng dụng, dùng ảnh hiện tại đã che PII.

Điểm nói: phân biệt đề xuất nhãn với áp dụng nhãn. Khả năng giữ trường hợp chưa phân loại giúp tránh ép mọi phản hồi vào chủ đề sẵn có. Không tuyên bố backend đã cưỡng chế hoàn chỉnh tập slug hợp lệ.

## Slide 7 UNDERSTAND và cơ chế AI Agent

**Thời lượng: 70 giây. Nguồn: mục 3.4, Hình 3.3.**

- Planner chọn công cụ theo câu hỏi và bối cảnh sản phẩm.
- Dispatch kiểm tham số, chạy công cụ và lưu evidence; evaluator đọc kết quả để quyết định điều tra tiếp.
- Synthesizer tạo finding, hypothesis và limitations. Graph lưu bản nháp và interrupt tại Gate 2.
- Người dùng có thể duyệt, sửa, từ chối hoặc yêu cầu điều tra thêm.

Hình thức: graph theo Hình 3.3, làm nổi vòng planner–dispatch–evaluator, bước tổng hợp và điểm dừng Gate 2.

Điểm nói: LLM lựa chọn hướng điều tra, chương trình thực thi truy vấn và phép đếm. Query compiler kiểm field theo schema; Agent không tự thực thi SQL do mô hình sinh. Mặc định giới hạn tám vòng và ngân sách logic 18 bản ghi gọi plan/evaluate/synthesize; fallback/retry có thể tăng số request vật lý. Evidence ID hợp lệ chưa chứng minh finding được nguồn hỗ trợ về ngữ nghĩa.

## Slide 8 ACT và phê duyệt phương án

**Thời lượng: 60 giây. Nguồn: mục 3.5.**

- Đầu vào là insight đã duyệt và evidence liên quan.
- Đề xuất nêu căn cứ, thực hành tham khảo, điều kiện áp dụng, phương án thay thế, đánh đổi và tiêu chí thành công.
- Điểm ưu tiên dựa trên impact, urgency, confidence và effort, do backend tính.
- Gate 3 cho phép sửa ước lượng, chấp nhận hoặc từ chối; giữ giá trị AI và lịch sử quyết định.

Hình thức: một phương án giả lập hoặc ảnh action hiện tại, đủ thấy nguồn, đánh đổi và thao tác phê duyệt. Đưa công thức chi tiết vào phụ lục.

Điểm nói: ACT v2 xác thực mã evidence/thẻ thực hành và lấy metadata nguồn chuẩn, không nhận URL tự tạo từ mô hình. Kiểm mã chưa bảo đảm nguồn được áp dụng đúng. “Accepted” ghi nhận lựa chọn trong ứng dụng, chưa chứng minh triển khai hay tác động.

## Slide 9 Minh họa một tình huống xuyên suốt

**Thời lượng: 75 giây. Nguồn: luồng Chương 3; đây là kịch bản minh họa đề xuất.**

Tình huống giả lập: phản hồi về thao tác thanh toán bị chậm. Không gán số lượng, tỷ lệ tăng hay nguyên nhân nếu chưa có kết quả chạy tương ứng.

1. Hiển thị dữ liệu đã che và mapping đã duyệt.
2. Đặt câu hỏi điều tra về vấn đề thanh toán; mở nhận định và evidence thực tế của run.
3. Duyệt insight, mở phương án ACT, chỉnh một ước lượng và xem lịch sử Gate 3.

Hình thức: video quay trước 60–75 giây hoặc ba ảnh theo trình tự có chú thích. Chuẩn bị ảnh dự phòng khi demo trực tiếp. Không chờ dịch vụ LLM chạy toàn bộ trong phiên bảo vệ.

Điểm nói: tập trung chứng minh đường đi của bằng chứng và quyền can thiệp của người dùng. Ghi rõ dữ liệu giả lập. Hình 3.4–3.5 trong khóa luận là bản thiết kế ngày 15/9/2026, không dùng như ảnh kiểm thử phiên bản hiện tại.

## Slide 10 Kết quả và phạm vi kiểm chứng

**Thời lượng: 65 giây. Nguồn: mục 4.1–4.3, Bảng 4.1.**

| Hạng mục | Kết quả được ghi trong khóa luận | Phạm vi |
|---|---|---|
| Frontend unit | 45/45 test đạt, 10 tệp | Lượt ngày 9/10/2026 |
| Frontend typecheck | Mã thoát 0 | Chưa phải kiểm chứng production build |
| Backend unit đủ quyền | 92 test đạt, 106 bị loại | Nhóm không integration, 65,31 giây |
| Integration/E2E | Không chạy lại ở lượt nền | Chưa có số mới để tính đạt |

Hình thức: bảng bốn dòng và một câu kết luận về phạm vi phần mềm được kiểm tra.

Điểm nói: đây là kết quả lịch sử được tài liệu ghi nhận, không phải lượt kiểm thử mới cho slide. Lượt sandbox trước đó gặp lỗi quyền đọc Stanza; chi tiết để phụ lục. Bảng nền không xác nhận các thay đổi ACT v2 phát sinh sau lượt chạy. Chưa có gold label để báo cáo F1, chưa có đối chứng thời gian hoặc tác động nghiệp vụ.

## Slide 11 Giới hạn và kế hoạch đánh giá tiếp

**Thời lượng: 40 giây. Nguồn: mục 3.3, 4.4.**

- Dữ liệu minh chứng nhỏ, chưa có tập nhãn chuẩn độc lập. Bước tiếp: xây tập Việt–Anh/code-switching và đo micro/macro-F1, tỷ lệ UNCATEGORIZED.
- Evidence ID và mã nguồn hợp lệ chưa xác nhận chất lượng lập luận. Bước tiếp: người chấm độc lập đánh giá finding/evidence và tính phù hợp phương án.
- Hiệu quả thời gian, chi phí và tác động chưa có đối chứng. Bước tiếp: cố định phiên bản, kiểm toán request/token và đo cùng công sức người duyệt.

Hình thức: ba cặp “giới hạn hiện tại / bước kiểm chứng tiếp”.

Điểm nói: ưu tiên hoàn thiện guard nhãn, kiểm chứng evidence và budget trước khi mở rộng triển khai.

## Slide 12 Kết luận và trao đổi

**Thời lượng: 25 giây. Nguồn: Kết luận.**

- Nguyên mẫu kết nối xử lý phản hồi, điều tra và đề xuất trong một quy trình có thể truy vết.
- Con người duyệt ánh xạ, taxonomy, nhận định và phương án ở các điểm xác định.
- Đánh giá chất lượng AI và tác động trên dữ liệu độc lập là bước tiếp theo.

Hình thức: kết luận ngắn, dòng cảm ơn Hội đồng và mời trao đổi ngay trên cùng slide.

Lời kết gợi ý: “Đóng góp chính của HappyNest là kết nối phản hồi, bằng chứng và lịch sử quyết định trong một quy trình có con người kiểm soát. Kết quả hiện tại xác nhận một phần hành vi phần mềm; đánh giá chất lượng AI và tác động thực tế là hướng hoàn thiện tiếp theo. Em xin cảm ơn Hội đồng.”

## Phụ lục phục vụ hỏi đáp

1. **Định vị với hệ thống liên quan:** rút gọn Bảng 2.1, so sánh phạm vi VoC, khai phá ý kiến, nền tảng thương mại, Fider và HappyNest. Chưa có benchmark chung để xếp hạng.
2. **Vì sao cần Agent và cách giới hạn:** graph bảy node, ba node gọi LLM, registry chín công cụ, phạm vi sản phẩm, query compiler, ngân sách logic và interrupt/resume.
3. **Taxonomy, cluster và confidence:** taxonomy là nhãn có quản trị; cluster phụ thuộc dữ liệu và tham số; confidence chưa được hiệu chuẩn thành xác suất đúng. Sweep 25 phản hồi cho toàn nhiễu ở các min_cluster_size đã thử, không chứng minh không có vấn đề.
4. **Công thức ưu tiên:** P = 0,4I + 0,3U + 0,2(10C) + 0,1(10 − E). Đây là hàm trọng số của đề tài, không phải RICE. Ví dụ giả lập I=8, U=7, E=3, C=0,8 cho P=7,6; đổi I=6 cho P=6,8.
5. **Dữ liệu, kiểm thử và an toàn:** tách 36 người khảo sát, 25 phản hồi sweep và 19 dòng demo. 650 dòng là kế hoạch, chưa là kết quả phân tích. Giữ đầy đủ Bảng 4.1 và ma trận Phụ lục A; nêu giới hạn PII và trạng thái integration/E2E.
6. **Nguồn thực hành ACT và cấu hình mô hình:** thư viện 18 thẻ, bảy góc nhìn khác tám nhóm nhận action; minh họa điều kiện áp dụng một thẻ. Phân biệt `typesafe/jev-router` với API Jev trực tiếp, không suy chất lượng mô hình chỉ từ tên router.

## Quy tắc dựng deck

- Dùng tỷ lệ 16:9 nếu trường không có mẫu bắt buộc. Mỗi slide giữ một ý chính và tối đa khoảng 3–4 cụm nội dung.
- Không thêm slide mục lục riêng trong giới hạn 10 phút; mạch bài đã thể hiện qua quy trình ở slide 4.
- Ưu tiên sơ đồ nghiệp vụ, graph và ảnh minh họa đã che PII; tránh đưa toàn bộ bảng dữ liệu hay mã nguồn lên slide chính.
- Dùng cùng một tình huống giả lập để giải thích LISTEN, UNDERSTAND, ACT và demo. Không chuyển ví dụ giả lập thành kết quả thực nghiệm.
- Phân biệt trên slide hoặc lời nói: đã hiện thực, kết quả kiểm thử lịch sử, minh họa và kế hoạch đánh giá.
- Chạy thử toàn bài với đồng hồ, giữ 20 giây dự phòng. Nếu quá giờ, rút phần kiến trúc trước; giữ phần Agent, kết quả và giới hạn.
