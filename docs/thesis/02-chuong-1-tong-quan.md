# CHƯƠNG 1. TỔNG QUAN VỀ ĐỀ TÀI

## 1.1. Bối cảnh và lý do chọn đề tài

Phản hồi của người dùng là một nguồn thông tin trực tiếp về cách sản phẩm hoạt động ngoài môi trường kiểm thử. Người dùng mô tả tình huống của họ bằng ngôn ngữ tự nhiên và không tuân theo một mẫu thống nhất. Cùng một vấn đề có thể xuất hiện dưới nhiều cách diễn đạt, trong khi cùng một từ khóa lại mang ý nghĩa khác nhau giữa các sản phẩm. Khi sản phẩm có tính năng AI, phản hồi còn đề cập đến độ chính xác câu trả lời, nội dung có thể gây hại, sự thiên lệch hoặc quyền riêng tư. Bởi vậy, chỉ đếm từ khóa hoặc lọc thủ công theo một vài nhãn cố định khó phản ánh đầy đủ tình hình.

Trong một nhóm sản phẩm, phản hồi thường đi qua nhiều bước trước khi trở thành công việc cụ thể. Dữ liệu được thu thập từ tệp xuất của hệ thống hỗ trợ, biểu mẫu, đánh giá ứng dụng hoặc kênh giao tiếp khác. Người tiếp nhận cần xác định những cột nào là nội dung phản hồi, thời gian, nguồn, nhóm khách hàng hay phiên bản sản phẩm. Sau đó họ đọc từng phản hồi, gắn nhãn và tìm mối liên hệ giữa các trường hợp. Cuối cùng, một nhận định cần có ví dụ và con số đủ tin cậy để người quản lý chấp nhận, rồi mới dẫn đến phương án xử lý. Nếu bỏ qua bước kiểm tra bằng chứng, một nhận định trôi chảy về mặt ngôn ngữ vẫn có thể sai về mặt dữ liệu.

Đặc thù của dữ liệu trong đề tài là sự pha trộn tiếng Việt và tiếng Anh. Một câu có thể chứa từ tiếng Anh chỉ lỗi, tên tính năng, mã phiên bản và phần mô tả bằng tiếng Việt. Phương pháp xử lý phải giữ được ngữ cảnh này. Mặt khác, phản hồi có thể chứa tên, địa chỉ email, số điện thoại hoặc thông tin định danh. Đưa nguyên văn phản hồi vào dịch vụ mô hình bên ngoài sẽ tạo ra rủi ro riêng tư; do đó hệ thống phải che những thông tin này trước khi phân tích.

Đề tài được lựa chọn vì có một khoảng trống rõ trong quy trình thực tế: nhiều công cụ hỗ trợ từng đoạn của công việc, nhưng người dùng vẫn phải tự nối dữ liệu thô, phân tích và quyết định hành động. Mục tiêu của khóa luận là xây dựng một ứng dụng phần mềm có quy trình liên tục, trong đó AI hỗ trợ phân loại và điều tra, các phép tính dùng công cụ xác định, bằng chứng được lưu lại, còn người dùng giữ quyền phê duyệt. Cách tiếp cận này phù hợp với quy mô phát triển của một khóa luận và có thể kiểm chứng qua những kịch bản đầu cuối.

## 1.2. Khảo sát nhu cầu và xác định vấn đề

### 1.2.1. Phương pháp khảo sát

Trong giai đoạn xác định yêu cầu, đề tài sử dụng một biểu mẫu khảo sát trực tuyến về công việc xử lý phản hồi người dùng. Tệp lưu tại `docs/thesis/Thesis - AI Feedback Survey Responses - Form Responses 1.csv` có 36 câu trả lời trong khoảng 10–20/8/2026. Cả 36 người chọn đồng ý tham gia và trả lời rằng trong sáu tháng gần đây họ đã từng đọc, tổng hợp hoặc xử lý phản hồi cho sản phẩm số có tính năng AI. Biểu mẫu hỏi vai trò công việc, quy mô phản hồi, mức độ khó khăn và đánh giá tính hữu ích của một số chức năng. Bản báo cáo chỉ dùng số liệu gộp từ câu hỏi lựa chọn; tên, email, thời điểm trả lời của cá nhân và các câu trả lời tự do không được đưa vào tài liệu.

Đây là mẫu khảo sát thuận tiện, không phải mẫu ngẫu nhiên đại diện cho mọi nhóm phát triển sản phẩm AI. Bởi vậy, kết quả chỉ được dùng để xác định vấn đề và thứ tự ưu tiên thiết kế. Khóa luận không suy ra tỷ lệ của toàn bộ ngành, cũng không coi ý kiến về mức hữu ích như bằng chứng cho hiệu quả sau triển khai. Số lượng mẫu của mọi tỷ lệ dưới đây là 36, trừ khi ghi khác.

### 1.2.2. Đặc điểm người trả lời và khối lượng xử lý

Người trả lời đến từ nhiều vai trò liên quan đến sản phẩm. Có 10 người thuộc nhóm phát triển/QA/dữ liệu/AI, 7 người thuộc quản lý sản phẩm, 5 người thuộc thiết kế hoặc nghiên cứu người dùng, 5 người thuộc hỗ trợ hoặc vận hành, 4 người thuộc phân tích nghiệp vụ và 5 người chọn nhóm khác. Điều này giúp khảo sát nhìn bài toán từ các vị trí tham gia khác nhau. Tuy nhiên, tỷ trọng 10/36 của nhóm kỹ thuật cho thấy không thể mặc định nhu cầu của mọi người trả lời là nhu cầu của người quản lý sản phẩm.

Về khối lượng công việc, 25 người chọn mức 101–500 phản hồi mỗi tháng, 8 người chọn mức 21–100 và 3 người chọn trên 500. Câu hỏi sử dụng khoảng số lượng nên không cho phép tính số phản hồi trung bình chính xác. Kết quả vẫn cho thấy đa số người trả lời quen với một lượng dữ liệu khiến việc đọc từng mục bằng tay có thể tiêu tốn thời gian đáng kể. Từ đó, chức năng nhập hàng loạt, lọc và chọn phạm vi phân tích được đưa vào yêu cầu của hệ thống.

**Bảng 1.1. Cơ cấu vai trò của người tham gia khảo sát (n = 36)**

| Vai trò | Số người | Tỷ lệ |
|---|---:|---:|
| Phát triển / QA / Dữ liệu / AI | 10 | 27,8% |
| Quản lý sản phẩm | 7 | 19,4% |
| Thiết kế / Nghiên cứu người dùng | 5 | 13,9% |
| Hỗ trợ / Vận hành | 5 | 13,9% |
| Phân tích nghiệp vụ | 4 | 11,1% |
| Khác | 5 | 13,9% |

**Nguồn:** tính tổng hợp từ biểu mẫu khảo sát của đề tài, tháng 8/2026. Các tỷ lệ làm tròn một chữ số thập phân; tổng có thể lệch 100% do làm tròn. Bảng 1.1 cho thấy mẫu không chỉ bao gồm một nhóm chức danh.

### 1.2.3. Khó khăn và mong đợi theo kết quả khảo sát

Người trả lời chấm mức độ khó khăn từ 1 đến 5. Vấn đề phản hồi phân tán ở nhiều nguồn nhận 24/36 câu trả lời ở mức 4 hoặc 5. Công việc đọc và gán loại thủ công nhận 21/36 câu trả lời ở mức 4; 15 người chọn mức 3. Khó nhận ra chủ đề mới nhận 25/36 câu trả lời ở mức 4 hoặc 5. Ngược lại, việc xác định vấn đề cần ưu tiên có 31/36 câu trả lời ở mức 3 và 5/36 ở mức 2. Như vậy, kết quả khảo sát hỗ trợ mạnh hơn cho nhu cầu gom dữ liệu và nhận tín hiệu mới so với nhận định rằng mọi người đều gặp khó khăn nghiêm trọng khi sắp thứ tự ưu tiên.

Một câu hỏi khác hỏi tần suất một vấn đề lặp lại chỉ được nhận ra khi nhiều phản hồi tương tự đã xuất hiện. Có 20 người chọn “thỉnh thoảng” và 16 người chọn “thường xuyên”. Không có nhóm trả lời “chưa từng” trong dữ liệu lưu được. Kết quả này gợi ý một yêu cầu quan trọng: sau khi phản hồi được chuẩn hóa, hệ thống phải giúp người dùng xem mức lặp lại và biến động theo thời gian, đồng thời cho phép truy về các phản hồi gốc đã được che thông tin cá nhân.

Về mức hữu ích của chức năng, 27/36 người đánh giá gom phản hồi tương tự ở mức 4; 22/36 đánh giá phát hiện chủ đề mới ở mức 4 hoặc 5. Tóm tắt nhận định kèm số lượng và phản hồi minh chứng nhận 15/36 ở mức 4, còn 19/36 ở mức 3. Tự động phân loại nhận 8/36 ở mức 4 và 27/36 ở mức 3. Chức năng xác định cảm xúc và mức nghiêm trọng được 33/36 người chọn mức 2. Những con số này ngăn việc thiết kế đề tài thành một bảng điều khiển sentiment đơn thuần: giá trị chính nên nằm ở chuẩn hóa, tìm các trường hợp liên quan, phát hiện tín hiệu mới và trình bày bằng chứng để người dùng xem xét.

**Bảng 1.2. Một số kết quả liên quan trực tiếp đến chức năng thiết kế (n = 36)**

| Nội dung khảo sát | Số câu trả lời | Diễn giải cho thiết kế |
|---|---:|---|
| Khó khăn vì phản hồi phân tán, mức 4–5 | 24 | Cần cơ chế nhập và chuẩn hóa nguồn |
| Khó nhận ra chủ đề mới, mức 4–5 | 25 | Cần khám phá chủ đề và so sánh theo thời gian |
| Đã phát hiện muộn vấn đề lặp lại, ít nhất “thỉnh thoảng” | 36 | Cần truy tìm phản hồi tương tự và dấu vết bằng chứng |
| Gom phản hồi tương tự hữu ích, mức 4 | 27 | Ưu tiên tìm kiếm ngữ nghĩa và nhóm hóa |
| Cảm xúc/mức nghiêm trọng hữu ích, mức 2 | 33 | Giữ là thuộc tính hỗ trợ, không coi là chức năng giá trị duy nhất |

**Nguồn:** tổng hợp từ cùng biểu mẫu khảo sát. Bảng 1.2 thể hiện các câu hỏi khác nhau và không tạo thành một thang điểm chung. Mức hữu ích được hỏi với điều kiện “nếu hoạt động với độ chính xác phù hợp”, vì vậy chưa phải là đánh giá hệ thống đã triển khai.

### 1.2.4. Phát biểu bài toán

Từ khảo sát và phân tích nghiệp vụ, bài toán được phát biểu như sau: xây dựng một ứng dụng có thể tiếp nhận phản hồi không đồng nhất, biến phản hồi thành dữ liệu có thể lọc và tìm kiếm, hỗ trợ phát hiện vấn đề xuất hiện hoặc lặp lại, rồi tạo ra nhận định có liên kết tới số liệu và trường hợp cụ thể. Ứng dụng cần cho phép người dùng xác nhận cách hiểu cột dữ liệu, duyệt nhận định và chỉnh sửa đề xuất hành động. Trong toàn bộ quy trình, dữ liệu cá nhân phải được che trước khi gửi đến các thành phần AI bên ngoài.

Đầu vào trực tiếp của phiên bản hiện tại là tệp CSV và phản hồi tạo thủ công trong ứng dụng. Đầu ra bao gồm dữ liệu phản hồi đã chuẩn hóa, nhãn phân loại, vector biểu diễn, thống kê/cụm khi có đủ dữ liệu, nhận định có bằng chứng và danh sách hành động được sắp xếp theo điểm ưu tiên. Chỉ một phần các bước cần mô hình ngôn ngữ; các thao tác kiểm tra điều kiện, tổng hợp số lượng và tính điểm có thể thực hiện bằng chương trình xác định.

## 1.3. Mục tiêu của đề tài

### 1.3.1. Mục tiêu tổng quát

Mục tiêu tổng quát là thiết kế và xây dựng một hệ thống hỗ trợ quá trình xử lý phản hồi của sản phẩm AI, từ lúc nhận dữ liệu cho tới khi người phụ trách có thể đưa ra hành động dựa trên một nhận định đã được kiểm tra. Hệ thống hướng tới giảm các thao tác lặp lại và giúp quyết định dễ truy vết hơn. Khóa luận không đặt mục tiêu chứng minh AI thay thế người phân tích; các điểm người dùng duyệt là một phần của thiết kế.

### 1.3.2. Mục tiêu cụ thể

Mục tiêu thứ nhất là tiếp nhận dữ liệu có cấu trúc cột thay đổi giữa các tệp, đề xuất cách ánh xạ và để người dùng sửa trước khi nhập. Mục tiêu thứ hai là che thông tin định danh, phân loại nội dung và lưu kết quả đủ để tìm kiếm, lọc, tổng hợp. Mục tiêu thứ ba là hỗ trợ điều tra câu hỏi bằng các công cụ số liệu và ghi lại bằng chứng dùng để lập nhận định. Mục tiêu thứ tư là chuyển nhận định được chấp nhận thành các lựa chọn hành động có điểm ưu tiên do công thức xác định, kèm quyền chỉnh sửa của người dùng. Mục tiêu cuối cùng là cung cấp giao diện và API có thể kiểm thử theo một kịch bản xuyên suốt.

Các mục tiêu này được kiểm tra bằng chỉ số và tình huống ở Chương 4. Một chức năng có giao diện chưa đồng nghĩa với chức năng đã được chứng minh chất lượng; cần đối chiếu API, dữ liệu lưu và hành vi khi đầu vào bất thường. Đặc biệt, nhận định có mã bằng chứng không tự động chứng minh tính đúng đắn của lập luận. Chất lượng này phải được đánh giá riêng trên mẫu có thể đọc lại.

## 1.4. Đối tượng và phạm vi nghiên cứu

### 1.4.1. Đối tượng sử dụng và dữ liệu

Hai vai trò đăng nhập hiện tại là `pm` và `operations`. Cả hai tham gia quy trình xem, nhập và phân tích dữ liệu theo quyền định nghĩa ở API; một số thao tác quản trị, chỉnh sửa hoặc xóa được giới hạn cho `pm`. Các nhóm như ENGINEERING, DESIGN hay SUPPORT trong phần ACT là nơi có thể nhận đề xuất xử lý, không phải vai trò đăng nhập của hệ thống.

Dữ liệu được nghiên cứu là phản hồi ngắn hoặc trung bình về sản phẩm số có tính năng AI. Phản hồi có thể trộn tiếng Việt, tiếng Anh và thuật ngữ kỹ thuật. Bên cạnh nội dung còn có ngày phát sinh, nguồn, thuộc tính theo sản phẩm và metadata riêng của nguồn. Phiên bản khảo sát không bao gồm cơ chế thu thập tự động trực tiếp từ mọi hệ thống ticket, email hoặc mạng xã hội; tệp xuất CSV đóng vai trò đầu vào có thể kiểm soát.

### 1.4.2. Phạm vi chức năng và triển khai

Trong phạm vi chức năng, hệ thống hiện thực ba giai đoạn LISTEN, UNDERSTAND và ACT. LISTEN tiếp nhận CSV, hiển thị hồ sơ cột đã che thông tin, đề xuất ánh xạ và xử lý quyết định của người dùng. Pipeline phân tích phân loại phản hồi, tạo embedding, hỗ trợ tìm tương tự, thống kê và phân cụm. UNDERSTAND tiếp nhận câu hỏi, dùng công cụ phân tích để ghi bằng chứng rồi tạo nhận định có phần sự kiện và phần giả thuyết riêng. ACT tạo các đề xuất theo nhóm nghiệp vụ, tính điểm, hiển thị ma trận và ghi lại thao tác của người dùng. Một số báo cáo tổng hợp và KPI được tạo bằng truy vấn dữ liệu.

Phạm vi môi trường là frontend Next.js, backend FastAPI chạy native trên Windows khi phát triển, PostgreSQL do Supabase quản lý và dịch vụ mô hình qua API tương thích OpenAI. Hệ thống được thiết kế cho quy mô dữ liệu khóa luận, không đặt yêu cầu phục vụ lưu lượng người dùng lớn. Mã nguồn có kế hoạch triển khai VPS nhưng tập lệnh triển khai hiện còn là khung; phần đó được nêu là hướng phát triển, không phải kết quả vận hành sản xuất.

### 1.4.3. Những giới hạn đặt ra từ đầu

Khóa luận không huấn luyện từ đầu một mô hình ngôn ngữ hoặc embedding. Chất lượng phân loại phụ thuộc mô hình do nhà cung cấp API và cấu hình prompt. Vì không có bộ nhãn chuẩn đủ lớn trong repo, đề tài tập trung vào độ đúng của quy trình phần mềm, kiểm tra tình huống và phân tích minh bạch các ví dụ đầu ra, thay vì báo cáo một giá trị F1 không có dữ liệu nền. Tương tự, ma trận ưu tiên là công cụ hỗ trợ quyết định; điểm ưu tiên là kết quả công thức, không phải phép đo khách quan của lợi ích kinh doanh.

## 1.5. Phương pháp thực hiện và cách đánh giá

Đề tài kết hợp khảo sát mô tả với phương pháp phát triển phần mềm. Khảo sát giúp xác định vấn đề và độ ưu tiên chức năng; kết quả được giới hạn trong nhóm 36 người trả lời. Phân tích yêu cầu được thể hiện bằng tác nhân, ca sử dụng, quy trình và đặc tả dữ liệu. Thiết kế hệ thống bao gồm ranh giới thành phần, mô hình dữ liệu, các trạng thái nghiệp vụ và luồng xử lý có sự tham gia của người dùng. Từng chức năng được triển khai thành các mô-đun và API để có thể kiểm tra riêng rồi kiểm tra liên thông.

Đánh giá ở cuối khóa luận có ba lớp. Lớp thứ nhất kiểm tra chức năng và phân quyền với dữ liệu giả lập, lỗi hợp lệ và thao tác lặp. Lớp thứ hai chạy một kịch bản xuyên suốt để chứng minh dữ liệu đi được từ đầu vào đến quyết định. Lớp thứ ba xem các giới hạn: tác động của lượng dữ liệu nhỏ đến phân cụm, độ trễ và chi phí mô hình, độ tin cậy của bằng chứng và những chức năng chưa có triển khai thực tế. Cách đánh giá này tương ứng với mục tiêu ứng dụng phần mềm; nó không biến các kịch bản demo thành bằng chứng về tác động xã hội hoặc hiệu quả kinh doanh ở quy mô lớn.

## 1.6. Ý nghĩa và đóng góp của đề tài

Đóng góp đầu tiên là một quy trình có thể theo dõi từ một tệp dữ liệu chưa chuẩn hóa đến phản hồi đã phân tích. Người dùng có cơ hội xác nhận cột dữ liệu trước khi chạy bước AI tốn phí. Đóng góp thứ hai là cơ chế điều tra có bằng chứng: hệ thống tách phép truy vấn, tập hợp bằng chứng và phát biểu kết luận, đồng thời phân biệt điều quan sát được với giả thuyết cần xác minh. Đóng góp thứ ba là cách tổ chức quyết định của con người thành ba điểm duyệt tương ứng với rủi ro ở từng giai đoạn. Đóng góp thứ tư là lưu cả đề xuất của AI và giá trị người dùng chỉnh sửa để có thể phân tích sai khác về sau.

Về mặt thực tiễn, ứng dụng minh họa cách một nhóm sản phẩm có thể chuyển phản hồi rời rạc thành thông tin có thể thảo luận. Ý nghĩa này nằm ở quy trình và khả năng truy vết; khóa luận chưa có phép đo đủ mạnh để kết luận hệ thống làm giảm bao nhiêu phần trăm thời gian xử lý trong một doanh nghiệp thực tế. Chương 4 nêu rõ những gì đã chạy và giới hạn của từng kết quả.

## 1.7. Chuyển nhu cầu khảo sát thành yêu cầu có thể kiểm chứng

Khảo sát mô tả một vấn đề bằng ngôn ngữ của người làm sản phẩm, trong khi đặc tả phần mềm cần nêu đầu vào, hành vi và kết quả quan sát được. Hai lớp này không thể nối với nhau bằng cách chọn chức năng được chấm hữu ích cao nhất rồi lập trình ngay. Ví dụ, người tham gia nói “khó nhận ra chủ đề mới” nhưng một màn hình liệt kê từ khóa phổ biến chưa chắc giải quyết được. Cần phân tích vì sao chủ đề bị nhận ra muộn: dữ liệu rải rác, cách diễn đạt khác nhau, thiếu mốc thời gian hoặc không có người kiểm tra nhận định. Từ đó, yêu cầu được chia thành nhập và chuẩn hóa nguồn, tìm liên hệ ngữ nghĩa, so sánh theo thời gian và mở được các phản hồi làm căn cứ.

**Bảng 1.3. Truy vết từ nhu cầu khảo sát tới yêu cầu thiết kế**

| Tín hiệu nhu cầu | Diễn giải giới hạn | Yêu cầu phần mềm | Minh chứng cần có |
|---|---|---|---|
| 24/36 chấm cao khó khăn vì nguồn phân tán | Cảm nhận của mẫu thuận tiện | Import CSV, mapping và product scope | Tệp khác schema qua Gate 1 |
| 25/36 chấm cao khó nhận chủ đề mới | Chưa đo thời gian phát hiện thật | Chủ đề, xu hướng, nhóm và nguồn phản hồi | Danh sách nguồn theo cửa sổ thời gian |
| 36/36 từng phát hiện muộn ít nhất đôi lúc | Không xác định mức trễ cụ thể | Tìm tương tự và evidence | Truy vấn mở được phản hồi liên quan |
| 27/36 chấm 4 cho gom phản hồi | Mức hữu ích giả định nếu đủ chính xác | Embedding và bộ lọc theo product | Tập relevance gán nhãn sau này |
| 33/36 chấm 2 cho sentiment/severity | Không chứng minh chức năng vô ích | Thuộc tính hỗ trợ, không làm sản phẩm chính | Kiểm tra tính đúng và khả năng lọc |

Bảng 1.3 cho thấy một tín hiệu khảo sát có thể dẫn đến nhiều yêu cầu, và một yêu cầu có thể cần nhiều loại minh chứng. Dữ liệu khảo sát hướng chọn mục tiêu nhưng không tự kiểm chứng kết quả. Chẳng hạn, 36 người đã gặp việc phát hiện muộn không có nghĩa ứng dụng chắc chắn rút ngắn thời gian phát hiện; điều đó chỉ tạo lý do để thiết kế phép đo `time_to_insight` và một nghiên cứu người dùng về sau. Việc ghi rõ quan hệ này giúp báo cáo tránh nhảy từ nhu cầu sang tuyên bố hiệu quả.

### 1.7.1. Thứ tự ưu tiên yêu cầu

Yêu cầu được ưu tiên theo mức đóng góp cho đường đi cốt lõi và mức rủi ro nếu thiếu. Không có dữ liệu chuẩn hóa và an toàn, kết quả phân tích phía sau không có nền tin cậy. Vì vậy, import, mapping, ranh giới PII và trạng thái phân tích được đặt trước các trang trình bày nâng cao. Tiếp theo là khả năng tìm, lọc và ghi evidence để UNDERSTAND có thể chứng minh nhận định. Sau đó mới đến khuyến nghị hành động và KPI. Thứ tự này không nói rằng giao diện ACT kém quan trọng; nó phản ánh sự phụ thuộc dữ liệu. Một ma trận ưu tiên đẹp sẽ gây hiểu lầm nếu action xuất phát từ insight không đối chiếu được với phản hồi.

Trong yêu cầu phi chức năng, bảo vệ PII có mức chặn: nếu không đạt, không được gửi nội dung đi gọi mô hình chỉ để giữ tính liên tục của demo. Tính truy vết và phân quyền cũng có mức chặn ở các bước duyệt. Hiệu năng và chi phí có thể điều chỉnh bằng phạm vi phân tích, ngưỡng và ngân sách, nhưng không được ẩn chi phí khỏi người dùng. Tính đúng của số đếm phải gắn với bộ lọc; một báo cáo nhanh nhưng sai mẫu số không có giá trị. Các tiêu chí này tạo thứ tự kiểm chứng cho Chương 4 và chỉ ra chỗ cần thêm bằng chứng trước khi nộp.

### 1.7.2. Ranh giới giữa yêu cầu và giả định

Một số lựa chọn trong thiết kế là giả định được đặt ra để có thể xây dựng phiên bản khóa luận. Tệp CSV là đầu vào kiểm soát được, trong khi nhiều nhóm ngoài thực tế dùng hệ thống ticket hoặc các kênh thời gian thực. Hai vai trò `pm` và `operations` đủ để kiểm tra RBAC cơ bản nhưng chưa phản ánh mọi cơ cấu doanh nghiệp. Tập tám nhóm nghiệp vụ trong ACT là danh sách cố định để sản phẩm thử nghiệm có thể giải thích; một tổ chức khác có thể dùng chức danh và trách nhiệm khác. Trọng số điểm ưu tiên và ngưỡng ma trận là cấu hình, chưa được tối ưu trên dữ liệu tổ chức. Báo cáo đánh dấu các giả định này để người đọc phân biệt phần đã quan sát với phần do tác giả chọn.

Thêm vào đó, “phát hiện vấn đề” có thể mang nhiều nghĩa. Ở mức dữ liệu, hệ thống tìm các phản hồi có nội dung giống nhau, nhóm chúng và nêu tín hiệu theo thời gian. Ở mức nghiệp vụ, một vấn đề cần được người phụ trách xác nhận là có ý nghĩa, mức độ ưu tiên và hướng xử lý. Khóa luận không coi mọi cụm vector là một sự cố sản phẩm; nó chỉ tạo ứng viên và nguồn đối chiếu. Tương tự, một insight được duyệt là một nhận định có thể dùng trong quy trình quyết định, không phải chân lý vĩnh viễn. Khi dữ liệu mới đến, người dùng có thể cần đánh giá lại.

## 1.8. Câu hỏi nghiên cứu và cách trả lời trong báo cáo

Câu hỏi thứ nhất là làm thế nào để tiếp nhận tệp phản hồi khác cấu trúc mà vẫn giữ nghĩa của dữ liệu và bảo vệ PII. Chương 3 trả lời bằng hồ sơ cột, schema theo product, Gate 1 và pipeline che thông tin; Chương 4 cần chứng minh bằng ca nhập có cột khác tên và dữ liệu giả lập chứa thông tin định danh. Nếu chỉ cho thấy một CSV trùng đúng tên cột cơ sở dữ liệu, câu hỏi này chưa được trả lời đủ. Kết quả kiểm thử môi trường của Presidio cũng cần nêu cùng điều kiện chạy để hội đồng biết giới hạn xác nhận.

Câu hỏi thứ hai là cách biến nhiều phản hồi thành nhận định có thể kiểm tra. Chương 2 phân tích giới hạn của tóm tắt LLM một lượt và vai trò của công cụ xác định. Chương 3 đưa ra query compiler, công cụ thống kê, evidence và graph UNDERSTAND. Chương 4 xem ID run, bộ lọc, số đếm và nội dung finding để kiểm tính truy vết. Một câu trả lời đúng định dạng nhưng không mở được phản hồi nguồn chưa đạt yêu cầu. Câu hỏi này cũng đòi hỏi phân biệt phát biểu quan sát với giả thuyết nguyên nhân.

Câu hỏi thứ ba là cách giữ quyền quyết định của người dùng mà vẫn nhận lợi ích từ AI. Ba Gate tương ứng ba rủi ro: hiểu sai cột, kết luận thiếu căn cứ và ưu tiên hành động sai. Chương 3 mô tả trạng thái và dữ liệu được lưu ở từng Gate; Chương 4 phải kiểm các quyết định duyệt, sửa, từ chối và thao tác lặp. Việc tồn tại một nút “Approve” trên giao diện chỉ là một phần rất nhỏ; giá trị của cơ chế này nằm ở việc lưu được ai duyệt, đã thay gì và tác động của thay đổi lên kết quả phía sau.

Câu hỏi thứ tư là có thể đánh giá tới đâu trong điều kiện dữ liệu và thời gian của khóa luận. Phần khảo sát cung cấp căn cứ thiết kế nhưng không chứng minh lợi ích sau sử dụng. Unit test cung cấp độ tin cậy cho một số hàm, trong khi integration và E2E cần môi trường phụ thuộc. HDBSCAN trên một bộ dữ liệu quá nhỏ có thể cho toàn nhiễu, và thiếu gold label làm F1 chưa tính được. Chương 4 trình bày cả kết quả lẫn khoảng trống này. Một câu trả lời trung thực cho câu hỏi nghiên cứu phải chỉ ra phép đo cần thiết tiếp theo, không thay số đo còn thiếu bằng nhận xét chủ quan.

## 1.9. Cách quản lý minh chứng và đạo đức dữ liệu

Các nguồn dùng trong báo cáo thuộc bốn loại: số liệu khảo sát đã tổng hợp, mã nguồn và cấu hình trong repo, kết quả test hoặc script có thể chạy lại, và tài liệu nghiên cứu/công nghệ trích dẫn. Mỗi loại có giới hạn riêng. Khảo sát có nguồn gốc người thật nhưng bản báo cáo không công khai dữ liệu cá nhân. Mã nguồn cho biết thiết kế được hiện thực tới đâu, không tự chứng minh hiệu quả đầu ra. Một test chạy đạt chứng minh hành vi ở điều kiện test đó, không bảo đảm mọi tình huống. Tài liệu bên ngoài giải thích nguyên lý và công nghệ, không được dùng thay cho minh chứng ứng dụng của đề tài.

Để giữ ranh giới đạo đức, ví dụ phản hồi trong chương đánh giá cần là dữ liệu giả lập hoặc đã che. Không trích nguyên văn câu trả lời mở của khảo sát khi chưa có nhu cầu và đánh giá quyền công bố. Bảng thống kê từ câu hỏi lựa chọn chỉ nêu tần số, tỷ lệ và mẫu số; nhóm quá nhỏ không được ghép nhiều thuộc tính khiến một người có thể bị nhận ra. Các file dữ liệu gốc phục vụ đối chiếu nội bộ, không phải phụ lục phát hành rộng. Khi tạo screenshot demo, người thực hiện phải kiểm lại cả dữ liệu hiển thị trên màn hình và tên tệp trong giao diện.

Sổ cái minh chứng trong thư mục thesis nối từng nhận định quan trọng với đường dẫn nguồn, ngày và trạng thái xác nhận. Những kết quả từ handoff hoặc báo cáo giai đoạn trước được ghi “lịch sử”; kết quả chạy trên working tree hiện tại được ghi riêng. Nếu repo thay đổi sau khi dựng bản nộp, cần chạy lại phép thử quan trọng và cập nhật bảng kết quả thay vì giữ số cũ. Quy trình này không làm khóa luận dài hơn một cách hình thức; nó làm cho mỗi kết luận có điều kiện kiểm tra rõ ràng, phù hợp với tính chất của một đồ án phần mềm có thành phần AI.
