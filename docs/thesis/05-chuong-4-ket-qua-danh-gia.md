# CHƯƠNG 4. KẾT QUẢ XÂY DỰNG, KIỂM THỬ VÀ ĐÁNH GIÁ

## 4.1. Điều kiện đánh giá và nguồn minh chứng

### 4.1.1. Môi trường chạy

Ứng dụng được xây dựng với backend Python 3.12/FastAPI, frontend Next.js và PostgreSQL managed trên Supabase. Trong phát triển, backend và frontend chạy native trên Windows; không dùng Docker. Tích hợp mô hình ngôn ngữ và embedding đi qua API của nhà cung cấp được cấu hình trong môi trường. Presidio và tài nguyên Stanza được dùng cho bước che thông tin cá nhân. Cấu hình chính và các phiên bản thư viện được khóa trong `backend/uv.lock` và `frontend/pnpm-lock.yaml`; bản báo cáo không đưa khóa API hoặc chuỗi kết nối thật vào phụ lục.

Các kết quả ở chương này có hai loại. Loại thứ nhất là **kết quả kiểm tra lại trên working tree ngày 24/9/2026** được thực hiện khi soạn báo cáo. Loại thứ hai là **minh chứng lịch sử** ghi trong report/handoff từ tháng 8–9/2026. Hai loại được đặt tách trong bảng để tránh cộng số test từ phiên bản khác nhau. Working tree hiện có nhiều thay đổi chưa commit, vì vậy những kết quả mới chỉ mô tả bản mã nguồn tại thời điểm kiểm tra, chưa phải một bản phát hành đã khóa commit. Trước khi bảo vệ cần chốt commit hoặc gắn tag và chạy lại lệnh kiểm chứng trên trạng thái sạch.

### 4.1.2. Dữ liệu dùng trong đánh giá

Dữ liệu khảo sát 36 người được dùng để hiểu nhu cầu, không dùng làm tập phản hồi để kiểm tra chất lượng phân loại. Repo có fixture CSV 20 phản hồi cho kiểm thử và tệp demo CSV hiện gồm 19 bản ghi dữ liệu. Tài liệu `docs/evidence/demo-dataset-shape.json` ghi metadata của một bộ dữ liệu giả lập 650 dòng theo kế hoạch đã bị thay thế; tệp hiện hữu không phải bộ 650 dòng đó. Do vậy không được viết “hệ thống được đánh giá trên 650 phản hồi” khi không tạo, đóng băng và chạy phép đo trên chính bộ đó.

Một số kiểm thử tích hợp dùng Supabase thật và dữ liệu giả lập; các test này có điều kiện về kết nối mạng và cơ sở dữ liệu. Bản khảo sát hiện tại không chạy lại toàn bộ nhóm integration để tránh tác động tới dữ liệu dev đang được dùng. Kết quả integration trong các handoff được ghi rõ ngày và chức năng tương ứng, không được suy rộng cho toàn bộ mã nguồn ngày 24/9. Kết quả chất lượng đầu ra LLM cũng không được đo bằng bộ nhãn chuẩn độc lập; phần dưới tập trung vào hành vi phần mềm và chỉ nêu số liệu AI đã được kiểm chứng theo đúng phạm vi.

## 4.2. Kết quả xây dựng theo quy trình nghiệp vụ

### 4.2.1. LISTEN: tiếp nhận và chuẩn hóa

Người dùng có thể tạo product, tải CSV và xem hồ sơ cột trước khi yêu cầu mô hình đề xuất mapping. Endpoint upload tạo import ở trạng thái `profile_ready`; hồ sơ có thông tin tên cột, kiểu/đặc trưng và ví dụ đã che thông tin cá nhân. Việc gọi mô hình là một bước khác, có receipt và trạng thái `mapping_generating`. Kết quả chuyển sang `mapping_review` để người dùng quyết định ở Gate 1. Hệ thống kiểm tra việc có cột nội dung, trường đích không trùng và cột mơ hồ đã được xử lý. Khi hợp lệ, import chạy nền, tạo phản hồi gắn với product và báo tổng số thành công/thất bại.

Sự tách giữa upload và gọi AI có ý nghĩa vận hành: nếu người dùng chỉ muốn kiểm tra một tệp, họ có thể dừng trước khi phát sinh lời gọi mô hình. Tính năng này được kiểm tra ở các bài test hợp đồng phase 28 và được thể hiện trong luồng Importer. Cơ chế lưu tệp gốc hiện là thư mục local `backend/storage/imports`, không phải Supabase Storage. Do đó phương án sao lưu hoặc chia sẻ tệp khi chuyển sang VPS chưa thể mô tả như đã hoàn tất.

### 4.2.2. Phân tích phản hồi và khám phá dữ liệu

Sau nhập, người dùng chọn những phản hồi cần phân tích trong đúng import. Preview cho biết số mục và số lượt gọi logic; một run tối đa 100 mục. Runner gọi classifier với văn bản đã che, lưu chủ đề, sentiment, severity và loại vấn đề AI trong `ai_analysis`, rồi tạo embedding và metadata mô hình. Chế độ batch gom tối đa 10 phản hồi vào một yêu cầu phân loại logic; hệ thống kiểm tra ID trả về để tránh gán nhãn của mục này cho mục khác. Kết quả có thể được xem ở Feedback Vault; một feedback có vector có thể tìm các mục gần nhất bằng cosine.

Data Graph và các endpoint báo cáo cung cấp các cách nhìn theo chủ đề, thời gian và thuộc tính sản phẩm. Phân cụm HDBSCAN gán cluster khi đủ cấu trúc trong dữ liệu. Hệ thống giữ phản hồi nhiễu ở kho phản hồi. Một kết quả thử nghiệm 25 mẫu lưu trong repo cho thấy tất cả được gán nhiễu ở các cấu hình `min_cluster_size` 5, 8, 10 và 15. Đây là minh chứng rằng với tập nhỏ hoặc quá phân tán, giao diện không thể dựa hoàn toàn vào cụm để hiển thị vấn đề. Tìm kiếm tương tự và thống kê vẫn cần hoạt động khi số cụm bằng 0.

### 4.2.3. UNDERSTAND: nhận định có thể truy vết

Người dùng gửi câu hỏi gắn với product qua API hoặc giao diện. Graph UNDERSTAND chạy các node nạp ngữ cảnh, lập kế hoạch, gọi công cụ, đánh giá và tổng hợp. Bản ghi evidence nêu công cụ đã gọi và kết quả trả về. Insight nháp lưu `finding`, độ tin cậy của finding, giả thuyết riêng, bối cảnh ảnh hưởng, giới hạn và mã bằng chứng. Gate 2 dừng để chờ quyết định của người dùng. Trên giao diện Reports, người dùng có thể nhìn thấy nội dung và bằng chứng trước khi chấp nhận, sửa, từ chối hoặc yêu cầu Agent điều tra thêm.

Trên phiên bản đang kiểm tra, các test trong `test_understand_agent.py` mô tả đường duyệt, sửa có che lại PII và quay lại planner khi điều tra thêm. Handoff ngày 2/9 đã thử hai run giả lập qua graph thật, trong đó một run có ba evidence và cả hai được duyệt sau interrupt. Handoff cũng ghi một lỗi vòng đời: run vẫn `running` sau duyệt; vì vậy kết quả lịch sử đó chỉ chứng minh một số bước orchestration, không đủ để nói toàn bộ vòng đời run đã hoàn thiện. Trước khi bảo vệ cần kiểm tra lại bằng API trên commit khóa sổ.

### 4.2.4. ACT: đề xuất và quyết định

ACT chỉ tạo phương án xử lý từ insight đã được duyệt. Dịch vụ gọi mô hình để xác định nhóm nghiệp vụ liên quan và sinh đề xuất, nhưng phép tính điểm ưu tiên dùng công thức xác định. Nếu người dùng sửa tác động, công sức hoặc mức cấp bách, hệ thống giữ giá trị do AI tạo, ghi giá trị được sửa và tính lại điểm. Giao diện Priority Matrix hiển thị các action theo tác động/công sức; Stakeholders tổ chức theo nhóm nghiệp vụ. Không có thao tác gửi lệnh thực hiện công việc ra hệ thống bên ngoài trong phạm vi phiên bản này.

Handoff FE-12 ngày 15/9 ghi nhận một luồng thử qua frontend và API: import 5/5, analysis 5/5, một run Agent tạo tám bằng chứng, Gate 2 chấp nhận insight, ACT sinh bảy action, Gate 3 sửa một giá trị impact từ 9 xuống 6 và điểm ưu tiên được tính lại từ 8,10 xuống 7,40. Đây là một kịch bản lịch sử có dữ liệu và thời điểm cụ thể, không phải số liệu trung bình hoặc kết quả chạy lại ngày 24/9. Thông tin này có thể dùng minh họa tính nối tiếp của sáu màn hình, sau khi kiểm chứng lại trạng thái mã nguồn và bảo đảm ảnh chụp không có dữ liệu cá nhân thô.

## 4.3. Kết quả kiểm thử phần mềm

### 4.3.1. Kiểm thử tự động tại thời điểm soạn báo cáo

Ngày 24/9/2026, lệnh `frontend/node_modules/.bin/vitest.cmd run` cho kết quả **9 tệp test đạt, 39 test đạt**. Các test tập trung vào logic điều hướng và biểu diễn màn hình: graph, matrix, phân nhóm bộ phận và một số quy tắc giao diện khác. Kết quả này chứng minh những kiểm tra tự động hiện có đạt trên working tree lúc chạy; nó không chứng minh từng màn hình đã được người dùng thử trong trình duyệt.

Lệnh backend `.venv/Scripts/python.exe -m pytest -m 'not integration' -q` cho **76 đạt, 1 lỗi, 4 bỏ qua; 87 test integration bị loại theo marker**. Test lỗi là `test_mode_reports_full_or_fallback`: Presidio khởi tạo ở chế độ `regex_only` vì tiến trình kiểm thử không được phép đọc `resources.json` của Stanza tại thư mục ngoài workspace. Đặt `STANZA_RESOURCES_DIR=D:/stanza_resources` rồi chạy lại cả nhóm không giải quyết được lỗi vì sandbox vẫn từ chối đọc tài nguyên này. Đây là lỗi điều kiện chạy của ca kiểm thử cụ thể, đồng thời cho thấy tại phiên chạy này không thể xác nhận PII full mode. Không được báo “backend test xanh” hay “Stanza full mode đã kiểm chứng” cho phiên hiện tại. Các test khác trong lượt đó đạt, nhưng cần chạy lại trên môi trường được cấp quyền đọc tài nguyên Stanza để chốt kết luận.

Lệnh kiểm tra kiểu frontend `tsc --noEmit` chưa đạt: file `.next/dev/types/validator.ts` đang có các dòng rời bị lỗi cú pháp. Đây là tệp được Next.js sinh trong thư mục build, còn nguồn TypeScript của ứng dụng chưa được kết luận đúng/sai từ kết quả này. Cần dọn hoặc tạo lại artifact sinh và chạy lại typecheck sau khi không có tiến trình dev server cùng ghi file. Kết quả test Vitest không thay thế cho kiểm tra kiểu. Bảng 4.1 ghi rõ cả kết quả đạt và chưa đạt.

**Bảng 4.1. Kết quả kiểm tra mới trên working tree ngày 24/9/2026**

| Phạm vi | Lệnh hoặc cách kiểm tra | Kết quả | Diễn giải |
|---|---|---|---|
| Frontend unit | `vitest run` | 39/39 đạt | Logic đã có test đạt |
| Backend không integration | `pytest -m 'not integration' -q` | 76 đạt, 1 lỗi, 4 bỏ qua | PII full mode chưa xác nhận trong sandbox |
| Frontend typecheck | `tsc --noEmit` | Chưa đạt | Artifact `.next/dev/types` lỗi cú pháp |
| Backend integration | Chưa chạy lại trong phiên này | Chưa có số mới | Cần Supabase và môi trường phù hợp |

Các số ở Bảng 4.1 phải được cập nhật nếu mã nguồn hoặc môi trường đổi trước khi nộp. Một bản nộp có kiểm thử thất bại có thể chấp nhận về mặt trung thực khoa học nếu giải thích rõ phạm vi và tác động; tuy nhiên trước khi kết luận hệ thống đáp ứng yêu cầu N01, phải kiểm chứng lại Presidio full mode ở môi trường có quyền truy cập tài nguyên.

### 4.3.2. Kiểm thử từng lớp và kịch bản quan trọng

Các file test backend bao phủ ingest, profiler, mapper, classifier, embedding, clustering, analytics tools, UNDERSTAND, ACT, auth, báo cáo và kiểm soát phạm vi/chi phí. Với chức năng nhập, tình huống quan trọng là upload chưa gọi LLM, proposal được tạo khi yêu cầu, Gate 1 chỉ chấp nhận mapping hợp lệ và import không lặp sai. Với runner, các tình huống quan trọng là giới hạn phạm vi theo import, cap 100, xác nhận số item, hủy và tiếp tục. Với Agent, cần kiểm tra tên công cụ, tham số không hợp lệ, bằng chứng không có thật, yêu cầu điều tra thêm và quyết định lặp lại. Với ACT, test kiểm tra insight chưa duyệt không sinh hành động, điểm ưu tiên theo công thức, override giữ giá trị AI và hành động do người dùng thêm.

Kiểm thử phân quyền cần bao gồm cả trường hợp chưa đăng nhập và vai trò không đủ quyền. Chỉ kiểm tra nút bị ẩn trên frontend không đủ, vì endpoint vẫn có thể được gọi trực tiếp. Ngược lại, một test API đạt không bảo đảm người dùng hiểu được lỗi 409 hoặc 422 trên giao diện. Vì thế tiêu chí chấp nhận của luận văn kết hợp kết quả unit/integration với các bước người dùng có thể quan sát. Ma trận yêu cầu–test chi tiết đặt tại Phụ lục D.

### 4.3.3. Minh chứng spike và giới hạn chuyển giao

Trước khi triển khai các mô-đun production, dự án giữ sáu script spike nhằm trả lời những câu hỏi kỹ thuật hẹp. S1 kiểm tra khả năng phát hiện PII Việt–Anh và ghi caveat cho nhận diện tên người. S2 kiểm tra đầu ra JSON schema của một provider cụ thể với 10/10 kết quả hợp lệ tại thời điểm đo. S3 kiểm tra vector 1536 chiều và self-match trên PostgreSQL/pgvector. S4 kiểm tra HDBSCAN trên vector mô phỏng. S5 kiểm tra graph dừng, restart và resume với checkpointer trên PostgreSQL. S6 kiểm tra tương thích Windows–Supabase. Chúng là minh chứng khả thi của từng khối, không tự động chứng minh tất cả các khối vẫn tương thích ở cấu hình provider và mã nguồn mới.

Một kết quả nền khác trong `docs/backend-foundation-report.md` ghi 22 phản hồi được xử lý trong khoảng 4 phút 26 giây và truy vấn tương tự khoảng 280 ms qua mạng ở giai đoạn tháng 8/2026. Các số này có điều kiện WAN, model và schema của phiên bản foundation. Sau đợt tái cấu trúc VoC OS, chưa có lượt đo lại tương đương trong phiên soạn báo cáo, nên không dùng chúng làm hiệu năng của phiên bản hiện tại. Khi đo lại, cần ghi số feedback, cấu hình batch, model, số lần thử do fallback, đường mạng, thời điểm và cách tính trung vị/độ lệch.

## 4.4. Đánh giá chất lượng và tác động trong giới hạn dữ liệu

### 4.4.1. Độ đúng cấu trúc và độ đúng nội dung

Kiểm tra đầu ra có cấu trúc xác nhận rằng JSON có đủ trường, kiểu và miền giá trị. Đây là điều kiện cần để lưu dữ liệu an toàn nhưng không đủ để khẳng định phân loại đúng. Với phân loại feedback, cần một bộ phản hồi có nhãn do người đánh giá gán độc lập và một quy tắc xử lý trường hợp bất đồng trước khi tính precision, recall hoặc F1. Repo hiện chưa cung cấp một bộ chuẩn và kết quả chấm như vậy cho phiên bản VoC OS. Bởi vậy khóa luận không tự tạo số độ chính xác. Mục đánh giá này phân biệt rõ phương pháp cần dùng và những kiểm tra hiện đã có.

### 4.4.2. Đánh giá bằng chứng của insight

Hệ thống có cơ chế không lưu mã evidence không tồn tại trong lượt điều tra. Có thể kiểm tra tỷ lệ insight có ít nhất một mã bằng chứng bằng truy vấn dữ liệu; KPI ở API cũng cho phép tính giá trị này. Nhưng tỷ lệ đó chỉ đo **sự hiện diện của liên kết**, không đo việc bằng chứng có thực sự hỗ trợ câu kết luận. Muốn đánh giá nội dung, cần chọn mẫu insight, đọc từng bằng chứng, chấm riêng ba tiêu chí: phát biểu finding có bám số liệu không, giả thuyết có được ghi là chưa xác nhận không, và giới hạn độ phủ có được nêu đúng không. Nếu không có người chấm và quy trình chấm, báo cáo chỉ được kết luận rằng hạ tầng truy vết đã được xây dựng.

### 4.4.3. Đánh giá quyết định tại ba Gate

Gate 1 có thể đo tỷ lệ proposal mapping được người dùng giữ nguyên hoặc chỉnh. Gate 2 có thể đếm insight chấp nhận, sửa, từ chối và điều tra tiếp. Gate 3 có thể đếm action được chấp nhận, bị sửa ước lượng hoặc loại bỏ; sai khác giữa tác động/công sức do AI và người dùng chọn được tính bằng công thức xác định. Những KPI này mô tả cách người dùng tác động lên đề xuất trong hệ thống. Chúng chưa tự chứng minh rằng mọi quyết định của người dùng tốt hơn AI, cũng chưa thể hiện hiệu quả kinh doanh sau hành động. Mẫu nhỏ, dữ liệu demo và sự thiếu đa dạng product có thể làm các tỷ lệ biến động mạnh.

### 4.4.4. Hiệu năng, chi phí và tác động sau hành động

Các mốc thời gian `time_to_listen`, `time_to_insight` và `time_to_action` được tính trung vị từ các bản ghi hệ thống khi có dữ liệu. `llm_call_logs` giữ loại lời gọi, model, token, độ trễ và lỗi để kiểm soát chi phí. Nếu một provider từ chối chế độ JSON schema, đường fallback có thể tạo thêm request và tăng thời gian; một handoff ngày 2/9 đã ghi nhận tình huống này. Muốn báo cáo độ trễ hiện tại phải có ảnh chụp run và log tương ứng; không thể lấy số từ một lượt chạy mô hình trước rồi gán cho provider hiện nay.

`impact_checks` so số phản hồi phù hợp trong hai cửa sổ thời gian trước/sau một action đã đủ tuổi đo. Nếu trước đó bằng 0, tỷ lệ thay đổi không được tính. Số lượng sau hành động thay đổi có thể bị ảnh hưởng bởi nhiều yếu tố ngoài action; vì thế đây là tín hiệu theo dõi, không phải kết quả thử nghiệm nhân quả. Hệ thống chưa có dữ liệu đối chứng để chứng minh giảm thời gian xử lý hoặc tăng tỷ lệ hành động được thực hiện trong một tổ chức thực tế.

## 4.5. Kịch bản minh họa một vòng xử lý

Một kịch bản demo hợp lệ bắt đầu bằng tệp phản hồi giả lập không chứa dữ liệu cá nhân thật. Người dùng chọn product, tải CSV và xem cấu trúc; upload chưa gọi mô hình. Họ yêu cầu mapping, xem các trường được đề xuất và chốt Gate 1. Sau khi import, họ chọn một nhóm phản hồi để phân tích và xác nhận phạm vi cùng chi phí. Khi runner hoàn thành, họ dùng Data Graph hoặc Feedback Vault để đặt câu hỏi cho UNDERSTAND. Agent gọi công cụ, lưu evidence và tạo insight; người dùng so số liệu với finding và đánh dấu rằng hypothesis chưa được xác nhận, rồi duyệt ở Gate 2. ACT sinh các phương án liên quan, đặt vào ma trận; người dùng sửa điểm tác động, quan sát điểm ưu tiên đổi và chấp nhận ở Gate 3. Kết quả cuối là một insight và một tập action có nguồn gốc, trạng thái và lịch sử chỉnh sửa.

Kịch bản này chứng minh luồng có thể đi qua các thành phần nếu được chạy và lưu bằng chứng. Handoff ngày 15/9 ghi một lượt tương tự với 5 phản hồi và 7 action. Khi trình bày cho hội đồng, cần quay lại từ đầu với dữ liệu giả lập mới hoặc từ bản trạng thái đã chốt, ghi ID run và ảnh thật tại các bước quan trọng. Các ảnh trong `docs/design/` chỉ diễn đạt ý đồ giao diện, không thay thế cho ảnh chụp hệ thống chạy. Dữ liệu đầu vào và đầu ra đưa vào slide cần qua bước kiểm tra PII.

## 4.6. Thảo luận kết quả, hạn chế và hướng cải tiến

Về chức năng, cấu trúc hiện tại đã có các thành phần chính từ nhập liệu đến đề xuất hành động và các điểm duyệt ở từng giai đoạn. Về kiểm chứng, nhóm unit frontend đạt trên phiên chạy mới; backend đạt phần lớn test không integration nhưng ca Presidio full mode thất bại trong môi trường bị giới hạn quyền đọc tài nguyên. Typecheck frontend cũng chưa qua do file build sinh sai. Điều này không cho phép trình bày sản phẩm ở trạng thái “mọi kiểm thử đều xanh”. Hệ thống cần một lượt kiểm chứng trên môi trường tái lập và mã nguồn được đóng băng trước khi phát hành bản nộp cuối.

Giới hạn dữ liệu ảnh hưởng trực tiếp tới khả năng phát hiện cụm và đo độ đúng AI. Tập 25 phản hồi phân tán cho kết quả toàn nhiễu; bộ 650 phản hồi trong metadata không phải bộ dữ liệu hiện có để đánh giá; chưa có gold label độc lập cho phân loại. Giới hạn kiến trúc gồm tác vụ nền theo tiến trình ứng dụng, tệp import lưu local và phụ thuộc dịch vụ ngoài. Giới hạn đánh giá gồm khảo sát thuận tiện 36 người, thiếu thử nghiệm người dùng đối chứng và thiếu phép đo tải trên VPS. Việc nêu rõ các giới hạn này giúp xác định chính xác đóng góp của hệ thống: một quy trình ứng dụng có các cơ chế kiểm soát và truy vết, đã được kiểm thử ở những phạm vi cụ thể, còn chất lượng kết quả AI và tác động kinh doanh cần nghiên cứu tiếp.

Hướng cải tiến theo thứ tự hợp lý là: chốt môi trường Stanza và làm sạch artifact build để có bộ kiểm thử tái lập; chuẩn bị bộ phản hồi giả lập Việt–Anh kèm nhãn tham chiếu và quy tắc chấm; đo riêng chất lượng phân cụm trên các mức kích thước dữ liệu; đánh giá insight bởi người kiểm tra độc lập; sau đó thử vận hành trên hạ tầng VPS và lưu trữ tệp bền vững. Các bước này tạo ra chứng cứ mới trước khi thêm những tính năng thu thập tự động hoặc cơ chế thực thi hành động bên ngoài.

## 4.7. Ma trận kiểm chứng theo yêu cầu hệ thống

Một đánh giá có thể kiểm tra lại cần nối từ yêu cầu ở Chương 3 đến thao tác thử, điều kiện đạt và kết quả thực tế. Trong phạm vi bản thảo, không phải ô nào của ma trận cũng có số đo hoàn chỉnh; việc giữ ô “chưa kiểm chứng” rõ ràng ngăn người đọc nhầm đặc tả kiểm thử với kết quả. Bảng 4.2 mô tả những phép thử có giá trị cho bản nộp cuối và tình trạng minh chứng hiện có. Các tiêu chí này tập trung vào luồng có rủi ro cao: nhập dữ liệu có PII, lọc theo product, duyệt insight, tính điểm action và tái lập báo cáo.

**Bảng 4.2. Ma trận yêu cầu, phép thử và trạng thái minh chứng**

| Yêu cầu | Tình huống kiểm tra | Điều kiện đạt | Trạng thái tại bản thảo |
|---|---|---|---|
| F03–F04 | CSV đổi tên cột và thiếu trường bắt buộc | Gate 1 yêu cầu duyệt, không nhập sai | Có mã nguồn và test; cần E2E mới |
| F05 | Chạy phân tích hai lần cùng phạm vi | Không nhân đôi kết quả hoặc chạy song song sai | Có runner; chưa đo lại E2E |
| F06 | Tìm tương tự trên cùng product | Kết quả có phạm vi, mở được nguồn | Có API; thiếu tập relevance gold |
| F07–F08 | Agent thiếu evidence rồi xin duyệt | Không tự coi hypothesis là finding; có checkpoint | Có graph; cần kiểm tra độc lập |
| F09 | Người dùng sửa impact/effort | Điểm và vùng ma trận cập nhật, giá trị AI giữ nguyên | Có logic và unit test liên quan |
| F10 | Báo cáo KPI thiếu dữ liệu đầu vào | Trả chưa xác định thay vì số giả | Có quy tắc tính; chưa có đo production |
| N01 | Phản hồi chứa email, số điện thoại, CCCD | Prompt và API chỉ có bản đã che | Unit chưa xanh toàn bộ trong sandbox |
| N02 | Duyệt sửa một insight | Evidence/run/decision liên kết | Có model; cần lượt E2E mới |

Các hàng trong bảng không phải tuyên bố tất cả điều kiện đạt. Chẳng hạn, trường hợp F06 cần một tập truy vấn và nhãn liên quan độc lập; API trả kết quả đúng định dạng chưa đủ để nói tìm kiếm có độ chính xác cao. F07–F08 cần so nội dung finding với evidence, việc graph đến được trạng thái chờ duyệt mới chỉ kiểm tra đường đi. N01 có mức ưu tiên đặc biệt vì một lỗi che thông tin có thể làm lộ dữ liệu trước khi người dùng nhìn thấy giao diện. Kết quả test Presidio không đạt trong sandbox buộc bản đánh giá hiện tại giữ trạng thái chưa xác nhận full mode.

### 4.7.1. Ca kiểm thử đầu vào và dữ liệu biên

Với CSV, bộ ca cần ít nhất một tệp hợp lệ có tiếng Việt Unicode, một tệp có cột nội dung tên khác, một tệp thiếu nội dung phản hồi, một tệp có ngày sai định dạng và một tệp có dòng trùng ID nguồn. Kết quả cần ghi số dòng được nhận, số dòng bỏ, lý do bỏ và ID import. Khi tệp có email hay số điện thoại giả lập, chỉ dùng chuỗi nhân tạo được tạo cho test; không dùng câu trả lời khảo sát nguyên văn. Preview phải đủ để người dùng quyết định mapping nhưng không hiện dữ liệu chưa che. Đây là điểm phải kiểm cả response API lẫn phần trình bày frontend, vì một lớp có thể đúng trong khi lớp kia làm lộ giá trị.

Ca phân tích cần gồm phản hồi đơn ngôn ngữ Việt, đơn ngôn ngữ Anh và một câu trộn thuật ngữ hai ngôn ngữ. Mục đích không phải để tuyên bố một tỷ lệ chính xác từ ba câu, mà để xác nhận pipeline không sụp đổ vì mã Unicode và schema đầu ra có đủ trường. Có thể thêm chuỗi rất ngắn, chuỗi dài và chuỗi có nhiều chủ đề để tìm lỗi giới hạn token hoặc validate JSON. Với mỗi ca, lưu bản đã che, model ID, prompt version và trạng thái; nếu provider trả JSON không hợp lệ, kiểm đường fallback rồi lỗi cuối. Những ca này tạo điều kiện đánh giá tái lập khi thay provider.

Ca query compiler phải thử field có trong active schema, field lõi được hỗ trợ và field không tồn tại. Với field lạ, điều kiện đạt là từ chối có kiểm soát, không phải trả danh sách rỗng như thể không có phản hồi nào. Một bộ lọc `product_id` khác phải không truy cập dữ liệu của sản phẩm đang mở. Ca taxonomy cần kiểm nhãn ở trạng thái chờ duyệt có được sử dụng như nhãn chính thức hay không. Nếu hệ thống hợp nhất hai chủ đề, cần giữ đường truy về nhãn gốc để các biểu đồ lịch sử không đổi nghĩa mà người dùng không biết.

### 4.7.2. Ca kiểm thử quyết định và khôi phục

Gate 1 cần thử phê duyệt mapping đề xuất, sửa mapping trước khi duyệt, hủy import và gửi lại cùng yêu cầu. Kết quả mong muốn là một phiên bản schema active hợp lệ, không có hai bản cùng active và không có dòng nhập đôi khi thao tác được gửi lại. Gate 2 cần thử bốn hướng quyết định, nhất là yêu cầu điều tra thêm sau khi đã có evidence. Lúc tiếp tục, graph phải giữ câu hỏi và các quan sát trước, tránh lặp vô hạn nhờ ngân sách vòng. Một quyết định mới gửi lên run đã đóng cần trả lỗi trạng thái có thể hiểu.

Gate 3 cần thử một insight đã duyệt nhưng không có nhóm nghiệp vụ nào vượt ngưỡng relevance. Kết quả rỗng có giải thích hợp lý tốt hơn việc buộc mô hình tạo việc không liên quan. Sau đó thử một action được chỉnh impact, effort và urgency: điểm ưu tiên phải tính lại từ giá trị hiệu lực, vùng ma trận cũng thay đổi nếu vượt ngưỡng. Khi sinh lại candidate, action đã chỉnh hoặc accepted phải được giữ. Cuối cùng, phải kiểm hai người dùng gửi quyết định gần nhau; hệ thống cần báo xung đột trạng thái thay vì ghi đè không dấu vết. Đây là những ca quan trọng để biến “Human-in-the-Loop” thành cơ chế có kiểm soát thật.

### 4.7.3. Ca kiểm thử khả năng quan sát

Lệnh test và ảnh demo chỉ là một phần của minh chứng. Với một run xuyên suốt, cần xuất một bảng gồm import ID, analysis run ID, agent run ID, insight ID, evidence IDs, action IDs, quyết định Gate 1–3 và thời điểm tương ứng. Số liệu token, độ trễ và loại lỗi trong `llm_call_logs` cho biết run phát sinh chi phí gì. Các giá trị này không cần đưa nguyên văn toàn bộ vào khóa luận, nhưng phải đủ để người kiểm tra tái hiện đường đi từ đầu vào giả lập đến quyết định. Nếu một ID không còn truy cập được hoặc không mở được evidence, bản demo không chứng minh đầy đủ tính truy vết.

## 4.8. Định nghĩa phép đo cần bổ sung trước khi khẳng định hiệu quả

Chất lượng phân loại nên được đo trên bộ phản hồi đã che và gán nhãn độc lập. Đơn vị mẫu, bộ nhãn, quy tắc gán nhiều nhãn và cách xử lý ca mơ hồ cần công bố cùng kết quả. Có thể mời hai người gán nhãn một phần để phát hiện bất đồng; nếu bất đồng cao, một giá trị F1 so với một người gán nhãn chưa phản ánh mục tiêu ổn định. Báo cáo nên nêu số mẫu từng lớp, không chỉ micro-average, bởi lớp safety hoặc lỗi nghiêm trọng có thể rất hiếm nhưng quan trọng. Với ca thiếu nhãn gold, ghi “chưa đo” thay vì dùng confidence do LLM tự trả như xác suất đúng.

Chất lượng nhóm chủ đề cần được xem qua tỷ lệ điểm nhiễu, số cụm, độ ổn định khi đổi tham số và mức đồng nhất ngữ nghĩa do người đánh giá. Một tỷ lệ điểm nhiễu cao có thể là tín hiệu tham số không phù hợp, dữ liệu quá thưa hoặc thực tế phản hồi phân tán; cần xem mẫu cụ thể trước khi kết luận. Kết quả sweep 25/25 nhiễu ở nhiều `min_cluster_size` là minh chứng rằng bộ hiện tại không đủ để chứng minh năng lực phát hiện cụm. Tăng số lượng phản hồi bằng cách nhân bản câu cũ cũng không giải quyết vấn đề, bởi cụm lúc đó có thể phản ánh bản sao nhân tạo.

Đối với thời gian xử lý, phép đo hợp lệ cần định nghĩa điểm bắt đầu và kết thúc. `time_to_listen` có thể đo từ upload đến khi mapping và import hoàn tất; `time_to_insight` từ lúc người dùng yêu cầu điều tra đến khi insight có thể duyệt; `time_to_action` từ insight được duyệt đến quyết định ở Gate 3. Nên báo cáo trung vị và phân vị cao trên nhiều lượt chạy, cùng cấu hình máy, provider, quy mô tệp và tình trạng cache. Một số đo ở lần chạy duy nhất không khái quát được độ trễ của toàn bộ hệ thống. Nếu người dùng dừng vài giờ ở một Gate, cần tách thời gian máy xử lý khỏi thời gian chờ con người.

Tác động tổ chức đòi hỏi phép đo khác hoàn toàn. Có thể chọn các nhóm xử lý phản hồi tương đương và đo thời gian từ phản hồi đầu tiên đến lúc nhận ra vấn đề, số vấn đề có evidence đầy đủ, tỷ lệ quyết định được thực hiện và mức hài lòng của người dùng nội bộ. Các biến như mùa vụ, số lượng phản hồi, độ khó sản phẩm và kinh nghiệm người phân tích cần được ghi để diễn giải. Trong khóa luận này chưa có thử nghiệm đó; vì vậy chỉ có thể nói hệ thống hỗ trợ một quy trình có cấu trúc và tạo khả năng đo, chưa thể kết luận làm giảm bao nhiêu phần trăm công sức của tổ chức.

Một phép so sánh công bằng với bảng tính thủ công hoặc tóm tắt LLM một lượt cũng cần cùng bộ dữ liệu và tác vụ. Người tham gia nên tìm cùng một loại vấn đề và đề xuất hành động dưới cùng thời hạn, sau đó được chấm bằng tiêu chí đã định trước. Nếu chỉ dùng cảm nhận của tác giả hoặc chọn ví dụ mà hệ thống hoạt động tốt, kết luận sẽ thiên lệch. Bảng 2.1 vì vậy là đối chiếu thiết kế, không phải kết quả thí nghiệm đối chứng. Việc phân biệt này giúp khóa luận đánh giá đúng mức đóng góp hiện có và cho thấy bước thực nghiệm cần làm tiếp.

## 4.9. Kế hoạch đóng băng kết quả cho bản nộp cuối

Bản nộp cuối cần gắn với một trạng thái mã nguồn xác định. Trước khi đóng băng, người thực hiện ghi commit, phiên bản Python/Node, cấu hình provider không chứa bí mật và phiên bản migration. Sau đó chạy lại cùng một bộ lệnh test, lưu đầu ra tóm tắt và đánh dấu điều kiện phụ thuộc cơ sở dữ liệu hoặc tài nguyên ngôn ngữ. Nếu một test chỉ chạy đạt trên máy cá nhân nhưng không đạt trong sandbox, phải nêu cả hai môi trường và nguyên nhân được xác minh. Không nên xóa một ca thất bại khỏi bảng chỉ vì nó cản trở mô tả hệ thống “hoàn tất”.

Một kịch bản demo được đóng băng cần có tệp phản hồi giả lập, product mới, ba quyết định Gate và danh sách ID thu được. Bắt đầu từ một trạng thái trống giúp tránh việc báo cáo vô tình sử dụng insight được tạo ở lần demo trước. Khi kết thúc, cần xuất bảng phản hồi đã che, evidence, insight, action và decision log liên quan. Tập đầu ra này cho phép hội đồng mở lại từng bước. Nếu một bước gọi dịch vụ AI không chạy vì hết quota hoặc provider lỗi, kết quả phải ghi thất bại thật, không điền bằng output của một run khác. Có thể chạy lại, nhưng phải giữ ID và thời gian của lượt mới.

Ảnh chụp màn hình trong Chương 4 nên được lấy từ cùng một lần chạy E2E. Tại Importer, ảnh cho thấy mapping đã duyệt; tại Reports, ảnh cho thấy finding tách hypothesis và ID evidence; tại Priority Matrix, ảnh cho thấy ít nhất một giá trị được người dùng sửa và điểm tính lại. Mỗi hình cần chú thích ngắn nói nó chứng minh điều gì và giới hạn gì. Ảnh chỉ đẹp về mặt giao diện nhưng không đọc được trạng thái hoặc nguồn dữ liệu không thay thế được bảng kết quả test. Các bản thiết kế ở Hình 3.4–3.8 vẫn hữu ích để giải thích ý đồ, nhưng không được chuyển tên thành “giao diện đã triển khai”.

Một lượt kiểm tra độc lập trước khi nộp cần đối chiếu các số liệu giữa tóm tắt, Chương 1, Chương 4 và phụ lục. Chẳng hạn, 36 người khảo sát là mẫu người trả lời; 25 phản hồi trong sweep phân cụm là tập kiểm thuật toán; 19 dòng trong `backend/demo_dataset.csv` là file demo hiện còn. Ba số này mô tả ba đối tượng khác nhau và không được cộng, thay thế hoặc so sánh trực tiếp. Các con số lịch sử như 22 phản hồi ở backend foundation hoặc 5 phản hồi của một handoff cần ghi rõ ngày, kiến trúc tương ứng và lý do chỉ dùng làm bối cảnh. Đây là bước kiểm tính nhất quán của báo cáo, không phải thay đổi dữ liệu.

Cuối cùng, việc đạt đủ số trang không đồng nghĩa với đạt yêu cầu học thuật. Phần Mở đầu đến Kết luận phải có nội dung liên quan, không lấp bằng ảnh lớn hoặc bảng lặp. Chương 2 cần nêu nguyên lý và lý do chọn công nghệ; Chương 3 cần mô tả cách thiết kế để người khác có thể xây dựng tương đương; Chương 4 cần có phép thử, số liệu và giới hạn tương xứng. Nếu một kết quả còn thiếu, bản nộp nên nói rõ thay vì kéo dài phần mô tả kiến trúc để che khoảng trống. Phần Turnitin và chữ ký hướng dẫn là điều kiện hành chính riêng cần hoàn tất trước bản in/PDF chính thức.
