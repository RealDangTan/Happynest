# CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ CÁC GIẢI PHÁP LIÊN QUAN

## 2.1. Phản hồi người dùng và quy trình Voice of Customer

Phản hồi người dùng là mô tả, đánh giá hoặc yêu cầu mà một cá nhân gửi về trải nghiệm của họ với sản phẩm. Một phản hồi không nhất thiết là báo cáo lỗi: nó có thể khen một tính năng, yêu cầu thay đổi, kể lại trở ngại trong một hoàn cảnh cụ thể hoặc cảnh báo hậu quả của câu trả lời AI. Khi phân tích phản hồi, điều cần tìm không chỉ là số lượt nhắc đến một từ. Người phân tích phải đặt nội dung bên cạnh thời gian, nguồn, phiên bản và nhóm người dùng để hiểu vấn đề ảnh hưởng tới ai và đang thay đổi như thế nào.

Voice of Customer (VoC) có thể được xem như quá trình biến phát biểu rời rạc của người dùng thành thông tin hỗ trợ quyết định. Trong phạm vi đề tài, quy trình được tổ chức thành ba câu hỏi. LISTEN trả lời “dữ liệu nào đã được tiếp nhận và hiểu đúng cấu trúc chưa?”. UNDERSTAND trả lời “tín hiệu nào có thể chứng minh từ dữ liệu và giới hạn của nó là gì?”. ACT trả lời “nhóm sản phẩm có thể cân nhắc việc gì tiếp theo?”. Việc tách ba giai đoạn giúp xác định vị trí kiểm tra thủ công: sai ánh xạ cột ở đầu vào sẽ làm hỏng mọi phân tích sau đó; một nhận định chưa đủ bằng chứng không nên trở thành quyết định; và một hành động có ảnh hưởng kinh doanh vẫn cần người phụ trách chấp nhận.

Phản hồi về sản phẩm AI có thêm các nhãn cần cân nhắc như câu trả lời sai, bịa đặt, thiên lệch, vấn đề an toàn và quyền riêng tư. Một văn bản ngắn có thể chứa nhiều tín hiệu đồng thời. Hệ thống vì vậy lưu nhãn chủ đề, mức độ nghiêm trọng, cảm xúc, loại vấn đề AI và mức tự đánh giá của mô hình thành các thuộc tính khác nhau. Các thuộc tính này có tác dụng lọc và tổng hợp, nhưng không thay thế bằng chứng nguyên thủy đã được che thông tin. Một nhãn “nghiêm trọng” chỉ là kết quả phân loại; người duyệt cần xem ngữ cảnh trước khi thực hiện thay đổi sản phẩm.

## 2.2. Chuẩn hóa nguồn dữ liệu và schema động

### 2.2.1. Sự khác biệt giữa các tệp phản hồi

Hai tệp CSV cùng nói về phản hồi có thể có cấu trúc khác nhau. Một tệp dùng cột `content` cho văn bản, tệp khác dùng `message`; thời gian có thể nằm trong `created_at`, `submitted_at` hoặc tên cột tiếng Việt. Các cột về gói dịch vụ, phiên bản và phân khúc khách hàng có thể chỉ tồn tại ở một nguồn. Ánh xạ mọi tệp theo một bộ tên cố định khiến một phần dữ liệu bị bỏ qua hoặc bị gán sai. Ngược lại, cho phép mọi cột mới trở thành cột vật lý của bảng sẽ tạo ra schema khó duy trì.

Giải pháp của đề tài sử dụng hồ sơ cột, đề xuất ánh xạ và một schema theo sản phẩm. Trước khi một dòng được nhập, hệ thống xem tên cột, kiểu giá trị và ví dụ đã che thông tin cá nhân. Một bộ ánh xạ được đề xuất để người dùng xác nhận hoặc sửa. Các trường chung như nội dung, nguồn và thời gian có vị trí xác định; thuộc tính sản phẩm linh hoạt được lưu trong vùng `data`; metadata chỉ có ý nghĩa với nguồn nằm trong `source_meta`. Kết quả diễn giải của AI nằm ở `ai_analysis`. Sự phân tách này ngăn trộn dữ liệu do khách hàng cung cấp với nhãn do hệ thống sinh ra.

PostgreSQL hỗ trợ JSONB để lưu đối tượng có cấu trúc biến đổi trong cùng một bảng. Tuy nhiên, JSONB không tự giải quyết vấn đề ngữ nghĩa: nếu hai tên cột cùng chỉ một khái niệm, vẫn cần quy tắc chuẩn hóa và phiên bản schema. Hệ thống dùng danh sách trường hợp lệ của sản phẩm để kiểm tra yêu cầu của công cụ phân tích, nhờ đó câu hỏi từ mô hình không được biến thành truy vấn tùy ý trên cơ sở dữ liệu. Việc đổi schema cũng cần có bản ghi phiên bản để người dùng biết dữ liệu từng được nhập theo cách hiểu nào.

### 2.2.2. Taxonomy và độ phủ dữ liệu

Taxonomy là cấu trúc nhãn chủ đề được quản lý theo sản phẩm. Nếu tên chủ đề mới xuất hiện trong phản hồi, không thể lập tức coi đó là một chủ đề chuẩn. Cần xem liệu nó thực sự mới, chỉ là biến thể của nhãn cũ, hay một cách diễn đạt quá hẹp. Quy trình của hệ thống giữ nhãn mới ở trạng thái chờ và hỗ trợ người dùng chấp nhận, nhập vào nhãn có sẵn hoặc từ chối. Bước này giảm nguy cơ phát sinh nhiều nhãn tương đương khi mô hình phân loại gặp văn bản đa ngôn ngữ.

Độ phủ của một trường là tỷ lệ phản hồi có giá trị sử dụng được cho trường đó. Ví dụ, nếu thuộc tính phiên bản chỉ có trong 30% phản hồi, một kết luận “vấn đề tập trung ở phiên bản X” cần nêu giới hạn mẫu. Khi công cụ thống kê trả về con số, độ phủ phải đi kèm để người đọc hiểu mẫu số. Đây là lý do bản thiết kế không chỉ lưu nhãn và phép đếm, mà còn lưu thông tin về điều kiện hình thành nhận định.

## 2.3. Mô hình ngôn ngữ lớn và đầu ra có cấu trúc

### 2.3.1. Phân loại văn bản tiếng Việt–Anh

Mô hình ngôn ngữ lớn có thể nhận văn bản và trả về nhãn phân loại dựa trên hướng dẫn. Với dữ liệu tiếng Việt–Anh trộn lẫn, mô hình có thể tận dụng cả ngữ cảnh câu và thuật ngữ kỹ thuật. Trong hệ thống của đề tài, prompt phân loại mô tả các nhãn chủ đề, loại vấn đề AI, cảm xúc, mức nghiêm trọng, cờ an toàn và mức tự đánh giá. Nếu sản phẩm đã có taxonomy, tên nhãn được đưa vào prompt để giảm việc tạo thêm chủ đề trùng lặp. Kết quả sau đó được kiểm tra bằng schema dữ liệu của ứng dụng trước khi lưu.

Một mô hình có thể trả lời hợp ngữ pháp nhưng không đúng định dạng yêu cầu, ví dụ thêm văn bản ngoài JSON, thiếu khóa bắt buộc hoặc cung cấp nhãn ngoài miền giá trị. Bởi vậy, hệ thống ưu tiên chế độ `json_schema`, rồi có đường dự phòng dùng hướng dẫn JSON và kiểm tra bằng Pydantic. Các lần thử và lỗi được ghi thành metadata. Cơ chế này nâng độ bền của giao tiếp API; nó không đảm bảo nhãn đúng về mặt nội dung. Chuẩn JSON Schema mô tả khả năng kiểm tra cấu trúc dữ liệu, không phải xác minh sự thật của một câu trả lời [1].

### 2.3.2. Giới hạn của mô hình trong quy trình ra quyết định

Mô hình có thể tự đưa ra một mức “confidence” nhưng giá trị đó chưa chắc tương ứng với xác suất đúng đã được hiệu chuẩn. Một tóm tắt có thể bỏ qua phản hồi trái chiều; một phỏng đoán về nguyên nhân có thể bị trình bày như sự kiện. Vì vậy, đề tài thiết kế phần `finding` cho điều quan sát được và phần `hypothesis` cho cách giải thích còn phải kiểm tra. Khi không đủ bằng chứng, kết quả phải chỉ ra điều thiếu thay vì cưỡng ép một kết luận mạnh. Người dùng nhìn thấy nguồn bằng chứng và hạn chế trước khi chấp nhận báo cáo.

Trong tương tác giữa con người và hệ thống AI, khả năng sửa, bác bỏ và khôi phục quyết định là quan trọng. Bộ hướng dẫn tương tác người–AI của Amershi và cộng sự nhấn mạnh việc thể hiện khả năng của AI, hỗ trợ sửa sai và cho phép kiểm soát khi AI không đáp ứng kỳ vọng [2]. Đề tài áp dụng tinh thần này qua ba điểm duyệt, nhưng không tuyên bố đã đánh giá định lượng mức độ tin cậy của người dùng.

## 2.4. Biểu diễn vector, tìm kiếm và phân cụm

### 2.4.1. Embedding và độ tương đồng cosine

Embedding biến một đoạn văn bản thành một vector số trong không gian nhiều chiều. Hai câu diễn đạt gần ý nhau có thể có vector gần nhau ngay cả khi không trùng từ. Công trình Sentence-BERT của Reimers và Gurevych là một ví dụ nền tảng cho hướng biểu diễn câu để so sánh ngữ nghĩa [3]. Ứng dụng trong khóa luận không sử dụng chính mô hình Sentence-BERT; nó gọi một dịch vụ embedding qua API tương thích OpenAI và lưu vector 1536 chiều cùng tên mô hình và số chiều. Sự phân biệt này quan trọng để tránh gán kết quả nghiên cứu của một mô hình cho mô hình đang chạy trong sản phẩm.

Độ tương đồng cosine dựa trên góc giữa hai vector. Khi vector đã có sẵn, truy vấn tìm phản hồi gần nhất có thể xếp hạng các trường hợp theo khoảng cách cosine. pgvector cung cấp toán tử cosine và chế độ tìm chính xác mặc định [4]. Với giới hạn dữ liệu của khóa luận, hệ thống dùng tìm chính xác thay vì lập chỉ mục gần đúng. Điều này giúp kết quả truy vấn dễ giải thích và tránh thêm một tham số đánh đổi giữa tốc độ và độ đầy đủ của hàng xóm, dù ở quy mô lớn hơn chi phí tìm kiếm sẽ tăng.

### 2.4.2. Phân cụm theo mật độ

Tìm phản hồi tương tự từ một mục đã biết khác với phát hiện nhiều nhóm phản hồi tự hình thành. HDBSCAN là một thuật toán phân cụm theo mật độ, có thể tìm nhóm ở những mức mật độ khác nhau và để lại những điểm không thuộc nhóm rõ ràng [5]. Khi sử dụng, hệ thống biểu diễn phản hồi bằng embedding, tính nhãn cụm, rồi giữ nhãn nhiễu `-1` như phản hồi chưa được gán. Một cụm có thể hỗ trợ việc nhìn thấy vấn đề lặp lại; nó không tự xác nhận rằng mọi phản hồi trong cụm mô tả cùng một lỗi sản phẩm.

Chất lượng phân cụm phụ thuộc kích thước tập dữ liệu, cấu hình và bản thân embedding. Nếu chỉ có ít phản hồi hoặc nội dung rất đa dạng, thuật toán có thể coi tất cả là nhiễu. Đây là một kết quả cần báo cáo, không phải lỗi hiển thị. Bằng chứng nội bộ của đề tài có một lượt thử trên 25 phản hồi mà 25/25 đều bị coi là nhiễu. Do đó Chương 4 không hứa rằng chức năng phân cụm luôn sinh ra nhóm hữu ích; thay vào đó cần nêu điều kiện để nó phát huy tác dụng và các công cụ tìm kiếm, thống kê còn dùng được khi không có cụm.

### 2.4.3. Tín hiệu theo thời gian

Một nhóm phản hồi chỉ đáng chú ý khi đặt bên cạnh thời gian. Hệ thống tách mốc phản hồi xảy ra (`occurred_at`) khỏi mốc bản ghi được nhập; điều này tránh đánh đồng một tệp dữ liệu cũ được import hôm nay với vấn đề mới xuất hiện hôm nay. Khi có cụm, dịch vụ thống kê số phản hồi ở cửa sổ gần đây và cửa sổ trước đó để xác định mức tăng, dấu hiệu spike hoặc emerging. Ngưỡng được cấu hình trong ứng dụng và phải được báo cáo cùng kết quả, vì nhãn “tăng bất thường” chỉ là kết luận từ một quy tắc định trước, không phải phát hiện nguyên nhân.

## 2.5. AI Agent, công cụ phân tích và sự tham gia của con người

### 2.5.1. Agent sử dụng công cụ

Thay vì yêu cầu mô hình đọc tất cả phản hồi rồi viết một báo cáo một lần, hệ thống tách quá trình điều tra thành các bước. Agent nhận câu hỏi, xem ngữ cảnh sản phẩm, chọn công cụ, đọc kết quả, đánh giá bằng chứng rồi quyết định điều tra thêm hay tổng hợp. Kiểu kết hợp suy luận và hành động qua công cụ có liên hệ với công trình ReAct [6]. Triển khai của đề tài không sao chép thuật toán ReAct nguyên dạng: các công cụ là hàm phân tích nội bộ có tham số bị kiểm tra, trạng thái được giữ trong LangGraph và kết quả được quản lý theo chính sách của ứng dụng.

Công cụ được lựa chọn theo câu hỏi. `get_schema` và `profile_field` cho biết dữ liệu có trường gì và độ phủ; `aggregate_feedback` và `segment_feedback` tính số lượng theo nhóm; `compare_periods` so sánh hai cửa sổ thời gian; `semantic_search` tìm văn bản tương tự; `representative_feedback` chọn ví dụ; `inspect_cluster` xem cụm; `search_similar_cases` tìm tiền lệ từ nhận định trước. Agent không được tự viết SQL. Query compiler chỉ chấp nhận trường đã đăng ký trong schema sản phẩm, cộng các bộ lọc chuẩn như nguồn, mức nghiêm trọng và cảm xúc. Công cụ lỗi phải được coi là một quan sát về điều không thực hiện được, thay vì biến thành bằng chứng ủng hộ giả thuyết.

### 2.5.2. Bằng chứng, giả thuyết và giới hạn điều tra

Một nhận định có căn cứ phải phân biệt dữ liệu quan sát và cách giải thích. Ví dụ, số phản hồi nhắc đến thao tác đăng nhập tăng trong tuần là một `finding` nếu phép đếm được ghi lại và kiểm tra; “do phiên bản mới gây ra” là một `hypothesis` nếu chưa có kiểm tra nguyên nhân. Hệ thống lưu mã bằng chứng từ công cụ. Trước khi lưu nhận định, các mã do mô hình nhắc đến được đối chiếu với những mã thực tồn tại trong lượt điều tra. Cách làm này ngăn một loại lỗi cụ thể là trích dẫn mã không có thật; nó vẫn không chứng minh rằng cách diễn giải bằng chứng là đúng.

Vòng điều tra có giới hạn số lần lặp và ngân sách lần gọi mô hình. Khi hết giới hạn hoặc không có đủ bằng chứng, Agent phải chuyển sang tổng hợp kết quả với mức chắc chắn thích hợp. Phần giới hạn không chỉ nhằm tiết kiệm phí dịch vụ. Một Agent gọi công cụ vô hạn hoặc liên tục thay đổi hướng điều tra sẽ khó dự đoán thời gian trả lời và khó kiểm thử. Các giới hạn cũng giúp người dùng nhìn thấy rõ công việc hệ thống đã làm trước khi nhận báo cáo.

### 2.5.3. Checkpoint và Human-in-the-Loop

LangGraph cho phép một graph dừng tại `interrupt()` để chờ dữ liệu đầu vào từ người dùng, sau đó tiếp tục từ trạng thái đã lưu [7]. Trong ứng dụng, điểm dừng Gate 2 xuất hiện sau khi Agent tạo bản nháp nhận định. Người dùng có thể chấp nhận, chỉnh sửa, từ chối hoặc yêu cầu điều tra thêm. Checkpoint trên PostgreSQL cho phép không phụ thuộc hoàn toàn vào bộ nhớ tiến trình. Tuy nhiên, phục hồi sau lỗi cần kiểm tra cả các tác dụng phụ ở cơ sở dữ liệu; chỉ có checkpoint không mặc nhiên đảm bảo thao tác ghi không bị lặp. Thiết kế vì vậy phải quy định các điểm ghi idempotent và kiểm thử tình huống chạy lại.

LISTEN và ACT cũng có điểm duyệt nhưng không nhất thiết dùng cùng một graph. Gate 1 duyệt cách hiểu dữ liệu nguồn trước khi nhập. Gate 3 duyệt đề xuất hành động và chỉnh sửa các ước lượng. Ba điểm duyệt mang ý nghĩa nghiệp vụ khác nhau; gọi chung là “AI có người giám sát” mà không mô tả đối tượng và hệ quả của từng quyết định sẽ che mất sự khác biệt đó.

## 2.6. Bảo vệ dữ liệu và lựa chọn công nghệ

### 2.6.1. Ranh giới thông tin cá nhân

Presidio cung cấp thành phần nhận diện và thay thế thông tin định danh trong văn bản, cho phép kết hợp bộ nhận dạng có sẵn với recognizer tùy chỉnh [8]. Hệ thống của đề tài dùng Presidio cùng Stanza và một số biểu thức nhận diện theo ngữ cảnh Việt Nam. Dữ liệu phản hồi nguyên gốc được giữ ở phạm vi lưu trữ có kiểm soát; văn bản gửi đến mô hình, công cụ phân tích, trace và giao diện dùng phiên bản đã được che. Cần hiểu đây là biện pháp giảm rủi ro, không phải bảo đảm tuyệt đối: tài liệu Presidio cũng nêu rõ phát hiện tự động có thể bỏ sót thông tin nhạy cảm [8].

### 2.6.2. Kiến trúc web và cơ sở dữ liệu

Frontend Next.js trình bày quy trình nhập liệu, xem dữ liệu, điều tra và duyệt. Backend FastAPI giữ logic nghiệp vụ, bảo vệ API và gọi dịch vụ bên ngoài. Người dùng được xác thực bằng luồng mật khẩu và JWT; ứng dụng dùng cookie `httpOnly` và phân quyền theo vai trò. Các mô hình dữ liệu chính nằm trong PostgreSQL do Supabase quản lý. pgvector lưu embedding cạnh dữ liệu phản hồi để dùng cùng khóa ngoại và truy vấn của cơ sở dữ liệu [4]. Tác vụ phân tích chạy nền nhằm tránh giữ một request trình duyệt mở trong thời gian gọi mô hình.

Sự lựa chọn này xuất phát từ quy mô và điều kiện triển khai: máy phát triển 8 GB RAM, dữ liệu luận văn giới hạn ở mức nhỏ, dịch vụ cơ sở dữ liệu được quản lý và ngân sách gọi mô hình cần kiểm soát. Nó không hàm ý rằng kiến trúc hiện tại đã giải quyết các yêu cầu ở quy mô rất lớn. Khi số phản hồi hoặc người dùng tăng đáng kể, các thành phần chạy nền, lưu tệp gốc và tìm vector có thể cần thay đổi; đó là hướng phát triển sau khi có phép đo tải thực tế.

## 2.7. Đối chiếu cách giải quyết bài toán

Có thể xử lý một phần công việc bằng bảng tính: nhập CSV, lọc, đếm và thêm nhãn thủ công. Ưu điểm là đơn giản, dễ kiểm tra ở quy mô nhỏ; nhược điểm là người dùng phải tự liên kết dữ liệu, chuẩn hóa nhãn và giữ lịch sử quyết định. Một cách khác là yêu cầu LLM đọc một tập phản hồi rồi sinh bản tóm tắt. Cách này tạo văn bản nhanh nhưng khó ràng buộc nguồn bằng chứng, khó kiểm tra kết quả theo bộ lọc sản phẩm và có rủi ro gửi nguyên văn thông tin cá nhân. Hướng thứ ba là xây dựng quy trình ứng dụng: công cụ xác định tính số liệu, AI diễn giải, dữ liệu giữ dấu vết và con người quyết định. Đây là hướng được chọn trong đề tài.

**Bảng 2.1. Đối chiếu ba cách xử lý phản hồi theo yêu cầu đề tài**

| Tiêu chí | Bảng tính thủ công | LLM tóm tắt một lần | Ứng dụng đề tài |
|---|---|---|---|
| Nhiều kiểu cột đầu vào | Người dùng sửa tay | Cần tiền xử lý | Hồ sơ cột + Gate 1 |
| Tìm trường hợp tương tự | Lọc từ khóa | Phụ thuộc văn bản gửi vào | Tìm kiếm vector |
| Số liệu và bằng chứng | Tạo tay | Có thể thiếu dấu vết | Công cụ thống kê + mã bằng chứng |
| Kiểm soát quyết định | Người dùng hoàn toàn | Phụ thuộc prompt | Gate 1, 2, 3 và lịch sử |
| Bảo vệ PII | Quy trình người dùng | Dễ lộ nếu gửi thẳng | Che trước lời gọi mô hình |

Bảng 2.1 so sánh các phương thức xử lý ở mức khái niệm theo phạm vi chức năng, không phải phép đo hiệu năng hoặc độ chính xác giữa ba sản phẩm cụ thể. Đặc điểm của hệ thống đề tài sẽ được đối chiếu với mã nguồn và kết quả kiểm thử tại Chương 3 và Chương 4.

## 2.8. Khung đánh giá cho hệ thống phân tích phản hồi

### 2.8.1. Tách chất lượng phần mềm và chất lượng nhận định

Một hệ thống có thể vượt qua kiểm thử API mà vẫn tạo ra nhận định yếu. Ngược lại, một câu trả lời nghe hợp lý của mô hình không chứng minh được rằng các quyền truy cập, trạng thái duyệt hoặc dữ liệu lưu trữ là đúng. Vì vậy, đề tài chia đánh giá thành hai lớp. Lớp phần mềm xem xét hợp đồng dữ liệu, tính nhất quán của trạng thái, ranh giới thông tin cá nhân và khả năng vận hành. Lớp phân tích xem xét câu trả lời có dựa trên đúng tập phản hồi hay không, con số có đúng khi đối chiếu truy vấn hay không, và câu nào chỉ là giả thuyết cần kiểm chứng. Chương 4 tách minh chứng của hai lớp thay vì cộng chúng thành một tỷ lệ đạt chung.

Đối với phân loại, đơn vị đánh giá là một phản hồi đã được gán nhãn tham chiếu theo bộ quy tắc rõ ràng. Có thể xây dựng ma trận nhầm lẫn, precision, recall và F1 theo từng nhãn khi có đủ trường hợp dương và âm. Nếu một phản hồi có nhiều chủ đề, bài toán là đa nhãn; một nhãn đúng không tự động làm cả phản hồi đúng. Trường hợp tiếng Việt xen tiếng Anh cần được giữ trong mẫu kiểm tra, bởi cách viết sản phẩm và thuật ngữ kỹ thuật ảnh hưởng trực tiếp đến nhãn. Khi chưa có gold label được gán độc lập, đề tài chỉ kiểm tra được cấu trúc đầu ra và một số tình huống đơn lẻ, không công bố F1 như một số liệu thực nghiệm.

Đối với tìm kiếm tương tự, cần phân biệt độ tương đồng vector với tính cùng vấn đề. Hai câu có thể giống nhau về ngữ nghĩa nhưng khác sản phẩm, thời điểm hoặc điều kiện gây lỗi. Một phép đánh giá phù hợp sẽ chọn truy vấn, gắn nhãn mức liên quan cho các kết quả và tính precision@k hoặc recall@k. Cần cố định phiên bản mô hình embedding, dim vector và tập ứng viên trước khi so sánh. Một kết quả gần trong không gian vector là tín hiệu để người dùng điều tra, chưa đủ để kết luận có lỗi lặp lại. Tương tự, cụm HDBSCAN là cấu trúc thống kê phụ thuộc dữ liệu và tham số, không phải nhãn nghiệp vụ cuối cùng.

Đối với insight, một phiếu đánh giá nên tách ít nhất bốn tiêu chí: dữ kiện có thể truy nguồn, phép tính đúng, giả thuyết được đánh dấu rõ và giới hạn được nêu. Người đánh giá có thể mở ID evidence, chạy lại bộ lọc và kiểm tra mẫu phản hồi đã che thông tin cá nhân. Một insight thiếu ID nguồn hoặc đưa ra nguyên nhân chắc chắn từ quan sát tương quan phải bị đánh dấu cần sửa dù văn phong tốt. Cách đánh giá này phù hợp với vai trò hỗ trợ quyết định của ứng dụng và với quy tắc con người phải duyệt ở Gate 2 [2], [7].

### 2.8.2. Mẫu số và cửa sổ thời gian

Các chỉ số từ phản hồi dễ sai khi thiếu mẫu số. Chẳng hạn, 10 phản hồi cùng chủ đề trong một tuần có thể là tăng mạnh nếu tuần trước chỉ có 2, nhưng là giảm nếu tuần trước có 20. Khi so sánh hai khoảng thời gian, cần nêu thời điểm bắt đầu/kết thúc, cùng điều kiện lọc, số phản hồi hợp lệ ở mỗi khoảng và cách xử lý bản ghi không có `occurred_at`. Nếu hai khoảng có độ dài khác nhau, số đếm thô không so sánh trực tiếp. Với lượng dữ liệu nhỏ, vài bản ghi mới có thể tạo tỷ lệ phần trăm rất lớn; giao diện vì vậy nên hiển thị đồng thời số tuyệt đối và tỷ lệ, đồng thời cho phép mở danh sách nguồn.

Một vấn đề khác là độ trễ giữa thời điểm người dùng gửi phản hồi và thời điểm hệ thống nhập dữ liệu. Nếu dùng thời gian import để đo xu hướng, một đợt nạp dữ liệu cũ có thể trông như đột biến mới. Thiết kế ưu tiên `occurred_at` khi có và giữ riêng thời gian hệ thống tiếp nhận để kiểm tra quá trình xử lý. Bản ghi thiếu hoặc sai định dạng thời gian phải được báo là giới hạn của phân tích xu hướng. Không được âm thầm gán ngày hiện tại rồi diễn giải thành hành vi người dùng ngày hiện tại.

Các chỉ số sau hành động cũng cần định nghĩa cửa sổ và điều kiện. Một action được chấp nhận hôm nay không thể được đánh giá bằng phản hồi của các ngày trước đó. Nếu không có dữ liệu trước hành động, kết quả trước/sau là chưa xác định. Nếu không có nhóm đối chứng, biến động sau action chỉ là tương quan quan sát được. Những giới hạn này là lý do hệ thống lưu trạng thái action và thời điểm duyệt, không chỉ lưu một câu khuyến nghị. Việc trình bày KPI cùng điều kiện tính quan trọng hơn một con số đơn lẻ trông chính xác.

### 2.8.3. Khả năng tái lập

Một phép thử AI có thể thay đổi khi dữ liệu, prompt, mô hình hoặc provider thay đổi. Để tái lập, ít nhất phải giữ định danh run, phiên bản prompt, tên mô hình, cấu hình bộ lọc, số lượng đầu vào, trạng thái lời gọi và nguồn evidence. Với các phép đo chất lượng, bộ dữ liệu tham chiếu phải được đóng băng và không chứa thông tin cá nhân thật. Nên ghi thời gian kiểm thử và commit mã nguồn; một kết quả thuộc bản demo cũ không được dùng làm kết quả của bản hiện tại. Các log cuộc gọi mô hình trong đề tài phục vụ kiểm toán chi phí và lỗi, nhưng không thay thế một benchmark có nhãn.

Đối với kiểm thử đơn vị, mô hình được mock để kết quả có thể lặp lại và không phát sinh chi phí. Kiểm thử tích hợp kiểm tra kết nối và hành vi giữa các thành phần, vì vậy phụ thuộc môi trường cơ sở dữ liệu và tài nguyên ngôn ngữ. Kiểm thử xuyên suốt cần tập đầu vào, các quyết định tại ba Gate và dấu vết đầu ra. Ba lớp này trả lời ba câu hỏi khác nhau; không thể lấy số lượng unit test đã qua để suy ra chất lượng phân cụm, cũng không thể lấy một buổi demo thành công để suy ra độ ổn định triển khai.

## 2.9. Các đe dọa đối với tính hợp lệ của kết quả

Đe dọa thứ nhất đến từ dữ liệu khảo sát. Người tham gia được tuyển theo cách thuận tiện, cùng tự báo cáo kinh nghiệm xử lý phản hồi trong sáu tháng gần đây. Mẫu này cho thấy những nhu cầu có thật của nhóm người trả lời, nhưng không đại diện thống kê cho tất cả tổ chức sản phẩm AI. Các câu hỏi theo thang mức cho biết cảm nhận, không đo trực tiếp thời gian lao động hay chi phí thực tế. Bởi vậy, kết quả khảo sát được dùng để ưu tiên thiết kế và chọn ca sử dụng, không dùng để tuyên bố mức lợi ích định lượng của ứng dụng.

Đe dọa thứ hai đến từ dữ liệu phản hồi phục vụ demo. Dữ liệu giả lập hữu ích để kiểm tra luồng và điều kiện biên, nhưng có thể sạch hơn dữ liệu thực, có phân bố chủ đề khác và ít cách viết sai hơn. Một bộ phản hồi nhỏ, đa chủ đề, có thể khiến HDBSCAN gán toàn bộ điểm là nhiễu; đó là kết quả hợp lệ của thuật toán trong điều kiện đó, không chứng minh cơ chế phát hiện chủ đề hoạt động tốt hay kém ở mọi quy mô. Muốn đánh giá phát hiện cụm, cần thêm bộ dữ liệu lớn hơn, tập chủ đề có độ dày phù hợp và nhãn kiểm tra độc lập.

Đe dọa thứ ba là thay đổi trạng thái mã nguồn. Repo trải qua nhiều pha phát triển; báo cáo nền tảng ban đầu, handoff demo và working tree tại thời điểm viết không đồng nhất. Các con số được ghi ở pha trước là minh chứng lịch sử, cần gắn với phiên bản và cách chạy. Chương 4 chỉ coi một phép thử là kết quả hiện tại khi lệnh được chạy lại trên checkout đang báo cáo và đầu ra được giữ. Những việc phụ thuộc dịch vụ ngoài hoặc quyền đọc tài nguyên mà phiên làm việc không kiểm chứng được phải được ghi là chưa xác nhận.

Đe dọa cuối cùng là sự chủ quan của người duyệt. Gate 2 và Gate 3 làm tăng khả năng kiểm soát, nhưng quyết định của một người không tự động chính xác. Nếu muốn đo mức nhất quán, có thể cho hai người đánh giá độc lập cùng một tập insight/action, quy định tiêu chí trước và so mức đồng thuận. Trong phạm vi khóa luận hiện tại chưa có thiết kế thử nghiệm như vậy. Do đó, luận điểm có thể bảo vệ là hệ thống tạo điều kiện để người dùng xem, sửa và lưu quyết định có căn cứ; mức cải thiện quyết định của tổ chức cần nghiên cứu tiếp.

## 2.10. Phân tích các lựa chọn kỹ thuật dưới ràng buộc đề tài

### 2.10.1. Kết hợp mô hình xác suất với logic xác định

LLM có khả năng đọc một câu phản hồi linh hoạt, nhận ra chủ đề từ cách diễn đạt không cố định và diễn giải kết quả bằng ngôn ngữ tự nhiên. Nhưng nó không phải nơi phù hợp để đếm chính xác một tập lớn hoặc tự bảo đảm một phép tính luôn giống nhau. Vì vậy, kiến trúc của đề tài dùng LLM cho nhiệm vụ ngữ nghĩa như đề xuất mapping, phân loại, lập kế hoạch điều tra và viết insight; còn điều kiện lọc, đếm, xác thực miền giá trị, tính điểm ưu tiên và kiểm trạng thái do chương trình đảm nhận. Sự kết hợp này giảm số việc phải tin hoàn toàn vào đầu ra mô hình.

Ví dụ, khi hỏi “có bao nhiêu phản hồi nghiêm trọng về tính năng tạo ảnh trong tháng vừa qua”, planner có thể xác định cần lọc theo topic, severity và thời gian. Tuy nhiên, số lượng phải đến từ truy vấn trên database với phạm vi product xác định, không phải từ việc mô hình ước lượng sau khi đọc vài trích đoạn. Synthesizer có thể viết “có xu hướng tăng” chỉ khi số liệu hai cửa sổ và mẫu số được cung cấp. Nếu công cụ báo không có ngày hợp lệ, câu trả lời phải nêu giới hạn thay vì tự chọn một mốc thời gian thay thế. Đây là nguyên tắc “AI hỗ trợ diễn giải, dữ liệu xác định làm căn cứ” của bản thiết kế.

Đầu ra có cấu trúc không loại bỏ hoàn toàn lỗi ngữ nghĩa. JSON đúng schema vẫn có thể chứa một nhãn sai hoặc một recommendation không liên quan. Pydantic có thể bảo đảm `confidence` nằm trong 0–1 và `impact` trong 1–10, nhưng không biết tác động kinh doanh thực tế. Do đó, xác thực cấu trúc là tầng đầu, đối chiếu evidence là tầng sau, và quyết định người dùng là tầng cuối. Các tầng này có chức năng riêng; thêm một tầng không làm tầng khác trở nên thừa. Cách tổ chức này giải thích vì sao các Gate xuất hiện ở ba thời điểm khác nhau thay vì một nút duyệt duy nhất cuối quy trình.

### 2.10.2. Khi nào tìm kiếm vector và phân cụm có ích

Tìm kiếm vector hữu ích khi người dùng nhớ ý nghĩa của một sự cố nhưng không nhớ đúng từ khóa phản hồi. Hai câu “bot quên bối cảnh sau khi tải lại” và “mở cuộc trò chuyện cũ thì mất phần trước” có thể cùng chỉ một vấn đề dù từ vựng khác. Tuy nhiên, embedding thường làm mượt khác biệt ngữ nghĩa; một kết quả tương tự vẫn cần bộ lọc product, phiên bản, thời điểm và người đọc xác nhận. Kết quả trả về phải kèm nội dung đã che, điểm tương đồng, nguồn và khả năng mở phản hồi gốc trong hệ thống. Nếu chỉ hiển thị số điểm, người dùng không thể phân biệt sự giống nhau có ích với câu chung chung.

Phân cụm giải một câu hỏi khác: trong toàn bộ tập phản hồi, có nhóm nào tự hình thành mà chưa có taxonomy sẵn hay không. HDBSCAN phù hợp với mục tiêu không ép mọi điểm vào một nhóm và có thể gán nhiễu [5]. Đổi lại, nó đòi hỏi mật độ dữ liệu phù hợp. Bộ dữ liệu 25 phản hồi rất phân tán có thể không tạo được cụm khi ngưỡng tối thiểu từ 5 trở lên. Kết quả toàn nhiễu không phải lỗi code mặc định; nó có thể phản ánh rằng không có nhóm đủ dày theo tham số. Để đánh giá chất lượng, cần thử trên dữ liệu đủ lớn và kiểm tra nội dung từng cụm, tránh đặt mục tiêu “phải có cụm” rồi hạ tham số đến khi một hình vẽ xuất hiện.

Các tín hiệu xu hướng và chủ đề mới cũng cần phân biệt. Một topic đã biết tăng tần suất là một spike của chủ đề cũ. Một nhóm câu mới chưa khớp taxonomy là ứng viên emerging, nhưng có thể do thay đổi cách viết hoặc nguồn dữ liệu mới chứ không phải vấn đề sản phẩm mới. Nếu một đợt nhập gồm nhiều phản hồi từ cùng kênh, hệ thống nên cho người dùng xem nguồn và số mẫu trước khi diễn giải. Các cơ chế này cùng hỗ trợ phát hiện vấn đề, song không thể gộp thành một chỉ số duy nhất mà vẫn giữ nghĩa.

### 2.10.3. Vai trò của lưu trữ quan hệ và theo dõi phiên bản

PostgreSQL được chọn vì bài toán cần nhiều liên kết có ràng buộc: một phản hồi thuộc product và import; một evidence gắn với run; một insight được tạo từ evidence; một action bắt nguồn từ insight và có decision log. CSDL quan hệ giúp giữ khóa ngoại và transaction ở các điểm người dùng quyết định. JSONB được dùng cho thuộc tính linh hoạt của nguồn, nhưng các trường cốt lõi vẫn có tên và hợp đồng ổn định. pgvector bổ sung tìm kiếm ngữ nghĩa ngay cạnh bản ghi phản hồi [4], tránh sao chép dữ liệu sang một kho vector thứ hai trong quy mô nhỏ của khóa luận.

Lưu phiên bản quan trọng vì kết quả AI phụ thuộc ngữ cảnh. Một nhãn taxonomy có thể được hợp nhất sau khi phản hồi đã phân tích; một product schema có thể thay đổi sau lần import; một prompt được chỉnh để cải thiện khả năng trả JSON. Nếu chỉ lưu kết quả mới nhất mà không giữ phiên bản và ID run, không thể giải thích vì sao cùng một câu hỏi ở hai thời điểm có câu trả lời khác. Đề tài chưa giải quyết toàn bộ bài toán quản lý phiên bản dữ liệu của hệ thống lớn, nhưng các khóa run, schema, prompt và model tạo nền để đối chiếu. Đây cũng là điều kiện để báo cáo Chương 4 nói rõ phép đo thuộc phiên bản nào.
