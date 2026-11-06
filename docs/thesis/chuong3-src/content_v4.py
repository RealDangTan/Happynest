"""Build ch3_content_v3.json: resolve [[fig:id]] / [[tbl:id]] references and figure widths.

Usage: python -I content_v3.py <trimdir> <sizes.csv> <out.json> [maxh]
"""
import json
import os
import re
import sys

S = []


def p(x):
    S.append({"t": "p", "x": x})


def h2(x):
    S.append({"t": "h2", "x": x})


def h3(x):
    S.append({"t": "h3", "x": x})


def b(x, bold=None):
    it = {"t": "b", "x": x}
    if bold:
        it["bold"] = bold
    S.append(it)


def fig(fid, img, title, wpt=None):
    S.append({"t": "fig", "id": fid, "img": img, "wpt": wpt})
    S.append({"t": "capf", "x": title})


def tbl(tid, title, widths, rows):
    S.append({"t": "capt", "id": tid, "x": title})
    S.append({"t": "tbl", "w": widths, "rows": rows})


def eq(tpl):
    S.append({"t": "eq", "tpl": tpl})


def spec(tid, name, actor, desc, pre, main, alt, post):
    tbl(tid, "Đặc tả use case " + name[0].lower() + name[1:], [105, 320], [
        ["Tên use case", name],
        ["Tác nhân", actor],
        ["Mô tả", desc],
        ["Tiền điều kiện", pre],
        ["Luồng sự kiện chính", "\n".join(main)],
        ["Luồng thay thế", "\n".join(alt)],
        ["Hậu điều kiện", post],
    ])


# =============================================================================== intro
p("Chương 1 đã chỉ ra bốn khó khăn chính của người xử lý phản hồi: phản hồi nằm rải rác ở nhiều nguồn, phải đọc và gán loại thủ công, khó nhận ra chủ đề mới và thường phát hiện muộn những vấn đề lặp lại. Chương 2 đã chọn cách tiếp cận Lắng nghe – Thấu hiểu – Hành động, trong đó chương trình đảm nhận các phép đếm và kiểm tra có quy tắc, mô hình AI hỗ trợ đọc hiểu và diễn giải, còn người phụ trách đưa ra quyết định cuối cùng.")
p("Chương này trình bày cách các lựa chọn đó được hiện thực thành hệ thống HappyNest. Chương bắt đầu từ người dùng: ai sử dụng hệ thống và họ cần làm gì, thể hiện bằng các biểu đồ use case. Tiếp theo là quy trình nghiệp vụ và yêu cầu, phương pháp thực hiện, kiến trúc, thiết kế dữ liệu, thiết kế từng bước Lắng nghe, Thấu hiểu, Hành động và cuối cùng là giao diện. Với mỗi thành phần, khóa luận trả lời ba câu hỏi: thành phần đó giải quyết khó khăn nào, nó hoạt động ra sao và còn giới hạn gì. Các giá trị tham số được nêu theo cấu hình hiện tại của mã nguồn.")

# =============================================================================== 3.1 use case
h2("3.1. Phân tích use case")
p("Phân tích bắt đầu từ người dùng: ai sử dụng HappyNest và họ cần thực hiện những công việc gì. Mục này xác định tác nhân, trình bày biểu đồ use case tổng quát, rồi phân rã từng nhóm use case kèm bảng đặc tả cho use case chính của nhóm. Mỗi nhóm được gắn với các yêu cầu chức năng F01–F12 liệt kê ở Mục 3.2.2.")
p("Các biểu đồ trong chương được vẽ theo ký hiệu UML 2 bằng công cụ PlantUML, gồm biểu đồ use case, hoạt động, trình tự, lớp, trạng thái, gói, thành phần và triển khai. Trong biểu đồ use case, quan hệ «include» chỉ phần bắt buộc luôn diễn ra cùng use case gốc, còn quan hệ «extend» chỉ phần tùy chọn mà người dùng có thể thực hiện thêm; use case tô xanh nhạt là điểm kiểm duyệt. Trong biểu đồ hoạt động, hành động tô xanh nhạt là quyết định của người phụ trách, hành động tô xám là bước có gọi dịch vụ AI, còn hành động nền trắng do chương trình xử lý. Trong biểu đồ trình tự, các thông điệp được đánh số theo thứ tự; khung alt thể hiện rẽ nhánh, khung loop thể hiện vòng lặp, mũi tên nét đứt là thông điệp trả về.")
h3("3.1.1. Tác nhân của hệ thống")
p("Tác nhân trong biểu đồ use case là người sử dụng hệ thống để đạt một mục tiêu của mình. Với HappyNest, đó là người phụ trách phản hồi của một sản phẩm. Người phụ trách là vai trò đại diện cho những người dùng thực tế đã nêu ở Mục 1.5.1: quản lý sản phẩm, quản lý thành công khách hàng và nhân sự vận hành. Ba nhóm này đảm nhận những phần việc khác nhau, nhưng thiết kế không chia quyền theo vai trò: mỗi tài khoản toàn quyền với các sản phẩm do mình tạo và không thấy dữ liệu của tài khoản khác. Vì vậy, hệ thống chỉ có một tác nhân; các vai trò thực tế được thể hiện bằng quan hệ tổng quát hóa trong [[fig:uctn]].")
fig("uctn", "uc_tac_nhan.png", "Tác nhân Người phụ trách và các vai trò người dùng")
p("[[tbl:roles]] mô tả công việc chính của từng vai trò khi sử dụng HappyNest.")
tbl("roles", "Các vai trò người dùng mà tác nhân Người phụ trách đại diện", [130, 295], [
    ["Vai trò", "Công việc chính trên HappyNest"],
    ["Quản lý sản phẩm", "Đặt câu hỏi điều tra, duyệt nhận định, chọn và ưu tiên phương án cải tiến"],
    ["Quản lý thành công khách hàng", "Nhập phản hồi từ kênh hỗ trợ, theo dõi chủ đề và xu hướng, xem phương án dành cho nhóm hỗ trợ khách hàng"],
    ["Nhân sự vận hành", "Nhập và chuẩn hóa dữ liệu, quản lý bộ chủ đề, chạy phân loại và phân cụm"],
])
p("Dịch vụ AI (mô hình ngôn ngữ và mô hình tạo véc-tơ) và Google không phải là tác nhân. Chúng không sử dụng HappyNest để đạt mục tiêu nào, mà là các hệ thống bên ngoài được HappyNest gọi tới khi thực hiện use case của người phụ trách. Vì vậy, chúng không xuất hiện trong biểu đồ use case; vai trò của chúng được thể hiện trong biểu đồ hoạt động, biểu đồ trình tự và biểu đồ triển khai ở các mục sau.")
h3("3.1.2. Biểu đồ use case tổng quát")
p("[[fig:uc00]] là biểu đồ use case tổng quát. Mười hai use case được nhóm theo ba bước Lắng nghe, Thấu hiểu, Hành động, cùng nhóm tài khoản và báo cáo. Hai use case tô màu là hai điểm kiểm duyệt có trên giao diện ở bước Thấu hiểu và Hành động; điểm kiểm duyệt thứ nhất nằm trong use case nhập dữ liệu CSV.")
fig("uc00", "uc00_tong_quat.png", "Biểu đồ use case tổng quát của HappyNest")
p("Những use case tốn chi phí gọi AI, như nhập dữ liệu (đề xuất ý nghĩa cột), phân loại, phân cụm, điều tra và sinh phương án, đều do người phụ trách chủ động kích hoạt thay vì tự chạy ngầm. Lựa chọn này đáp ứng yêu cầu kiểm soát chi phí ở Mục 1.5.3. Các mục tiếp theo phân rã từng nhóm use case.")
h3("3.1.3. Nhóm tài khoản và sản phẩm")
p("Nhóm này bảo đảm mỗi người chỉ làm việc với dữ liệu của mình, đáp ứng yêu cầu F01, F02 và N02. Người dùng có thể đăng ký bằng thư điện tử hoặc đăng nhập bằng Google; sau khi đăng nhập, mọi thao tác đều gắn với sản phẩm đang chọn (xem [[fig:uc01]]).")
fig("uc01", "uc01_tai_khoan.png", "Biểu đồ use case nhóm tài khoản và sản phẩm")
p("[[tbl:spec_login]] đặc tả use case đăng nhập. Thông báo lỗi khi sai thông tin được viết chung để không tiết lộ một thư điện tử có tồn tại trong hệ thống hay không. Quá trình đăng ký được thể hiện ở [[fig:a11]]: tài khoản mới luôn bắt đầu với không gian làm việc trống.")
spec("spec_login", "Đăng nhập", "Người phụ trách",
     "Người phụ trách xác thực để làm việc với các sản phẩm của mình.",
     "Đã có tài khoản bằng thư điện tử hoặc tài khoản Google.",
     ["1. Người phụ trách nhập thư điện tử và mật khẩu.",
      "2. Hệ thống tìm tài khoản và so khớp mật khẩu đã băm bằng Argon2.",
      "3. Hệ thống tạo phiên đăng nhập có hạn 12 giờ, lưu trong cookie mà mã trên trang không đọc được.",
      "4. Giao diện mở màn hình làm việc."],
     ["1a. Chọn đăng nhập bằng Google: hệ thống chuyển sang Google, xác minh id_token rồi tìm hoặc tạo tài khoản.",
      "2a. Sai thông tin: hệ thống báo lỗi chung.",
      "2b. Tài khoản chỉ đăng ký bằng Google: hệ thống đề nghị đăng nhập bằng Google."],
     "Phiên đăng nhập hợp lệ; các yêu cầu sau chỉ truy cập dữ liệu của tài khoản.")
fig("a11", "a11_dang_ky.png", "Biểu đồ hoạt động đăng ký tài khoản")
h3("3.1.4. Nhóm nhập dữ liệu")
p("Nhóm nhập dữ liệu giải quyết khó khăn đầu tiên ở Chương 1: phản hồi nằm rải rác ở nhiều nguồn với cấu trúc khác nhau (yêu cầu F03, F04). Trong [[fig:uc02]], việc tải tệp luôn kèm lập hồ sơ cột, còn việc xác nhận ý nghĩa các cột luôn dẫn tới nhập phản hồi vào kho. Đổi cách xử lý một cột là phần mở rộng của bước xác nhận.")
fig("uc02", "uc02_nhap_du_lieu.png", "Biểu đồ use case nhóm nhập dữ liệu")
p("[[tbl:spec_import]] đặc tả use case chính của nhóm. Luồng thay thế cho thấy hệ thống không bao giờ nhập dữ liệu khi chưa có quyết định hợp lệ của người phụ trách, và lỗi ở một dòng không làm hỏng cả tệp.")
spec("spec_import", "Nhập tệp CSV và xác nhận ý nghĩa cột", "Người phụ trách",
     "Đưa phản hồi từ một tệp CSV vào kho phản hồi của sản phẩm sau khi người phụ trách xác nhận ý nghĩa các cột.",
     "Đã đăng nhập, đã chọn sản phẩm; sản phẩm không có lượt nhập đang dở.",
     ["1. Người phụ trách tải tệp CSV.",
      "2. Hệ thống lưu tệp gốc, lập hồ sơ cột và hiển thị dữ liệu mẫu đã che.",
      "3. Người phụ trách yêu cầu AI đề xuất.",
      "4. Hệ thống gọi dịch vụ AI để đề xuất cách xử lý từng cột.",
      "5. Người phụ trách đồng ý hoặc đổi cách xử lý (điểm kiểm duyệt thứ nhất).",
      "6. Hệ thống kiểm tra quyết định, ghi nhật ký, nhập nền từng dòng sau khi che thông tin.",
      "7. Hệ thống hiển thị báo cáo nhập."],
     ["1a. Sản phẩm có lượt nhập dở: hệ thống từ chối.",
      "4a. Gọi dịch vụ AI lỗi: lượt nhập trở về trạng thái đã lập hồ sơ để yêu cầu lại.",
      "6a. Quyết định không hợp lệ: hệ thống báo lỗi để người phụ trách sửa.",
      "6b. Dòng thiếu nội dung hoặc sai ngày: ghi vào báo cáo lỗi, các dòng khác vẫn được nhập.",
      "Người phụ trách có thể hủy lượt nhập trước khi xác nhận."],
     "Phản hồi đã che thông tin nằm trong kho; quyết định ánh xạ được lưu trong nhật ký quyết định.")
h3("3.1.5. Nhóm quản lý bộ chủ đề")
p("Nhóm này đáp ứng nhu cầu nhận ra chủ đề mới (yêu cầu F11) và nguyên tắc ở Mục 2.4.1.1: bộ chủ đề do AI gợi ý nhưng phải được con người xem xét. Trong [[fig:uc03]], áp dụng chủ đề là quyết định của người phụ trách và được tô màu; sửa đề xuất là phần mở rộng trước khi áp dụng. Người phụ trách cũng có thể tự thêm, sửa hoặc xóa chủ đề.")
fig("uc03", "uc03_bo_chu_de.png", "Biểu đồ use case nhóm quản lý bộ chủ đề")
p("[[tbl:spec_tax]] đặc tả use case sinh và áp dụng bộ chủ đề. Đề xuất của AI chỉ tồn tại tạm thời trên giao diện; không có gì được ghi vào hệ thống cho đến khi người phụ trách bấm áp dụng.")
spec("spec_tax", "Sinh và áp dụng bộ chủ đề", "Người phụ trách",
     "Tạo hoặc mở rộng bộ chủ đề của sản phẩm bằng gợi ý của AI, có người duyệt.",
     "Sản phẩm đã có phản hồi trong kho.",
     ["1. Người phụ trách yêu cầu sinh bộ chủ đề.",
      "2. Hệ thống chọn mẫu phản hồi đã che, rải đều theo thời gian.",
      "3. Hệ thống gọi dịch vụ AI để đề xuất cây chủ đề.",
      "4. Hệ thống loại đề xuất trùng hoặc không hợp lệ, hiển thị đề xuất.",
      "5. Người phụ trách sửa và chọn áp dụng.",
      "6. Hệ thống lưu chủ đề, tăng phiên bản bộ chủ đề và ghi nhật ký."],
     ["1a. Sản phẩm đã có bộ chủ đề: hệ thống đọc nhóm chưa phân loại và gợi ý tối đa 8 chủ đề mới.",
      "5a. Người phụ trách bỏ đề xuất: không có dữ liệu nào được ghi.",
      "5b. Người phụ trách tự thêm, sửa hoặc xóa chủ đề."],
     "Bộ chủ đề mới có hiệu lực cho các lượt phân loại sau.")
h3("3.1.6. Nhóm kho phản hồi và phân loại")
p("Nhóm này giảm gánh nặng đọc và gán loại thủ công (yêu cầu F05, F06). [[fig:uc04]] cho thấy chạy phân loại luôn kèm xem phiếu ước tính chi phí, còn hủy lượt là phần mở rộng. Tìm phản hồi tương tự được mở từ màn hình chi tiết của một phản hồi.")
fig("uc04", "uc04_kho_phan_hoi.png", "Biểu đồ use case nhóm kho phản hồi và phân loại")
p("[[tbl:spec_classify]] đặc tả use case chạy phân loại. Phiếu ước tính và bước xác nhận số phản hồi là cách hiện thực yêu cầu kiểm soát chi phí N03.")
spec("spec_classify", "Chạy phân loại phản hồi", "Người phụ trách",
     "Gán chủ đề, thuộc tính phụ và véc-tơ cho các phản hồi chưa được phân loại.",
     "Sản phẩm có bộ chủ đề đang hiệu lực và có phản hồi chưa phân loại.",
     ["1. Người phụ trách chọn phạm vi phản hồi.",
      "2. Hệ thống lập phiếu ước tính số phản hồi và số lượt gọi tối đa.",
      "3. Người phụ trách xác nhận số phản hồi.",
      "4. Hệ thống tạo lượt phân loại (tối đa 100 phản hồi) và chạy nền.",
      "5. Với mỗi phản hồi, hệ thống gọi dịch vụ AI để gán chủ đề, thuộc tính phụ và tạo véc-tơ.",
      "6. Hệ thống lưu kết quả; giao diện hiển thị tiến độ đến khi lượt kết thúc."],
     ["3a. Dữ liệu đã thay đổi so với phiếu: hệ thống yêu cầu xem lại.",
      "5a. Không có chủ đề đạt 0,60: phản hồi vào nhóm chưa phân loại.",
      "5b. Lỗi gọi dịch vụ: phản hồi trở về trạng thái chờ.",
      "6a. Người phụ trách hủy lượt; 6b. Quá nửa số phản hồi lỗi: lượt thất bại."],
     "Phản hồi có chủ đề, thuộc tính và véc-tơ, lưu kèm phiên bản bộ chủ đề đã dùng.")
h3("3.1.7. Nhóm phân cụm và theo dõi biến động")
p("Nhóm này phục vụ việc phát hiện sớm vấn đề lặp lại (yêu cầu F06), khó khăn mà 36/36 người tham gia khảo sát từng gặp. Trong [[fig:uc05]], chạy phân cụm luôn bao gồm đặt tên cụm và tính chỉ số biến động; xem phản hồi mẫu và lọc cụm đang tăng là các phần mở rộng của việc xem danh sách cụm.")
fig("uc05", "uc05_phan_cum.png", "Biểu đồ use case nhóm phân cụm và theo dõi biến động")
p("[[tbl:spec_cluster]] đặc tả use case chạy phân cụm. Phân cụm chạy riêng cho từng sản phẩm nên tên cụm chỉ được tạo từ phản hồi của chính sản phẩm đó.")
spec("spec_cluster", "Chạy phân cụm", "Người phụ trách",
     "Gom các phản hồi gần nghĩa của một sản phẩm thành cụm và tính mức biến động của từng cụm.",
     "Phản hồi của sản phẩm đã có véc-tơ.",
     ["1. Người phụ trách chọn “Tạo lại phân cụm”.",
      "2. Hệ thống đọc véc-tơ của sản phẩm và chạy HDBSCAN.",
      "3. Với mỗi cụm, hệ thống gọi dịch vụ AI để đặt tên và tóm tắt từ tối đa 5 phản hồi mẫu.",
      "4. Hệ thống tính chỉ số biến động và điểm gợi ý điều tra.",
      "5. Hệ thống ghi cụm mới, trả số cụm và số phản hồi ngoài cụm.",
      "6. Người phụ trách xem danh sách cụm."],
     ["2a. Không hình thành cụm nào: hệ thống báo không có cụm.",
      "3a. Gọi dịch vụ AI lỗi: cụm được đặt tên đánh số."],
     "Các cụm của sản phẩm được thay mới; cụm cũ không còn phản hồi bị xóa.")
h3("3.1.8. Nhóm điều tra và duyệt nhận định")
p("Nhóm này đáp ứng yêu cầu F07 và F08: đi từ “điều gì đang xảy ra” đến “vì sao”, có người kiểm tra căn cứ. Trong [[fig:uc06]], duyệt nhận định luôn bao gồm xem bằng chứng, thể hiện nguyên tắc ở Mục 2.4.3.2 rằng kiểm duyệt không chỉ là bấm nút. Sửa, từ chối và yêu cầu điều tra thêm là các phần mở rộng của bước duyệt.")
fig("uc06", "uc06_dieu_tra.png", "Biểu đồ use case nhóm điều tra và duyệt nhận định")
p("[[tbl:spec_inv]] đặc tả use case điều tra và duyệt nhận định. Lượt điều tra có thể lặp lại nhiều vòng khi người phụ trách yêu cầu điều tra thêm.")
spec("spec_inv", "Điều tra và duyệt nhận định", "Người phụ trách",
     "Tác tử AI tra cứu dữ liệu để trả lời một câu hỏi, tạo nhận định kèm bằng chứng cho người phụ trách duyệt.",
     "Sản phẩm có phản hồi đã phân loại.",
     ["1. Người phụ trách nhập câu hỏi hoặc chọn câu hỏi gợi ý.",
      "2. Hệ thống che thông tin trong câu hỏi, tạo lượt điều tra và chạy nền.",
      "3. Tác tử tra cứu bằng công cụ, lưu bằng chứng và đánh giá cho đến khi đủ hoặc chạm giới hạn.",
      "4. Tác tử tổng hợp nhận định; lượt điều tra tạm dừng.",
      "5. Người phụ trách xem nhận định, bằng chứng và chọn duyệt (điểm kiểm duyệt thứ hai).",
      "6. Hệ thống ghi quyết định và kết thúc lượt."],
     ["3a. Không có bằng chứng khả dụng: hệ thống tạo nhận định “không đủ bằng chứng”.",
      "5a. Sửa nhận định trước khi duyệt; 5b. Từ chối nhận định.",
      "5c. Yêu cầu điều tra thêm: tác tử tiếp tục tra cứu với ý kiến của người duyệt."],
     "Nhận định ở trạng thái đã duyệt, đã sửa hoặc đã từ chối; quyết định được ghi cùng người duyệt.")
h3("3.1.9. Nhóm xây dựng và chọn phương án")
p("Nhóm này đáp ứng yêu cầu F09: biến nhận định đã duyệt thành phương án có căn cứ. Trong [[fig:uc07]], chọn phương án là điểm kiểm duyệt thứ ba, với phần mở rộng là sửa điểm và nội dung. Người phụ trách còn có thể tự thêm phương án, xem phương án theo nhóm nghiệp vụ và chạy phép quan sát trước – sau.")
fig("uc07", "uc07_hanh_dong.png", "Biểu đồ use case nhóm xây dựng và chọn phương án")
p("[[tbl:spec_act]] đặc tả use case sinh và chọn phương án. Giá trị do AI ước lượng và giá trị người phụ trách sửa được lưu song song để có thể so sánh về sau.")
spec("spec_act", "Sinh và chọn phương án", "Người phụ trách",
     "Đề xuất các phương án cải tiến từ một nhận định đã duyệt để người phụ trách so sánh và lựa chọn.",
     "Nhận định đã được duyệt hoặc đã sửa.",
     ["1. Người phụ trách chọn “Gợi ý hành động”.",
      "2. Hệ thống nạp bằng chứng của nhận định và thư viện thực hành.",
      "3. Hệ thống gọi dịch vụ AI để đánh giá tám nhóm nghiệp vụ và soạn phương án.",
      "4. Hệ thống kiểm tra căn cứ, tính điểm ưu tiên và hiển thị ma trận.",
      "5. Người phụ trách xem căn cứ, sửa điểm hoặc nội dung, chấp nhận hoặc từ chối (điểm kiểm duyệt thứ ba).",
      "6. Hệ thống tính lại điểm và ghi nhật ký quyết định."],
     ["1a. Nhận định chưa duyệt: hệ thống từ chối.",
      "4a. Căn cứ không hợp lệ: hệ thống báo lỗi, giữ nguyên phương án cũ.",
      "5a. Người phụ trách tự thêm phương án."],
     "Phương án ở trạng thái đã chấp nhận hoặc đã từ chối; giá trị của AI và của người được lưu song song.")
h3("3.1.10. Nhóm báo cáo và theo dõi")
p("Nhóm cuối phục vụ mục tiêu theo dõi ở Mục 1.3.2 (yêu cầu F10, F12). [[fig:uc08]] gồm xem báo cáo tổng hợp theo kỳ, xem và chỉnh sửa các nhận định đã lưu, xem chỉ số thời gian và kiểm duyệt, theo dõi các tác vụ đang chạy nền và kiểm tra tình trạng hệ thống. Các use case này chỉ đọc dữ liệu đã có, không gọi dịch vụ AI.")
fig("uc08", "uc08_bao_cao.png", "Biểu đồ use case nhóm báo cáo và theo dõi")

# =============================================================================== 3.2
h2("3.2. Quy trình nghiệp vụ và yêu cầu")
h3("3.2.1. Quy trình nghiệp vụ và ba điểm kiểm duyệt")
p("Mục 2.5.3 đã mô tả cách làm thủ công: người phụ trách gom phản hồi từ các nguồn, đọc và phân nhóm, tìm nội dung lặp lại, kiểm tra căn cứ rồi soạn phương án cải tiến. HappyNest giữ nguyên trình tự công việc này. Những việc lặp lại như chuẩn hóa dữ liệu, gán chủ đề, đếm và tra cứu được chuyển cho hệ thống; những chỗ cần hiểu bối cảnh nghiệp vụ vẫn do người phụ trách quyết định. Các use case ở Mục 3.1 được sắp theo trình tự công việc thành hai biểu đồ hoạt động có làn: người phụ trách, hệ thống HappyNest và dịch vụ AI. Dịch vụ AI được vẽ thành một làn riêng để thấy rõ bước nào có gọi mô hình; nó là hệ thống bên ngoài, không phải tác nhân.")
p("[[fig:a01a]] mô tả giai đoạn Lắng nghe. Phản hồi đi từ tệp CSV qua điểm kiểm duyệt thứ nhất, được che thông tin, nhập vào kho, rồi được phân loại và phân cụm theo bộ chủ đề do người phụ trách áp dụng.")
fig("a01a", "a01a_quy_trinh_lang_nghe.png", "Biểu đồ hoạt động nghiệp vụ giai đoạn Lắng nghe")
p("[[fig:a01b]] mô tả hai giai đoạn còn lại. Người phụ trách đặt câu hỏi, tác tử tra cứu và tổng hợp nhận định; nhận định có thể được yêu cầu điều tra thêm nhiều lần trước khi được duyệt. Chỉ nhận định đã duyệt mới được dùng để soạn phương án, và quy trình kết thúc ở việc chọn phương án.")
fig("a01b", "a01b_quy_trinh_hieu_hanh_dong.png", "Biểu đồ hoạt động nghiệp vụ giai đoạn Thấu hiểu và Hành động")
p("Ba điểm kiểm duyệt được đặt ở những chỗ mà sai sót của AI sẽ lan sang các bước sau:")
b("Điểm kiểm duyệt thứ nhất: xác nhận ý nghĩa các cột dữ liệu. Nếu cột ngày tháng hoặc cột nội dung bị hiểu sai, mọi phép đếm và so sánh về sau đều sai theo. Vì vậy, dữ liệu chỉ được nhập vào kho sau khi người phụ trách đồng ý.", "Điểm kiểm duyệt thứ nhất")
b("Điểm kiểm duyệt thứ hai: duyệt nhận định. Tác tử AI có thể kết luận vượt quá bằng chứng. Người phụ trách đối chiếu nhận định với bằng chứng trước khi nhận định được dùng làm căn cứ cho phương án.", "Điểm kiểm duyệt thứ hai")
b("Điểm kiểm duyệt thứ ba: chọn phương án. Điểm số và đề xuất do hệ thống tạo ra không biết hết nguồn lực, rủi ro và ưu tiên của tổ chức. Người phụ trách sửa, chấp nhận hoặc từ chối từng phương án.", "Điểm kiểm duyệt thứ ba")
p("Ngoài ba điểm trên, mọi thay đổi bộ chủ đề do AI gợi ý chỉ có hiệu lực khi người phụ trách áp dụng. Quy trình dừng ở việc lựa chọn phương án; việc triển khai thay đổi lên sản phẩm diễn ra bên ngoài hệ thống, đúng phạm vi đã giới hạn ở Mục 1.5.4. Các bước không bắt buộc chạy liền một mạch: người phụ trách có thể nhập thêm dữ liệu, sửa bộ chủ đề hoặc đặt nhiều câu hỏi điều tra cho cùng một sản phẩm.")
h3("3.2.2. Yêu cầu chức năng")
p("Mỗi yêu cầu chức năng ứng với một hoặc vài use case ở Mục 3.1 và phải trả lời được câu hỏi “vì sao hệ thống cần chức năng này”. [[tbl:F]] liệt kê các yêu cầu cùng lý do, lấy từ kết quả khảo sát ở Mục 1.2.1 hoặc mục tiêu ở Mục 1.3.2. Cảm xúc và mức độ nghiêm trọng không được tách thành yêu cầu riêng vì 33/36 người chỉ chấm mức 2 cho tính hữu ích của chúng; hệ thống giữ chúng như thuộc tính phụ trong kết quả phân loại để lọc và sắp xếp. Các mã F01–F12 được dùng lại trong ma trận kiểm chứng ở Phụ lục A.")
tbl("F", "Yêu cầu chức năng và lý do cần có", [40, 170, 215], [
    ["Mã", "Chức năng", "Vì sao cần"],
    ["F01", "Đăng ký, đăng nhập, đăng xuất", "Mỗi người dùng chỉ được thấy dữ liệu của mình (Mục 1.5.3)"],
    ["F02", "Tạo và quản lý sản phẩm", "Mỗi sản phẩm có dữ liệu và bộ chủ đề riêng, không trộn lẫn khi phân tích"],
    ["F03", "Tải tệp CSV, xem hồ sơ cột và dữ liệu mẫu", "24/36 người gặp khó khăn vì phản hồi phân tán ở nhiều nguồn"],
    ["F04", "Xác nhận ý nghĩa các cột (điểm kiểm duyệt thứ nhất)", "Mỗi nguồn đặt tên cột khác nhau; hiểu sai một cột làm sai mọi thống kê về sau"],
    ["F05", "Phân loại phản hồi theo bộ chủ đề", "21/36 người chấm mức 4 cho gánh nặng đọc và gán loại thủ công"],
    ["F06", "Tìm phản hồi tương tự, xem các cụm", "27/36 người đánh giá việc gom phản hồi tương tự là hữu ích"],
    ["F07", "Đặt câu hỏi cho tác tử AI, xem bằng chứng", "36/36 người từng phát hiện muộn vấn đề lặp lại; cần biết vấn đề nằm ở đâu và vì sao"],
    ["F08", "Duyệt nhận định hoặc yêu cầu điều tra thêm (điểm kiểm duyệt thứ hai)", "Kết luận của AI có thể vượt quá bằng chứng (Mục 2.4.3.2)"],
    ["F09", "Sinh, sửa và chọn phương án (điểm kiểm duyệt thứ ba)", "Chuyển nhận định thành việc cần làm, nhưng quyết định ưu tiên vẫn thuộc con người (Mục 1.2.1)"],
    ["F10", "Xem báo cáo tổng hợp", "Theo dõi chủ đề và xu hướng theo kỳ (Mục 1.3.2)"],
    ["F11", "Quản lý bộ chủ đề theo từng sản phẩm", "25/36 người gặp khó khăn khi nhận ra chủ đề mới"],
    ["F12", "Kiểm tra tình trạng và ghi nhận hoạt động của hệ thống", "Cần số liệu về thời gian và chi phí để đánh giá hệ thống (Mục 1.3.2)"],
])
h3("3.2.3. Yêu cầu phi chức năng")
p("Yêu cầu phi chức năng tập trung vào những rủi ro riêng của một hệ thống có dùng AI: lộ thông tin cá nhân, trộn dữ liệu giữa các tài khoản, chi phí gọi mô hình tăng ngoài kiểm soát và tác tử AI chạy vòng lặp không dừng. [[tbl:N]] nêu từng yêu cầu và cách thiết kế đáp ứng. Các yêu cầu này không bảo đảm độ chính xác của phân loại hay chất lượng của nhận định; hai nội dung đó cần được đánh giá riêng theo tiêu chí ở Mục 2.4.5.")
tbl("N", "Yêu cầu phi chức năng", [40, 115, 270], [
    ["Mã", "Yêu cầu", "Cách thiết kế đáp ứng"],
    ["N01", "Bảo vệ thông tin định danh", "Chỉ văn bản đã che thông tin mới được gửi tới dịch vụ AI, ghi vào nhật ký hoặc trả qua API; nội dung gốc chỉ nằm trong vùng lưu trữ nội bộ"],
    ["N02", "Đúng phạm vi dữ liệu và truy vết được", "Mọi truy vấn nghiệp vụ lọc theo sản phẩm của tài khoản; nhận định chỉ được dẫn bằng chứng của chính lượt điều tra đó"],
    ["N03", "Kiểm soát chi phí", "Thao tác tốn phí do người dùng kích hoạt; trước khi phân loại, người dùng xem ước tính số lượt gọi và xác nhận"],
    ["N04", "Giới hạn tài nguyên", "Mỗi lượt phân loại tối đa 100 phản hồi; tác tử tối đa 8 vòng và 18 lời gọi mô hình; mỗi lần tra cứu trả tối đa 30 phản hồi"],
    ["N05", "Theo dõi tiến độ và chịu lỗi", "Tác vụ dài chạy nền và báo tiến độ; lỗi ở một phản hồi không làm dừng cả lượt; trạng thái điều tra được lưu để tiếp tục"],
])

# =============================================================================== 3.3 method
h2("3.3. Phương pháp và quy trình thực hiện")
p("Sau khi đã xác định người dùng cần gì và hệ thống phải đáp ứng những yêu cầu nào, mục này trình bày cách đề tài được thực hiện: phương pháp nghiên cứu, quy trình làm việc và các thử nghiệm kỹ thuật dùng để chốt thiết kế.")
h3("3.3.1. Phương pháp nghiên cứu")
p("Đề tài xây dựng một phần mềm để giải quyết một vấn đề thực tế, nên khóa luận đi theo hướng nghiên cứu khoa học thiết kế (design science research). Theo Hevner và cộng sự, hướng nghiên cứu này tạo ra một sản phẩm nhân tạo nhằm giải quyết vấn đề, sau đó đánh giá sản phẩm đó trong bối cảnh sử dụng [38]. Peffers và cộng sự chia quá trình thành sáu hoạt động: xác định vấn đề, đặt mục tiêu cho giải pháp, thiết kế và phát triển, trình diễn, đánh giá và truyền đạt kết quả [39].")
p("Các hoạt động này tương ứng với bố cục của khóa luận. Vấn đề được xác định qua bối cảnh và khảo sát 36 người ở Chương 1. Mục tiêu của giải pháp được nêu ở Mục 1.3 và được làm rõ bằng cơ sở lý thuyết ở Chương 2. Chương 3 trình bày hoạt động thiết kế và phát triển. Việc trình diễn và đánh giá hệ thống thuộc Chương 4. Nhờ cách tổ chức này, mỗi quyết định thiết kế đều có điểm xuất phát rõ ràng: một khó khăn đã được ghi nhận hoặc một nguyên tắc đã được lựa chọn ở các chương trước.")
h3("3.3.2. Quy trình thực hiện và công cụ")
p("Hệ thống được xây dựng theo từng giai đoạn nhỏ. Mỗi giai đoạn có tiêu chí nghiệm thu riêng và kết thúc bằng kiểm thử tự động: pytest cho phần máy chủ và Vitest cho phần giao diện. Mọi thay đổi so với kế hoạch được ghi vào nhật ký quyết định của dự án, kèm lý do và các phương án đã loại. Nhờ đó, khi một lựa chọn thay đổi giữa chừng, người đọc vẫn biết vì sao nó thay đổi.")
p("Với những thành phần có rủi ro kỹ thuật cao, đề tài viết thử nghiệm ngắn trước khi đưa vào thiết kế chính thức. [[tbl:spike]] tóm tắt các thử nghiệm đó và quyết định rút ra. Đây là phép kiểm tra tính khả thi trên dữ liệu nhỏ hoặc giả lập, chưa phải số đo chất lượng của hệ thống hoàn chỉnh.")
tbl("spike", "Các thử nghiệm kỹ thuật trước khi chốt thiết kế", [150, 135, 140], [
    ["Điều cần kiểm tra", "Kết quả", "Quyết định thiết kế"],
    ["Che thông tin định danh trên 20 câu giả lập Việt–Anh bằng Presidio và Stanza", "Thư điện tử, số điện thoại, CCCD, đường dẫn, địa chỉ IP: phát hiện đủ 100%; tên người: 66,7%", "Thêm bộ nhận dạng riêng cho các mẫu của Việt Nam; ghi nhận giới hạn với tên người"],
    ["Mô hình trả kết quả đúng mẫu JSON (10 lượt gọi)", "10/10 lượt đúng mẫu", "Dùng lược đồ JSON làm cách gọi chính, có đường dự phòng"],
    ["Lưu và tìm véc-tơ ngay trong PostgreSQL (10 câu)", "Mỗi câu đều tìm lại đúng chính nó ở vị trí đầu tiên", "Lưu véc-tơ trong cơ sở dữ liệu nghiệp vụ, không cần kho véc-tơ riêng"],
    ["Phân cụm HDBSCAN trên 200 véc-tơ giả lập", "Tìm đúng 3 cụm; 7,5–8,5% điểm không thuộc cụm nào", "Chọn HDBSCAN cho bước phân cụm"],
    ["Tạm dừng và tiếp tục lượt điều tra sau khi tắt tiến trình", "Tiếp tục đúng chỗ dừng; thao tác ghi dữ liệu chỉ thực hiện một lần", "Dùng cơ chế lưu trạng thái cho điểm kiểm duyệt thứ hai"],
    ["Phân loại bằng dịch vụ System One trên 16 câu tự tạo có chủ ý mơ hồ", "16/16 kết quả hợp lệ; 95% lượt gọi xong trong khoảng 1,06 giây; chưa đạt ngưỡng chất lượng đặt trước", "Vẫn chọn vì nhanh và chỉ trả nhãn trong danh sách cho phép; cần đánh giá lại trên tập gán nhãn độc lập"],
])

# =============================================================================== 3.4 architecture
h2("3.4. Kiến trúc hệ thống")
h3("3.4.1. Kiến trúc tổng thể")
p("HappyNest gồm ba tầng: giao diện web, máy chủ ứng dụng và cơ sở dữ liệu (xem [[fig:arch]]). Người dùng chỉ làm việc với giao diện; giao diện chuyển các yêu cầu dữ liệu sang máy chủ. Máy chủ là nơi duy nhất gọi dịch vụ AI bên ngoài, và chỉ gửi đi văn bản đã che thông tin định danh.")
p("Máy chủ được viết thành một ứng dụng duy nhất, chia mô-đun theo ba bước Lắng nghe, Thấu hiểu, Hành động, thay vì tách thành nhiều dịch vụ nhỏ. Lý do nằm ở các ràng buộc của đề tài: máy phát triển chỉ có 8 GB RAM, không dùng Docker và dữ liệu thử nghiệm dưới 1.500 phản hồi. Ở quy mô này, tách thành nhiều dịch vụ chỉ làm tăng công sức vận hành mà không đem lại lợi ích rõ ràng. Cái giá phải chấp nhận là các tác vụ dài chạy nền ngay trong tiến trình máy chủ: nếu máy chủ dừng giữa chừng, tác vụ đang chạy không tự chạy tiếp. Khi khởi động lại, hệ thống đánh dấu các lượt bị treo là thất bại để giao diện không chờ vô hạn và người dùng có thể chạy lại.")
fig("arch", "fig33_arch.png", "Kiến trúc ba tầng của HappyNest", 370)
p("[[tbl:tech]] nêu các công nghệ chính và lý do lựa chọn.")
tbl("tech", "Công nghệ sử dụng và lý do lựa chọn", [105, 135, 185], [
    ["Thành phần", "Công nghệ", "Lý do lựa chọn"],
    ["Giao diện", "Next.js, React, shadcn/ui", "Tổ chức màn hình theo đường dẫn; có sẵn thư viện thành phần giao diện"],
    ["Máy chủ ứng dụng", "Python, FastAPI", "Kiểm tra dữ liệu vào và ra theo lược đồ; hệ sinh thái xử lý ngôn ngữ phong phú"],
    ["Cơ sở dữ liệu", "PostgreSQL (Supabase) với pgvector [19]", "Một hệ quản trị lưu cả dữ liệu nghiệp vụ lẫn véc-tơ"],
    ["Tác tử AI", "LangGraph [23]", "Mô tả lượt điều tra thành các bước; tạm dừng và tiếp tục được khi chờ người duyệt"],
    ["Che thông tin định danh", "Presidio [25], Stanza", "Nhận diện tên người tiếng Việt và các mẫu số điện thoại, CCCD của Việt Nam"],
    ["Phân cụm", "HDBSCAN [20]", "Không cần biết trước số cụm; cho phép để lại phản hồi không thuộc cụm nào"],
    ["Đăng nhập", "Argon2 [40], JWT [41]", "Băm mật khẩu an toàn; phiên đăng nhập có thời hạn"],
])
h3("3.4.2. Biểu đồ thành phần")
p("[[fig:k01]] thể hiện các thành phần chính bên trong máy chủ và quan hệ phụ thuộc giữa chúng. Ba thành phần nghiệp vụ Lắng nghe, Thấu hiểu và Hành động nhận yêu cầu từ giao diện qua API REST, cùng đọc và ghi cơ sở dữ liệu. Cả ba đều đi qua một thành phần dùng chung để xác thực, che thông tin định danh và gọi mô hình. Nhờ đặt các việc này ở một chỗ, quy tắc “chỉ gửi văn bản đã che” và giới hạn chi phí được áp dụng thống nhất, không phụ thuộc vào từng chức năng.")
fig("k01", "k01_thanh_phan.png", "Biểu đồ thành phần của HappyNest")
h3("3.4.3. Biểu đồ gói")
p("Mã nguồn phía máy chủ được chia thành các gói theo trách nhiệm (xem [[fig:p01]]). Gói điểm cuối API chỉ nhận yêu cầu, kiểm tra quyền và chuyển việc cho các gói bên dưới. Nghiệp vụ nằm trong gói dịch vụ, tác vụ phân loại nền và luồng điều tra; luồng điều tra dùng gói công cụ tra cứu để đọc dữ liệu. Tất cả dùng chung gói lớp dữ liệu, còn gói cấu hình chứa thiết lập, bảo mật và quan sát. Phụ thuộc chỉ đi từ trên xuống, nên có thể thay một gói bên dưới mà không phải sửa điểm cuối API.")
fig("p01", "p01_goi_may_chu.png", "Biểu đồ gói phía máy chủ")
p("Phía giao diện được tổ chức tương tự (xem [[fig:p02]]). Các màn hình nghiệp vụ dùng thành phần giao diện và các hàm truy vấn dữ liệu; mọi lời gọi API đi qua một thư viện chung, rồi được cấu hình Next.js chuyển tiếp tới máy chủ. Nhờ đi chung một nguồn gốc, cookie phiên đăng nhập hoạt động mà không cần mở quyền truy cập chéo giữa các tên miền.")
fig("p02", "p02_goi_giao_dien.png", "Biểu đồ gói phía giao diện")
h3("3.4.4. Sử dụng mô hình AI theo từng tác vụ")
p("Mục 2.4.1.2 đã tách nguyên lý phân loại khỏi việc chọn một mô hình cụ thể. Trong hệ thống, mỗi tác vụ AI được gán mô hình qua một biến cấu hình, nên có thể đổi mô hình mà không sửa mã nguồn. Nguyên tắc phân công dựa trên tính chất công việc. Tác vụ mở, như đề xuất bộ chủ đề hay soạn phương án, cần mô hình đa dụng. Tác vụ đóng và lặp lại cho từng phản hồi, như gán chủ đề, dùng dịch vụ System One: dịch vụ này hỏi mô hình bằng các câu hỏi có kiểu dữ liệu xác định nên chỉ trả về nhãn trong danh sách cho phép [15], [16], [17]. [[tbl:models]] ghi cấu hình hiện tại; đây là lựa chọn cấu hình, không phải kết luận về chất lượng của từng mô hình.")
tbl("models", "Mô hình được dùng cho từng tác vụ", [175, 105, 145], [
    ["Tác vụ", "Tính chất", "Mô hình cấu hình"],
    ["Đề xuất ý nghĩa cột, bộ chủ đề, tên cụm và phương án", "Tác vụ mở, trả kết quả theo mẫu", "openai/gpt-4o-mini"],
    ["Phân loại từng phản hồi", "Tập nhãn đóng, lặp lại nhiều lần", "typesafe/jev-router (System One)"],
    ["Lập kế hoạch, đánh giá và tổng hợp trong lượt điều tra", "Nhiều bước, có giới hạn", "qwen/qwen3-30b-a3b-instruct-2507"],
    ["Tạo véc-tơ cho phản hồi", "1536 chiều", "text-embedding-3-small"],
])
p("Hệ thống vẫn giữ cách phân loại bằng mô hình ngôn ngữ thông thường làm phương án thay thế qua cấu hình; cách này chưa đối chiếu lại từng nhãn với danh sách cho phép ở phía máy chủ, nên chỉ dùng khi dịch vụ System One không sẵn sàng.")
p("Mọi lời gọi mô hình ngôn ngữ đi qua một lớp dùng chung, có luồng xử lý như [[fig:a02]]. Lớp này yêu cầu mô hình trả kết quả theo lược đồ JSON [18]; nếu dịch vụ lỗi hoặc quá 90 giây, nó chuyển sang yêu cầu JSON trong nội dung. Kết quả được kiểm tra theo lược đồ và được thử lại một lần kèm thông báo lỗi nếu sai mẫu; nếu vẫn sai, lỗi được báo lên thay vì để dữ liệu sai đi tiếp. Mỗi lời gọi được ghi vào nhật ký gồm loại tác vụ, mô hình, thời gian xử lý và lượng văn bản, nhưng không lưu nội dung. Nhật ký này vừa dùng để đếm số lời gọi khi giới hạn chi phí của tác tử, vừa cung cấp số liệu chi phí cho phần đánh giá. Ngoài ra, hệ thống có thể gửi dấu vết từng lượt chạy sang công cụ Langfuse để theo dõi chi tiết.")
fig("a02", "a02_goi_mo_hinh.png", "Biểu đồ hoạt động của lớp gọi mô hình")
h3("3.4.5. Biểu đồ triển khai")
p("[[fig:d01]] là môi trường phát triển và chạy thử của đề tài. Giao diện Next.js và máy chủ FastAPI chạy trực tiếp trên máy Windows 8 GB RAM, không dùng Docker; tệp CSV gốc được lưu trong thư mục nội bộ. Cơ sở dữ liệu PostgreSQL có pgvector đặt trên Supabase. Máy chủ gọi ra ngoài tới dịch vụ mô hình ngôn ngữ qua OpenRouter, dịch vụ tạo véc-tơ và Langfuse.")
fig("d01", "d01_trien_khai_dev.png", "Biểu đồ triển khai môi trường phát triển")
p("[[fig:d02]] là phương án triển khai cho người dùng thật. Giao diện đặt trên Vercel và chuyển tiếp các yêu cầu API tới máy chủ qua biến cấu hình địa chỉ máy chủ. Máy chủ Ubuntu chạy FastAPI dưới systemd, phía trước là Caddy để cấp HTTPS. Phương án này mới ở mức thiết kế, chưa phải kết quả vận hành.")
fig("d02", "d02_trien_khai_du_kien.png", "Biểu đồ triển khai dự kiến")

# =============================================================================== 3.5 data
h2("3.5. Thiết kế dữ liệu")
h3("3.5.1. Mô hình dữ liệu khái niệm và chuỗi truy vết")
p("Mục 2.4.3.2 đặt ra yêu cầu truy vết: phải đi được từ một kết luận trở về những phản hồi làm căn cứ cho nó. Mô hình dữ liệu của HappyNest được thiết kế quanh yêu cầu này (xem [[fig:concept]]). Mỗi sản phẩm thuộc một tài khoản và là ranh giới dữ liệu: lượt nhập, phản hồi, bộ chủ đề, cụm, lượt điều tra và phương án đều gắn với một sản phẩm cụ thể.")
fig("concept", "fig34_data.png", "Mô hình dữ liệu khái niệm của HappyNest", 400)
p("Chuỗi truy vết đi như sau. Mỗi lần tác tử chạy một công cụ tra cứu, kết quả được lưu thành một bằng chứng. Mỗi nhận định giữ danh sách mã của các bằng chứng mà nó dựa vào. Mỗi phương án giữ bản sao các căn cứ tại thời điểm được tạo. Mọi quyết định của con người ở ba điểm kiểm duyệt được ghi vào nhật ký quyết định, lưu song song giá trị do AI đề xuất và giá trị người phụ trách chọn, nhờ đó có thể đối chiếu con người đã sửa những gì so với đề xuất ban đầu.")
p("Bảng phản hồi được thiết kế để đáp ứng hai nhu cầu đã nêu ở Chương 2. Thứ nhất, mỗi sản phẩm có những trường thông tin khác nhau, ví dụ phiên bản ứng dụng hay loại thiết bị. Các trường này được lưu ở dạng linh hoạt (kiểu JSONB của PostgreSQL), nên thêm trường mới không phải sửa cấu trúc bảng; kết quả do AI tạo được lưu ở một vùng riêng, tách khỏi dữ liệu gốc. Thứ hai, phép so sánh theo thời gian phải phân biệt ngày phát sinh phản hồi với ngày nhập vào hệ thống (Mục 2.4.2.3), nên hai ngày này được lưu thành hai trường riêng.")
h3("3.5.2. Biểu đồ lớp")
p("Ở mức thiết kế, dữ liệu nghiệp vụ gồm 15 lớp, mỗi lớp tương ứng một bảng trong cơ sở dữ liệu và được tạo bằng các tệp chuyển đổi cấu trúc (migration) trong mã nguồn. Tên lớp và tên thuộc tính giữ đúng như trong mã nguồn để tiện đối chiếu; nghĩa tiếng Việt của mỗi lớp được ghi ở dòng khuôn mẫu phía trên tên lớp. [[fig:c01]] là biểu đồ lớp tổng quan, chỉ gồm tên lớp và quan hệ. Quan hệ hợp thành (hình thoi đặc) cho biết đối tượng con không tồn tại độc lập với đối tượng cha, ví dụ phản hồi thuộc về một sản phẩm.")
fig("c01", "c01_lop_tong_quan.png", "Biểu đồ lớp tổng quan")
p("[[fig:c02]] chi tiết nhóm lớp tài khoản, sản phẩm và dữ liệu phản hồi. Lớp Feedback giữ đồng thời nội dung gốc (raw_content) và văn bản đã che (feedback_text); chỉ trường sau được dùng cho phân tích và trả ra API. Các trường data, source_meta và ai_analysis lần lượt chứa chiều phân tích đã được duyệt, thông tin chỉ có nghĩa trong nguồn và kết quả do AI tạo. Lớp Taxonomy có quan hệ với chính nó để biểu diễn cây chủ đề.")
fig("c02", "c02_lop_du_lieu.png", "Biểu đồ lớp nhóm tài khoản, sản phẩm và dữ liệu phản hồi")
p("[[fig:c03]] chi tiết nhóm lớp phân tích và bằng chứng. Lớp AnalysisRun dùng chung cho lượt phân loại và lượt điều tra, phân biệt bằng trường mode. Mỗi lượt sinh ra nhiều bằng chứng (Evidence) và có thể tạo nhận định (Insight). Nhận định chỉ tham chiếu mã bằng chứng thay vì sao chép nội dung, nên việc kiểm tra mã có thuộc đúng lượt hay không do máy chủ thực hiện. Lớp LlmCallLog ghi mọi lời gọi mô hình và là căn cứ đếm ngân sách của tác tử.")
fig("c03", "c03_lop_phan_tich.png", "Biểu đồ lớp nhóm phân tích và bằng chứng")
p("[[fig:c04]] chi tiết nhóm lớp quyết định và theo dõi. Lớp Action lưu song song ước lượng của AI (impact, urgency, effort) và giá trị người phụ trách sửa (các trường human_*), cùng điểm ưu tiên đã tính. Lớp InsightReview ghi từng lần duyệt nhận định, còn DecisionLog là nhật ký chung cho mọi quyết định ở ba điểm kiểm duyệt. ImpactCheck lưu kết quả quan sát trước – sau của một phương án.")
fig("c04", "c04_lop_quyet_dinh.png", "Biểu đồ lớp nhóm quyết định và theo dõi")
p("Các thuộc tính chỉ nhận một tập giá trị cố định được khai báo thành kiểu liệt kê (xem [[fig:c05]]). Việc cố định tập giá trị giúp cơ sở dữ liệu từ chối giá trị lạ, chẳng hạn chỉ có bốn quyết định hợp lệ ở điểm kiểm duyệt thứ hai và tám nhóm nghiệp vụ cho phương án.")
fig("c05", "c05_liet_ke.png", "Các kiểu liệt kê chính")
h3("3.5.3. Biểu đồ trạng thái")
p("Bốn đối tượng có vòng đời quan trọng là lượt nhập, lượt xử lý, nhận định và phương án. Biểu đồ trạng thái giúp kiểm tra rằng mỗi điểm kiểm duyệt là một chuyển trạng thái bắt buộc, không thể bị bỏ qua.")
p("[[fig:st01]] là vòng đời của một lượt nhập. Lượt nhập chỉ chuyển sang trạng thái đang nhập khi qua điểm kiểm duyệt thứ nhất. Nếu AI lỗi khi đề xuất, lượt nhập quay lại trạng thái đã lập hồ sơ để người phụ trách yêu cầu lại; người phụ trách có thể hủy lượt nhập ở các trạng thái chưa nhập.")
fig("st01", "st01_luot_nhap.png", "Biểu đồ trạng thái lượt nhập")
p("[[fig:st02]] là vòng đời của một lượt xử lý, dùng chung cho phân loại và điều tra. Với lượt điều tra, trạng thái đang chạy có hai trạng thái con: đang xử lý và chờ duyệt nhận định; yêu cầu điều tra thêm đưa lượt về lại trạng thái đang xử lý. Lượt bị đánh dấu thất bại khi quá nửa số mục lỗi, khi luồng điều tra gặp lỗi, hoặc khi bị treo quá 30 phút lúc máy chủ khởi động lại.")
fig("st02", "st02_luot_xu_ly.png", "Biểu đồ trạng thái lượt xử lý")
p("[[fig:st03]] là vòng đời của một nhận định. Nhận định được tạo ở trạng thái chờ duyệt và chỉ rời trạng thái này bằng quyết định của người phụ trách. Chỉ nhận định đã duyệt hoặc đã sửa mới được dùng để sinh phương án; khi người phụ trách yêu cầu điều tra thêm, lượt điều tra sẽ tạo một nhận định mới.")
fig("st03", "st03_nhan_dinh.png", "Biểu đồ trạng thái nhận định")
p("[[fig:st04]] là vòng đời của một phương án. Phương án do AI sinh bắt đầu ở trạng thái đề xuất; phương án do người phụ trách tự thêm bắt đầu ở trạng thái đã chấp nhận. Khi sinh lại, chỉ các phương án còn ở trạng thái đề xuất bị thay thế, nên quyết định đã có của người phụ trách luôn được giữ nguyên.")
fig("st04", "st04_phuong_an.png", "Biểu đồ trạng thái phương án")
h3("3.5.4. Bảo vệ thông tin và phân tách dữ liệu")
p("Mục 2.4.4.2 xem việc che thông tin định danh là điều kiện xuyên suốt, không phải chức năng phụ. HappyNest thực hiện điều này bằng một bước che thông tin đặt ở mọi cửa vào của văn bản: dữ liệu mẫu khi xem trước tệp, từng dòng khi nhập, phản hồi nhập tay hoặc sửa tay, câu hỏi gửi cho tác tử và nội dung người duyệt sửa ở điểm kiểm duyệt thứ hai, thứ ba. Luồng xử lý của bước này được thể hiện ở [[fig:a03]].")
fig("a03", "a03_che_thong_tin.png", "Biểu đồ hoạt động che thông tin định danh")
p("Bước che thông tin dùng Presidio kết hợp Stanza để nhận diện tên người trong câu tiếng Việt và tiếng Anh, cùng các mẫu riêng cho thư điện tử, số điện thoại Việt Nam và số CCCD 12 chữ số. Phần bị phát hiện được thay bằng nhãn như <EMAIL>, <PHONE_NUMBER> hoặc <PERSON>; hệ thống chỉ lưu loại và vị trí của thông tin bị che, và không API nào trả về nội dung gốc. Trong quá trình chạy thử, bộ nhận diện từng nhầm từ “AI” là tên người, làm mất đúng từ khóa quan trọng của đề tài, nên hệ thống có một danh sách ngắn các từ viết tắt kỹ thuật được giữ nguyên. Nếu Stanza không khởi tạo được, hệ thống chỉ dùng biểu thức chính quy và mất khả năng nhận diện tên người. Như Mục 2.4.4.2 đã lưu ý và [[tbl:spike]] cho thấy, che thông tin không đồng nghĩa với ẩn danh hoàn toàn.")
p("Về phân tách dữ liệu, mỗi sản phẩm thuộc đúng một tài khoản. Mọi yêu cầu đều kiểm tra quyền sở hữu; khi sản phẩm không tồn tại hoặc thuộc tài khoản khác, hệ thống trả cùng một thông báo “không tìm thấy” để không tiết lộ dữ liệu của người khác. Người duyệt luôn được xác định từ phiên đăng nhập, không lấy từ dữ liệu do trình duyệt gửi lên. Hiện còn một ngoại lệ: chỉ số tổng hợp về thời gian xử lý và kết quả kiểm duyệt đang được tính trên toàn hệ thống, chưa tách theo tài khoản.")
p("Phiên đăng nhập là nền tảng của việc phân tách dữ liệu. [[fig:s01]] là trình tự đăng nhập bằng thư điện tử: mật khẩu được so khớp với bản băm Argon2 [40], sau đó máy chủ tạo JWT [41] có hạn 12 giờ và đặt vào cookie mà mã JavaScript trên trang không đọc được.")
fig("s01", "s01_dang_nhap.png", "Biểu đồ trình tự đăng nhập bằng thư điện tử")
p("[[fig:s02]] là trình tự đăng nhập bằng Google. Máy chủ gửi kèm một mã chống giả mạo khi chuyển người dùng sang Google, kiểm tra lại mã này khi Google gọi về, rồi xác minh chữ ký của id_token trước khi tìm hoặc tạo tài khoản. Sau bước này, phiên đăng nhập được tạo giống như cách đăng nhập bằng mật khẩu.")
fig("s02", "s02_dang_nhap_google.png", "Biểu đồ trình tự đăng nhập bằng Google")

# =============================================================================== 3.6 LISTEN
h2("3.6. Thiết kế bước Lắng nghe")
p("Bước Lắng nghe giải quyết hai khó khăn đầu tiên ở Chương 1: phản hồi phân tán và gánh nặng đọc, gán loại thủ công. Đầu ra của bước này là một kho phản hồi thống nhất, đã che thông tin, đã gắn chủ đề và có thể tìm theo ý nghĩa. Người phụ trách quyết định ở hai chỗ: ý nghĩa các cột dữ liệu và nội dung bộ chủ đề.")
h3("3.6.1. Nhập dữ liệu và xác nhận ý nghĩa các cột")
p("Mỗi nguồn phản hồi xuất dữ liệu với tên cột riêng: nguồn này gọi là “nội dung”, nguồn khác gọi là “comment”; ngày tháng có thể nằm ở cột “created_at” hay “ngày gửi”. Muốn phân tích chung, hệ thống phải biết mỗi cột có ý nghĩa gì. [[fig:a04a]] mô tả phần đầu của việc nhập: hệ thống tự lập hồ sơ từng cột bằng chương trình (kiểu dữ liệu, tỷ lệ ô trống, số giá trị khác nhau và vài giá trị mẫu đã che), không gọi AI. Mô hình ngôn ngữ chỉ được gọi khi người phụ trách yêu cầu, và chỉ đọc hồ sơ cột chứ không đọc toàn bộ tệp.")
fig("a04a", "a04a_tai_csv.png", "Biểu đồ hoạt động tải tệp và đề xuất ý nghĩa cột")
p("Với mỗi cột, mô hình đề xuất một trong năm cách xử lý:")
b("Ghép vào trường có sẵn: dùng cho các cột như nội dung phản hồi hoặc ngày phản hồi.", "Ghép vào trường có sẵn")
b("Tạo trường phân tích mới: dùng cho thông tin vẫn có nghĩa khi phản hồi đến từ nguồn khác, như phiên bản ứng dụng hay thiết bị.", "Tạo trường phân tích mới")
b("Lưu làm thông tin nguồn: dùng cho thông tin chỉ có nghĩa trong nguồn hiện tại, như trạng thái của phiếu hỗ trợ.", "Lưu làm thông tin nguồn")
b("Bỏ qua: dùng cho cột không có giá trị phân tích, như số thứ tự dòng.", "Bỏ qua")
b("Chưa rõ: dùng khi mô hình không chắc chắn, ví dụ cột “score” có thể là điểm hài lòng hoặc điểm sẵn lòng giới thiệu. Người phụ trách bắt buộc phải tự quyết định.", "Chưa rõ")
p("[[fig:a04b]] mô tả phần sau, bắt đầu từ điểm kiểm duyệt thứ nhất. Máy chủ kiểm tra lại các quyết định: mọi cột đều đã được xử lý, hai cột không cùng ghép vào một trường và phải có cột nội dung phản hồi. Sau đó việc nhập chạy nền: từng dòng được che thông tin rồi mới ghi vào kho. Dòng thiếu nội dung hoặc sai định dạng ngày được ghi vào báo cáo nhập, các dòng khác vẫn tiếp tục. Dòng không có ngày phát sinh sẽ lấy ngày nhập, nên với nguồn thiếu cột ngày, các phép so sánh theo thời gian ở Mục 3.6.4 cần được đọc thận trọng.")
fig("a04b", "a04b_xac_nhan_nhap.png", "Biểu đồ hoạt động xác nhận cột và nhập dữ liệu")
p("Về tương tác giữa các thành phần, [[fig:s03]] cho thấy việc tải tệp trả kết quả ngay vì chỉ gồm các phép tính bằng chương trình, còn việc đề xuất ý nghĩa cột được nhận ngay rồi chạy nền; giao diện hỏi trạng thái định kỳ cho đến khi có đề xuất. Mỗi sản phẩm chỉ được có một lượt nhập đang dở để tránh các đề xuất chồng chéo trên cùng lược đồ dữ liệu.")
fig("s03", "s03_tai_csv.png", "Biểu đồ trình tự tải tệp và đề xuất ý nghĩa cột")
p("[[fig:s04]] là trình tự xác nhận và nhập dữ liệu. Nếu quyết định có trường phân tích mới, một phiên bản lược đồ dữ liệu mới của sản phẩm được kích hoạt; quyết định cũng được ghi vào nhật ký để có thể xem lại về sau.")
fig("s04", "s04_xac_nhan_nhap.png", "Biểu đồ trình tự xác nhận cột và nhập dữ liệu")
h3("3.6.2. Xây dựng và cập nhật bộ chủ đề")
p("Khảo sát cho thấy 25/36 người gặp khó khăn khi nhận ra chủ đề mới, còn Mục 2.4.1.1 yêu cầu bộ chủ đề phải phù hợp với từng sản phẩm và được con người xem xét trước khi áp dụng. HappyNest đáp ứng cả hai bằng cách để AI gợi ý, còn người phụ trách quyết định. Nghiên cứu về dùng mô hình ngôn ngữ để mã hóa chủ đề cũng lưu ý các rủi ro về sai lệch, thiên lệch và quyền riêng tư khi áp dụng cách làm này [12].")
p("[[fig:a05]] cho thấy hai đường sinh đề xuất. Khi sản phẩm chưa có bộ chủ đề, mẫu phản hồi được chọn rải đều theo thời gian để một đợt sự cố gần đây không chiếm hết mẫu. Khi đã có bộ chủ đề, mô hình đọc nhóm “chưa phân loại” và gợi ý tối đa 8 chủ đề mới. Cả hai loại gợi ý đều chưa được ghi cho đến khi người phụ trách sửa và bấm áp dụng; mỗi lần áp dụng làm tăng số phiên bản của bộ chủ đề.")
fig("a05", "a05_bo_chu_de.png", "Biểu đồ hoạt động sinh và áp dụng bộ chủ đề")
p("[[fig:s05]] là trình tự tương ứng. Mỗi chủ đề có tên tiếng Anh chuẩn để mô hình dùng thống nhất, tên tiếng Việt để hiển thị và một mã định danh không đổi. Vì mã không đổi khi đổi tên, các kết quả phân loại cũ vẫn trỏ đúng chủ đề. Cách tách tên gọi khỏi khái niệm này tham khảo nguyên tắc của SKOS [14] và giúp mô hình xử lý ổn định các phản hồi pha trộn Việt–Anh.")
fig("s05", "s05_bo_chu_de.png", "Biểu đồ trình tự sinh và áp dụng bộ chủ đề")
h3("3.6.3. Phân loại phản hồi và tìm phản hồi tương tự")
p("Với 21/36 người chấm mức 4 cho gánh nặng đọc và gán loại thủ công, phân loại tự động là chức năng giảm việc trực tiếp nhất. [[fig:a06a]] là phần chuẩn bị: người phụ trách xem phiếu ước tính gồm số phản hồi sẽ xử lý và số lượt gọi tối đa. Số phản hồi xác nhận phải khớp với phiếu; nếu dữ liệu đã thay đổi trong lúc chờ, hệ thống yêu cầu xem lại.")
fig("a06a", "a06a_phieu_chi_phi.png", "Biểu đồ hoạt động lập phiếu ước tính và tạo lượt phân loại")
p("[[fig:a06b]] là phần xử lý từng phản hồi. Mỗi phản hồi được gán tối đa ba chủ đề kèm mức độ phù hợp, cùng các thuộc tính phụ: sắc thái, cảm xúc, ý định, mức độ nghiêm trọng, cờ an toàn và độ tin cậy. Chủ đề có mức phù hợp dưới 0,60 bị loại; nếu không còn chủ đề nào, phản hồi được đưa vào nhóm “chưa phân loại” thay vì bị ép vào chủ đề gần nhất, đúng nguyên tắc ở Mục 2.4.1.2. Lỗi ở một phản hồi chỉ đưa phản hồi đó về trạng thái chờ, không làm hỏng cả lượt.")
fig("a06b", "a06b_xu_ly_phan_hoi.png", "Biểu đồ hoạt động xử lý từng phản hồi")
p("[[fig:s06]] là trình tự của cả lượt phân loại. Mỗi lượt xử lý tối đa 100 phản hồi và gọi dịch vụ AI song song tối đa 3 luồng, trong khi chỉ một luồng ghi cơ sở dữ liệu. Kết quả được lưu kèm phiên bản bộ chủ đề đã dùng để có thể kiểm tra lại.")
fig("s06", "s06_phan_loai.png", "Biểu đồ trình tự chạy phân loại")
p("Bên cạnh chủ đề, mỗi phản hồi được chuyển thành một véc-tơ 1536 chiều, lưu kèm tên mô hình để tránh so sánh giữa các mô hình khác nhau. [[fig:s07]] là trình tự tìm phản hồi tương tự: máy chủ tìm các phản hồi gần nhất theo độ tương đồng cô-sin của pgvector [19], trong phạm vi sản phẩm của tài khoản. Đây là cách đáp ứng nhu cầu gom phản hồi tương tự mà 27/36 người đánh giá là hữu ích. Theo Mục 2.4.2.2, kết quả chỉ gợi ý những phản hồi nên đọc cùng nhau, không kết luận chúng có cùng nguyên nhân.")
fig("s07", "s07_tim_tuong_tu.png", "Biểu đồ trình tự tìm phản hồi tương tự")
h3("3.6.4. Phân cụm và phát hiện biến động")
p("Việc 36/36 người từng phát hiện muộn vấn đề lặp lại cho thấy cần một cơ chế tự làm nổi bật các nhóm phản hồi đang tăng. Phân loại theo bộ chủ đề chưa đủ, vì một vấn đề mới có thể chưa có tên trong bộ chủ đề. Vì vậy, hệ thống bổ sung phân cụm: gom các phản hồi có véc-tơ gần nhau mà không cần biết trước tên nhóm (Mục 2.4.2.3).")
p("[[fig:a07]] mô tả luồng phân cụm. Phân cụm chạy riêng cho từng sản phẩm khi người phụ trách yêu cầu, dùng HDBSCAN [20] với khoảng cách cô-sin; phản hồi không đủ gần với nhóm nào được để ngoài, không bị ép vào cụm. Kích thước cụm tối thiểu là tham số cấu hình, mặc định là 10; với tập dữ liệu thử nghiệm khoảng 120 phản hồi, giá trị này được hạ xuống 4 để các cụm có thể hình thành. Mô hình ngôn ngữ chỉ đặt tên và tóm tắt mỗi cụm từ tối đa 5 phản hồi mẫu đã che thông tin. Tên cụm chỉ là gợi ý, không tự trở thành chủ đề chính thức.")
fig("a07", "a07_phan_cum.png", "Biểu đồ hoạt động phân cụm và tính biến động")
p("Để biết cụm nào đang tăng, hệ thống so sánh hai khoảng 30 ngày liên tiếp. Gọi C là số phản hồi của cụm trong 30 ngày gần nhất và T là số phản hồi trong 30 ngày liền trước, tỷ lệ tăng trưởng G được tính theo Công thức (3.1):")
eq("G")
p("Cụm được đánh dấu tăng đột biến khi kỳ trước có phản hồi, kỳ này có ít nhất 5 phản hồi và G ≥ 2, tức số phản hồi tăng ít nhất gấp đôi. Cụm được đánh dấu mới xuất hiện khi kỳ trước không có phản hồi nào nhưng kỳ này có ít nhất 3. Khi T = 0, phép chia không xác định nên G được gán giá trị quy ước 9,99 nếu C > 0. Để gợi ý cụm nên điều tra trước, hệ thống tính thêm một điểm từ 0 đến 1, kết hợp ba yếu tố: quy mô cụm (chiếm 50%), cụm có đang tăng đột biến hoặc mới xuất hiện hay không (30%) và tỷ lệ phản hồi có mức nghiêm trọng cao (20%). Các ngưỡng và trọng số này do đề tài đặt để sắp xếp, chưa được hiệu chỉnh trên dữ liệu thực.")
p("[[fig:s08]] là trình tự phân cụm. Máy chủ đọc véc-tơ rồi đóng giao dịch đọc trước khi chạy HDBSCAN và gọi mô hình đặt tên, sau đó ghi cụm mới trong một giao dịch ngắn. Cách làm này tránh giữ khóa cơ sở dữ liệu trong lúc chờ dịch vụ bên ngoài.")
fig("s08", "s08_phan_cum.png", "Biểu đồ trình tự phân cụm")
p("Thiết kế này còn hai giới hạn. Thứ nhất, G đếm số phản hồi tuyệt đối, chưa chia cho tổng phản hồi cùng kỳ, nên theo Mục 2.4.2.3 nó chỉ là tín hiệu để điều tra, chưa phải bằng chứng vấn đề đã phổ biến hơn. Thứ hai, hai khoảng thời gian được tính lùi từ ngày hiện tại; với dữ liệu lịch sử được nhập theo lô, cả hai khoảng có thể không có phản hồi nào và tín hiệu sẽ không xuất hiện.")

# =============================================================================== 3.7 UNDERSTAND
h2("3.7. Thiết kế bước Thấu hiểu")
h3("3.7.1. Vì sao cần tác tử điều tra")
p("Bước Lắng nghe cho biết điều gì đang xảy ra: chủ đề nào có nhiều phản hồi, cụm nào đang tăng. Nhưng để quyết định cải tiến, người phụ trách còn cần biết vấn đề tập trung ở đâu và vì sao nó xảy ra. Chẳng hạn, câu hỏi “vì sao phàn nàn về độ chính xác của AI tăng trong tuần này” cần nhiều bước: đếm theo chủ đề, so sánh hai kỳ, xem phân bố theo nguồn và mức độ nghiêm trọng, rồi đọc vài phản hồi đại diện. Bước sau phụ thuộc vào kết quả của bước trước, nên khó viết sẵn thành một chương trình cố định.")
p("Mục 2.4.3.1 đã phân biệt quy trình định trước với tác tử AI tự chọn bước, và theo khuyến nghị của Anthropic, chỉ dùng tác tử khi nhiệm vụ thực sự cần [21]. HappyNest kết hợp cả hai: các phép đếm, lọc và so sánh do chương trình thực hiện chính xác; tác tử chỉ quyết định nên tra cứu gì tiếp theo và diễn giải kết quả. Cách làm này dựa trên ý tưởng kết hợp suy luận với hành động của ReAct [10]. Thay vì đưa toàn bộ phản hồi vào một lời gọi mô hình, tác tử chỉ đọc những gì công cụ trả về, nhờ đó mọi con số trong nhận định đều truy được về một lần tra cứu cụ thể.")
h3("3.7.2. Vòng điều tra có giới hạn")
p("Mỗi lượt điều tra bắt đầu từ một câu hỏi của người phụ trách và đi qua các bước trong [[fig:a08a]]:")
b("Che thông tin và nạp bối cảnh: câu hỏi được che thông tin định danh; hệ thống đọc các trường dữ liệu của sản phẩm, bộ chủ đề và các cụm hiện có.", "Che thông tin và nạp bối cảnh")
b("Bước đầu cố định: chương trình luôn mở đầu bằng phép đếm phản hồi theo chủ đề, để tác tử có bức tranh tổng quát trước khi lọc hẹp.", "Bước đầu cố định")
b("Chọn bước tra cứu: mô hình chọn công cụ và điều kiện lọc cho bước tiếp theo.", "Chọn bước tra cứu")
b("Chạy công cụ: chương trình kiểm tra điều kiện lọc, chạy công cụ và lưu kết quả thành bằng chứng.", "Chạy công cụ")
b("Đánh giá: mô hình xem bằng chứng mới ủng hộ hay mâu thuẫn với giả thuyết nào, còn câu hỏi nào chưa trả lời và đã đủ để kết luận chưa. Nếu chưa đủ, vòng lặp quay lại bước chọn tra cứu.", "Đánh giá")
fig("a08a", "a08a_vong_tra_cuu.png", "Biểu đồ hoạt động vòng tra cứu của tác tử")
p("Bước đầu được cố định vì trong quá trình chạy thử, mô hình đôi khi lọc hẹp ngay từ đầu và bỏ sót một phần dữ liệu liên quan. Tương tự, với câu hỏi về thay đổi theo thời gian, chương trình buộc lượt điều tra phải có ít nhất một phép so sánh hai kỳ trước khi kết luận; nếu chưa đo được, độ tin cậy của nhận định bị hạ và nhận định phải nêu rõ giới hạn này.")
p("Để tác tử không chạy vòng lặp tốn kém, chương trình chủ động chuyển sang bước tổng hợp khi gặp một trong các điều kiện: đã chạy 8 vòng; đã dùng gần hết 18 lời gọi mô hình cho phép (luôn giữ lại một lời gọi cho bước tổng hợp); bước đánh giá báo đã đủ bằng chứng; hoặc bước tiếp theo trùng hoàn toàn với một bước đã chạy. Các điều kiện này được chương trình kiểm tra trước mỗi lời gọi mô hình, không phụ thuộc vào việc mô hình tự dừng. Luồng điều tra được hiện thực bằng LangGraph [23] và chạy ở luồng nền, như trình tự trong [[fig:s09]].")
fig("s09", "s09_tao_dieu_tra.png", "Biểu đồ trình tự tạo lượt điều tra")
h3("3.7.3. Công cụ tra cứu và bằng chứng")
p("Tác tử chỉ được dùng chín công cụ chỉ đọc, liệt kê trong [[tbl:tools]]. Mỗi công cụ luôn gắn với sản phẩm đang điều tra và mỗi lần trả về tối đa 30 phản hồi. Đây là cách hiện thực yêu cầu kiểm soát công cụ ở Mục 2.4.3.1.")
tbl("tools", "Các công cụ tra cứu của tác tử", [130, 295], [
    ["Công cụ", "Tác dụng"],
    ["Xem cấu trúc dữ liệu", "Liệt kê các trường phân tích của sản phẩm và mức độ đầy đủ của từng trường"],
    ["Xem chi tiết một trường", "Giá trị phổ biến, số giá trị khác nhau và tỷ lệ ô trống của một trường"],
    ["Đếm theo nhóm", "Đếm phản hồi theo chủ đề, mức độ nghiêm trọng, nguồn hoặc một trường bất kỳ, có lọc"],
    ["So sánh hai kỳ", "So sánh số phản hồi của một vấn đề giữa kỳ hiện tại và kỳ trước (7 hoặc 30 ngày)"],
    ["Phân tích phân bố", "Xem một nhóm vấn đề phân bố thế nào theo các chiều dữ liệu"],
    ["Tìm theo ý nghĩa", "Tìm các phản hồi gần nghĩa với một câu mô tả"],
    ["Lấy phản hồi đại diện", "Lấy một số phản hồi tiêu biểu, xen kẽ giữa các nguồn"],
    ["Xem một cụm", "Xem số liệu biến động và mức độ nghiêm trọng của một cụm"],
    ["Tìm nhận định tương tự", "Tìm các nhận định đã có trước đây về vấn đề tương tự"],
])
p("[[fig:s10]] cho thấy một bước tra cứu diễn ra như thế nào. Mô hình không tự viết câu lệnh truy vấn cơ sở dữ liệu: nó chỉ gửi tên công cụ, tên trường và giá trị cần lọc. Bộ biên dịch truy vấn đối chiếu với danh sách trường hợp lệ của sản phẩm rồi mới tạo truy vấn có tham số, và từ chối trường lạ. Khi công cụ gặp lỗi, lỗi được trả lại như một quan sát để mô hình điều chỉnh, không làm dừng cả lượt.")
fig("s10", "s10_mot_buoc_tra_cuu.png", "Biểu đồ trình tự một bước tra cứu")
p("Mỗi lần chạy công cụ tạo ra một bằng chứng gồm tên công cụ, mô tả ngắn, dữ liệu trả về và độ phủ dữ liệu. Kết quả rỗng hoặc lỗi không được tính là bằng chứng, vì tra cứu không ra dữ liệu chưa đủ để kết luận sản phẩm không có vấn đề.")
h3("3.7.4. Tổng hợp nhận định và điểm kiểm duyệt thứ hai")
p("[[fig:a08b]] mô tả phần cuối của lượt điều tra. Nhận định được tổng hợp theo cách phân biệt ở Mục 2.4.3.2: điều quan sát được, giả thuyết giải thích và giới hạn, trong đó phần quan sát và phần giả thuyết có độ tin cậy riêng. Chương trình kiểm tra nhận định trước khi lưu: mã bằng chứng không thuộc lượt điều tra bị loại; nếu không còn bằng chứng khả dụng, hệ thống tạo nhận định “không đủ bằng chứng” mà không gọi mô hình; nếu nhận định chỉ dựa trên vài phản hồi mẫu hoặc kết quả tìm theo ý nghĩa, độ tin cậy bị giới hạn ở mức 0,7. Các kiểm tra này xác nhận bằng chứng có thật và đúng phạm vi; còn việc bằng chứng có thực sự ủng hộ kết luận hay không vẫn do người duyệt đánh giá.")
fig("a08b", "a08b_tong_hop_kd2.png", "Biểu đồ hoạt động tổng hợp nhận định và kiểm duyệt thứ hai")
p("Khi nhận định được lưu, lượt điều tra tạm dừng và giữ toàn bộ trạng thái trong cơ sở dữ liệu nhờ cơ chế tạm dừng của LangGraph [23]. Việc chờ người duyệt vì vậy không chiếm tài nguyên máy chủ, và người phụ trách có thể quay lại duyệt sau. Giao diện hiển thị nhận định cùng bằng chứng ở dạng dễ đọc: câu mô tả, số liệu, biểu đồ phân bố và trích đoạn phản hồi đã che thông tin.")
p("Người phụ trách có bốn lựa chọn: duyệt, sửa, từ chối hoặc yêu cầu điều tra thêm, hiện thực nguyên tắc hỗ trợ sửa sai và giữ quyền kiểm soát của người dùng [22]. [[fig:s11]] là trình tự xử lý quyết định. Quyết định được nhận ngay rồi xử lý nền; khi chọn điều tra thêm, ý kiến của người duyệt được đưa trở lại vòng điều tra để tác tử tra cứu tiếp, còn ba lựa chọn khác kết thúc lượt. Mỗi quyết định được ghi lại cùng người duyệt, thời điểm và lý do. Khi lượt điều tra tiếp tục sau tạm dừng, một số bước có thể chạy lại, nên thao tác lưu nhận định kiểm tra trước để không tạo bản ghi trùng, đúng lưu ý ở Mục 2.4.3.2.")
fig("s11", "s11_quyet_dinh_kd2.png", "Biểu đồ trình tự xử lý quyết định ở điểm kiểm duyệt thứ hai")

# =============================================================================== 3.8 ACT
h2("3.8. Thiết kế bước Hành động")
p("Bước Hành động trả lời câu hỏi “nên làm gì” sau khi đã hiểu vấn đề. Khảo sát ở Mục 1.2.1 không cho thấy mọi nhóm đều gặp khó khăn nghiêm trọng khi ưu tiên (31/36 người chấm mức 3), nên bước này không nhằm thay người phụ trách quyết định. Mục tiêu của nó là trình bày các phương án cùng căn cứ một cách minh bạch để người phụ trách so sánh và lựa chọn. Hệ thống chỉ đề xuất, không tác động lên sản phẩm.")
h3("3.8.1. Sinh phương án từ nhận định đã duyệt")
p("Phương án chỉ được sinh từ nhận định đã được duyệt hoặc đã sửa. Ràng buộc này bảo đảm mọi đề xuất đều dựa trên một kết luận đã qua kiểm tra của con người. Mục 2.4.4.1 yêu cầu tách căn cứ về vấn đề khỏi căn cứ về cách xử lý, nên đầu vào của mô hình gồm hai phần: tối đa 10 bằng chứng của nhận định, cho biết điều gì đang xảy ra; và một thư viện 18 thẻ thực hành do đề tài biên soạn từ các nguồn trong [[tbl:lib]], gợi ý cách có thể xử lý. Mỗi thẻ ghi nguyên tắc, điều kiện áp dụng, giới hạn và nguồn.")
tbl("lib", "Nguồn của thư viện thực hành", [120, 245, 60], [
    ["Góc nhìn", "Nguồn", "Số thẻ"],
    ["Sản phẩm", "Khung ưu tiên RICE [24]", "3"],
    ["Khám phá nhu cầu", "Cây cơ hội – giải pháp [31]", "3"],
    ["Kỹ thuật", "Triển khai thử nghiệm giới hạn của Google SRE [32]", "3"],
    ["Trải nghiệm người dùng", "Hướng dẫn tương tác người – AI [22]", "3"],
    ["Rủi ro", "Khung quản lý rủi ro AI của NIST [29], [30]", "2"],
    ["Thành công khách hàng", "Xử lý phản hồi vòng kín của Qualtrics [33]", "2"],
    ["Tài chính", "Kinh tế đơn vị của FinOps Foundation [34]", "2"],
])
p("[[fig:a09]] mô tả luồng sinh và chọn phương án. Trong một lời gọi duy nhất, mô hình đánh giá mức liên quan của nhận định với tám nhóm nghiệp vụ: marketing, pháp lý, thiết kế, tài chính, kỹ thuật, vận hành, kinh doanh và hỗ trợ khách hàng. Chỉ nhóm có mức liên quan từ 0,5 trở lên mới nhận phương án, nên một nhận định thường chỉ có vài phương án chứ không đủ tám. Mỗi phương án kèm phần căn cứ gồm bằng chứng được sử dụng, thẻ thực hành được tham khảo, một phương án thay thế, các đánh đổi, giả định và tiêu chí để biết phương án thành công.")
fig("a09", "a09_hanh_dong.png", "Biểu đồ hoạt động sinh và chọn phương án")
p("[[fig:s12]] là trình tự sinh phương án. Trước khi lưu, máy chủ kiểm tra: bằng chứng phải thuộc nhận định và đúng sản phẩm; thẻ thực hành phải có trong thư viện; nếu không có thẻ phù hợp thì phải ghi rõ là thiếu nguồn. Mô hình chỉ được chọn mã thẻ, còn đường dẫn nguồn do máy chủ điền, nên kết quả không chứa đường dẫn do mô hình tự tạo. Khi sinh lại, hệ thống chỉ thay các phương án chưa được người phụ trách xử lý. Như Mục 2.6.2 đã nêu, các kiểm tra này hạn chế nguồn không tồn tại nhưng không xác nhận thực hành đã được áp dụng đúng bối cảnh.")
fig("s12", "s12_sinh_phuong_an.png", "Biểu đồ trình tự sinh phương án")
h3("3.8.2. Điểm ưu tiên và ma trận tác động – công sức")
p("Để so sánh các phương án, mô hình ước lượng bốn thành phần: tác động, mức cấp bách, công sức (cùng thang 1–10) và độ tin cậy (từ 0 đến 1). Điểm ưu tiên không do mô hình tính mà do máy chủ tính theo một công thức cố định, để kết quả nhất quán và kiểm tra lại được. Đề tài tham khảo khung RICE ở việc công khai tiêu chí [24], còn trọng số là lựa chọn riêng, theo Công thức (3.2):")
eq("P")
p("Trong đó P là điểm ưu tiên; I là tác động, U là mức cấp bách, E là công sức; C là độ tin cậy, được nhân 10 để cùng thang đo với ba thành phần còn lại. Công sức càng thấp thì điểm càng cao, và P nằm trong khoảng từ 0,7 đến 9,9. Ví dụ, một phương án có I = 8, U = 7, E = 3 và C = 0,8 sẽ có P = 3,2 + 2,1 + 1,6 + 0,7 = 7,6. Các trọng số có thể đổi qua cấu hình và chưa được tối ưu trên dữ liệu của tổ chức nào.")
p("Phương án còn được đặt vào ma trận tác động – công sức với ngưỡng 5 để người phụ trách nhìn nhanh: tác động cao và công sức thấp là nhóm làm nhanh; tác động cao và công sức cao là nhóm đầu tư chiến lược; tác động thấp và công sức thấp là nhóm ưu tiên thấp; còn lại là nhóm cân nhắc lại. Điểm số và ma trận chỉ giúp minh bạch căn cứ. Các yếu tố như an toàn, nghĩa vụ pháp lý hay sự phụ thuộc giữa các công việc vẫn do người phụ trách cân nhắc.")
h3("3.8.3. Điểm kiểm duyệt thứ ba và theo dõi sau quyết định")
p("Tại điểm kiểm duyệt thứ ba, người phụ trách có thể sửa tác động, mức cấp bách, công sức và nội dung phương án, rồi chấp nhận hoặc từ chối. [[fig:s13]] cho thấy giá trị do người phụ trách nhập được lưu riêng, còn giá trị ước lượng của AI được giữ nguyên; điểm ưu tiên và vị trí trong ma trận được tính lại theo giá trị của người phụ trách. Thiết kế này cho phép đo mức đồng thuận giữa người và AI, một tiêu chí đánh giá đã nêu ở Mục 2.4.5.2. Người phụ trách cũng có thể tự thêm phương án không do AI đề xuất.")
fig("s13", "s13_kiem_duyet_kd3.png", "Biểu đồ trình tự sửa và chọn phương án")
p("Trạng thái “đã chấp nhận” chỉ ghi nhận lựa chọn trong ứng dụng, chưa có nghĩa phương án đã được triển khai. Hệ thống có một chức năng quan sát trước – sau, mô tả ở [[fig:a10]] và [[fig:s14]]: với phương án đã chấp nhận quá 7 ngày, chương trình đếm số phản hồi cùng bối cảnh trong 7 ngày trước và 7 ngày sau ngày tạo phương án. Chức năng này hiện chỉ có ở dạng API, chưa có màn hình. Vì mốc so sánh là ngày tạo phương án chứ không phải ngày triển khai thật, kết quả chỉ là quan sát ban đầu và không chứng minh quan hệ nhân quả (Mục 2.4.5.2).")
fig("a10", "a10_quan_sat.png", "Biểu đồ hoạt động quan sát trước – sau")
fig("s14", "s14_quan_sat.png", "Biểu đồ trình tự quan sát trước – sau")

# =============================================================================== 3.9 UI
h2("3.9. Thiết kế giao diện")
h3("3.9.1. Sơ đồ màn hình")
p("Thanh điều hướng được chia đúng theo ba bước Lắng nghe, Thấu hiểu và Hành động để người dùng biết mình đang ở đâu trong quy trình; mỗi bước mang một màu riêng (xem [[fig:w01]]). Người dùng có thể đi theo thứ tự hoặc mở thẳng màn hình cần dùng. Một dải gợi ý “bước tiếp theo” cùng các nhãn đếm việc đang chờ giúp người mới biết nên làm gì tiếp. [[tbl:screens]] liệt kê các màn hình chính và điểm kiểm duyệt tương ứng.")
fig("w01", "w01_so_do_man_hinh.png", "Sơ đồ màn hình của HappyNest")
tbl("screens", "Các màn hình chính theo từng bước", [70, 100, 190, 65], [
    ["Bước", "Màn hình", "Công việc chính", "Kiểm duyệt"],
    ["Lắng nghe", "Nhập dữ liệu", "Tải tệp CSV, xem hồ sơ cột, xác nhận ý nghĩa các cột", "Thứ nhất"],
    ["Lắng nghe", "Bộ chủ đề (Taxonomy)", "Sinh, gợi ý, sửa và áp dụng chủ đề", "Áp dụng chủ đề"],
    ["Lắng nghe", "Kho phản hồi", "Tra cứu, lọc, chạy phân loại, xem phản hồi tương tự", "Không"],
    ["Thấu hiểu", "Đồ thị dữ liệu", "Đặt câu hỏi cho tác tử, theo dõi điều tra, duyệt nhận định ngay tại chỗ", "Thứ hai"],
    ["Thấu hiểu", "Báo cáo", "Xem lại các nhận định và bằng chứng", "Không"],
    ["Hành động", "Ma trận ưu tiên", "Xem ma trận, sửa điểm, chấp nhận hoặc từ chối phương án", "Thứ ba"],
    ["Hành động", "Các bên liên quan", "Xem phương án theo từng nhóm nghiệp vụ", "Không"],
])
h3("3.9.2. Nguyên tắc trình bày kết quả của AI")
p("Mục 2.4.3.2 nhấn mạnh rằng kiểm duyệt không chỉ là thao tác bấm nút: người duyệt cần thấy nguồn và bối cảnh trước khi quyết định. Giao diện vận dụng các hướng dẫn tương tác người – AI [22] theo bốn nguyên tắc:")
b("Nội dung do AI tạo luôn có nhãn riêng để người dùng phân biệt với dữ liệu gốc và nội dung do người nhập.")
b("Nhận định hiển thị điều quan sát được, giả thuyết, giới hạn và bằng chứng trước các nút quyết định, để người duyệt đọc căn cứ trước khi chọn.")
b("Bằng chứng được trình bày thành thẻ dễ đọc gồm câu mô tả, số liệu và trích đoạn phản hồi, thay vì dữ liệu kỹ thuật thô.")
b("Thao tác tốn chi phí luôn có bước xác nhận, còn tác vụ chạy lâu có khu vực theo dõi tiến độ.")
p("Giao diện hỗ trợ tiếng Việt và tiếng Anh. Báo cáo tổng hợp theo kỳ 7, 30 hoặc 90 ngày được tính hoàn toàn bằng truy vấn cơ sở dữ liệu, không gọi AI (xem [[fig:s15]]). Một giới hạn cần nêu là bằng chứng hiện chỉ hiển thị trích đoạn phản hồi, chưa có liên kết để mở thẳng phản hồi gốc trong kho phản hồi; việc truy vết đầy đủ mới được bảo đảm ở tầng dữ liệu như mô tả ở Mục 3.5.1.")
fig("s15", "s15_bao_cao.png", "Biểu đồ trình tự xem báo cáo tổng hợp")

# =============================================================================== 3.10 conclusion
h2("3.10. Kết luận chương")
p("Chương 3 đã chuyển các khó khăn ở Chương 1 và các lựa chọn phương pháp ở Chương 2 thành thiết kế cụ thể của HappyNest, thể hiện qua các biểu đồ use case, hoạt động, trình tự, lớp, trạng thái, gói, thành phần và triển khai. Mỗi bước có một vai trò rõ ràng: Lắng nghe gom phản hồi phân tán về một kho thống nhất và giảm việc gán loại thủ công; Thấu hiểu giúp đi từ “điều gì đang xảy ra” đến “vì sao” bằng các lần tra cứu có bằng chứng; Hành động biến nhận định đã duyệt thành các phương án có căn cứ để người phụ trách lựa chọn. Xuyên suốt ba bước là cùng một nguyên tắc: chương trình làm phần có quy tắc, mô hình AI hỗ trợ trong giới hạn được kiểm soát và con người quyết định tại ba điểm kiểm duyệt. [[tbl:goals]] đối chiếu thiết kế với các mục tiêu cụ thể đã đặt ra ở Mục 1.3.2.")
tbl("goals", "Mức đáp ứng các mục tiêu cụ thể ở Mục 1.3.2", [120, 160, 145], [
    ["Mục tiêu", "Thiết kế đáp ứng", "Mức đáp ứng"],
    ["Tiếp nhận và chuẩn hóa phản hồi", "Nhập CSV có xác nhận ý nghĩa cột; nhập tay từng phản hồi", "Một phần: chưa có biểu mẫu thu thập và kết nối trực tiếp với nguồn"],
    ["Che thông tin định danh", "Bước che thông tin ở mọi cửa vào của văn bản", "Đáp ứng; nhận diện tên người còn hạn chế"],
    ["Đánh giá mức nghiêm trọng và độ tin cậy", "Thuộc tính trong kết quả phân loại", "Đáp ứng; độ tin cậy chưa được hiệu chuẩn"],
    ["Nhóm các phản hồi tương tự", "Véc-tơ, tìm theo ý nghĩa, phân cụm theo sản phẩm", "Đáp ứng"],
    ["Đặt tên chủ đề, nhận diện xu hướng", "Đặt tên cụm, so sánh hai khoảng 30 ngày", "Đáp ứng; tỷ lệ tăng chưa chia theo tổng phản hồi"],
    ["Báo cáo liên kết tới phản hồi nguồn", "Chuỗi bằng chứng – nhận định – phương án", "Một phần: giao diện chưa có liên kết mở phản hồi gốc"],
    ["Chuyển trường hợp rủi ro cho người kiểm duyệt", "Nhóm chưa phân loại; sắp xếp theo mức nghiêm trọng và độ tin cậy; ba điểm kiểm duyệt", "Một phần: chưa có hàng chờ kiểm duyệt tự động"],
    ["Chấp nhận, sửa, từ chối, yêu cầu phân tích thêm", "Bốn lựa chọn ở điểm kiểm duyệt thứ hai; sửa điểm ở điểm kiểm duyệt thứ ba", "Đáp ứng"],
    ["Theo dõi chủ đề, xu hướng và trạng thái kiểm duyệt", "Báo cáo tổng hợp, danh sách cụm, nhãn việc đang chờ", "Một phần: chưa gom vào một màn hình tổng quan"],
    ["Ghi nhận chỉ số đánh giá", "Nhật ký lời gọi AI, nhật ký quyết định, API chỉ số", "Một phần: chưa có màn hình; độ chính xác cần đánh giá riêng"],
    ["Gợi ý hành động theo phòng ban", "Tám nhóm nghiệp vụ, thư viện 18 thẻ thực hành", "Đáp ứng"],
])
p("Thiết kế hiện tại còn một số giới hạn đã được nêu trong chương: tác vụ nền chưa có hàng đợi bền vững, chỉ số tổng hợp chưa tách theo tài khoản, tín hiệu biến động chưa chuẩn hóa theo tổng phản hồi và phép quan sát trước – sau dùng mốc tạo phương án thay vì mốc triển khai. Chất lượng của phân loại, nhận định và phương án không thể suy ra từ thiết kế; các nội dung này được đánh giá ở Chương 4 theo tiêu chí đã đặt ra ở Mục 2.4.5.")


# =============================================================================== resolve
def main(trimdir, sizes_csv, out, maxh=640.0):
    sizes = {}
    with open(sizes_csv, encoding="utf-8-sig") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 5:
                sizes[parts[0]] = (float(parts[3]), float(parts[4]))
    fig_no, tbl_no = {}, {}
    fi = ti = 0
    for it in S:
        if it["t"] == "fig":
            fi += 1
            fig_no[it["id"]] = fi
        if it["t"] == "capt":
            ti += 1
            tbl_no[it["id"]] = ti

    def sub(text):
        def r(m):
            kind, key = m.group(1), m.group(2)
            if kind == "fig":
                return "Hình 3.%d" % fig_no[key]
            return "Bảng 3.%d" % tbl_no[key]
        out_text = re.sub(r"\[\[(fig|tbl):([A-Za-z0-9_]+)\]\]", r, text)
        if "[[" in out_text:
            raise SystemExit("unresolved ref: " + text[:80])
        return out_text

    res = []
    restarted_f = restarted_t = False
    for it in S:
        it = dict(it)
        if "x" in it:
            it["x"] = sub(it["x"])
        if it["t"] == "fig":
            base = os.path.splitext(it["img"])[0]
            if it.get("wpt") is None:
                w, h = sizes[base]
                s = min(1.0, 425.0 / w, maxh / h)
                it["wpt"] = round(w * s, 1)
            it["img_path"] = os.path.join(trimdir, it["img"])
        if it["t"] == "capf" and not restarted_f:
            it["restart"] = True
            restarted_f = True
        if it["t"] == "capt" and not restarted_t:
            it["restart"] = True
            restarted_t = True
        res.append(it)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=0)
    print("items", len(res), "figs", fi, "tables", ti)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], a[3], float(a[4]) if len(a) > 4 else 640.0)
