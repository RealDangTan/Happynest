# Nguồn Chương 3 (bản 2026-11-06)

Thư mục này giữ mọi thứ cần để dựng lại Chương 3 trong `../Khoa-luan-Le-Dang-Tan-11236199-chuong3-v3.docx`.

| Tệp | Vai trò |
|---|---|
| `uml/*.puml`, `style.iuml` | 54 biểu đồ UML (use case `uc*`, hoạt động `a*`, trình tự `s*`, lớp `c*`, trạng thái `st*`, gói `p*`, thành phần `k01`, triển khai `d*`, sơ đồ màn hình `w01`) |
| `make_figs.py` | Hai hình tự vẽ còn dùng: kiến trúc ba tầng (`fig33_arch`) và mô hình dữ liệu khái niệm (`fig34_data`), vẽ SVG rồi chụp bằng Chrome headless |
| `content_v3.py` | Toàn bộ nội dung chữ, bảng, đặc tả use case của Chương 3; tự đánh số Hình/Bảng và tính độ rộng hình |
| `build_ch3.ps1` | Dựng chương vào bản sao docx bằng Word COM, giữ kiểu Heading, chú thích SEQ, công thức và danh mục tự động |
| `trim.ps1` | Cắt viền trắng ảnh PlantUML và ghi kích thước tự nhiên (pt) vào `sizes.csv` |

## Dựng lại

```bash
# 1. Vẽ UML (cần Java 8+ và plantuml-1.2024.8.jar; máy owner: D:\ATEMP\plantuml)
cd uml && java -DPLANTUML_LIMIT_SIZE=16384 -jar plantuml-1.2024.8.jar -charset UTF-8 -Playout=smetana -o ../png *.puml
```

```powershell
# 2. Cắt viền, 3. sinh nội dung, 4. dựng docx (nguồn: bản có Chương 1–2 và công thức mẫu)
./trim.ps1 -InDir png -OutDir trim -Pad 20
python -I content_v3.py trim trim/sizes.csv ch3.json 640
./build_ch3.ps1 -Src <khoa-luan-goc.docx> -Dst <ra.docx> -Json ch3.json -ImgDir trim -Log build.txt -Pdf ""
```

Quy ước hình: hành động tô xanh nhạt `#D6E4F2` là quyết định của người phụ trách, tô xám `#E9E9E9` là bước gọi dịch vụ AI, nền trắng do chương trình xử lý. Mọi con số trong hình đã đối chiếu với mã nguồn ngày 2026-11-06 (phân cụm theo sản phẩm, bước điều tra đầu cố định, model theo `.env`).
