# Agent Control — Bảng điều khiển agent UNDERSTAND

Folder này biến agent UNDERSTAND (module phân tích phản hồi người dùng) từ "hộp đen" thành **building box**: toàn bộ cách agent hoạt động được mô tả bằng 1 file bản vẽ (`agent-schema.json`) mà bạn có thể xem, sửa trên trình duyệt, rồi xuất change-request để agent lập trình (Claude Code) áp vào code.

---

## 1. Agent UNDERSTAND là gì, chạy khi nào?

UNDERSTAND là "nhân viên điều tra" của hệ thống: bạn đưa cho nó **một câu hỏi** (vd: *"Tuần này khách than gì về tính năng upload?"*) hoặc một **signal hệ thống** (vd: cluster đang spike), nó tự điều tra dữ liệu feedback rồi viết **một insight có bằng chứng kèm theo** để bạn ra quyết định.

Nó được kích hoạt từ 3 chỗ:

| Chỗ chạy | Cách |
|---|---|
| Web | `POST /api/agent/runs` — nút chạy agent trên UI |
| Terminal | `uv run python scripts/agent_terminal.py` (từ thư mục `backend/`) |
| Kịch bản E2E | `uv run python scripts/e2e_happytest.py` |

## 2. Vòng đời 1 run (ngôn ngữ thường)

1. **Xem hồ sơ** (`load_context`) — đọc thông tin sản phẩm: schema dữ liệu, độ phủ từng trường, taxonomy, 5 cluster nổi bật nhất.
2. **Chọn bước kế** (`planner` — gọi LLM) — "điều tra viên" nhìn câu hỏi + những gì đã biết, rồi chọn: *gọi thêm 1 công cụ phân tích* hay *đủ bằng chứng, viết báo cáo thôi*.
3. **Chạy công cụ** (`dispatch`) — thực thi tool SQL/pgvector được chọn, kết quả lưu vào kho bằng chứng (`evidence`). Tool lỗi cũng chỉ được ghi chú, không làm sập phiên.
4. **Tự đánh giá** (`evaluator` — gọi LLM) — nhìn bằng chứng mới nhất: có gì hỗ trợ, có gì mâu thuẫn, còn câu hỏi nào cần đào thêm, dữ liệu có chất lượng không.
5. **Lặp lại bước 2→4** cho đến khi tự thấy đủ, hoặc chạm trần: tối đa **8 vòng** và **18 lần gọi LLM**.
6. **Viết báo cáo** (`synthesizer` — gọi LLM) — tổng hợp thành insight: phần *finding* (fact có bằng chứng) tách khỏi phần *hypothesis* (suy luận, kèm mức tin cậy riêng). Chỉ được trích dẫn bằng chứng có thật — id bịa sẽ bị hệ thống loại.
7. **Nộp chờ duyệt** (`persist_insight` — Gate #2) — insight lưu với status `pending`, phiên **dừng lại** chờ con người.
8. **Chốt** (`apply_decision`) — bạn chọn: **approve** (duyệt) / **edit** (sửa text rồi duyệt) / **investigate_more** (đào tiếp — quay lại bước 2) / **reject** (loại). Mọi quyết định đều được ghi audit trail.

Tóm lại: **3 điểm gọi LLM** (planner, evaluator, synthesizer), phần còn lại là code chạy chắc chắn. Mọi kết quả tool và mọi call LLM đều được lưu lại (bảng `evidence` và `llm_call_logs`) nên luôn truy vết được.

## 3. Các file trong folder này

| File | Là gì |
|---|---|
| `agent-schema.json` | **Bản vẽ hiện tại** của agent — nguồn sự thật. Mô tả từng node, prompt, tool, ngưỡng. Cập nhật trong cùng commit mỗi khi code agent thay đổi. |
| `schema-guide.md` | Bảng giải thích từng field của schema bằng tiếng Việt không kỹ thuật. |
| `editor.html` | **Bảng điều khiển trên trình duyệt** — mở trực tiếp bằng double-click, không cần server. |
| `change-requests/` | Nơi lưu các đề nghị sửa của bạn (template có sẵn). |

## 4. Cách dùng editor.html

Trang **nhúng sẵn bản vẽ hiện trạng** của agent — double-click là thấy ngay toàn bộ agent như nó đang chạy, không cần nạp file gì cả. (Nút "Nhập JSON…" chỉ dùng khi bạn muốn nạp một bản schema khác, vd bản đề xuất đã tải xuống.)

1. Double-click `editor.html`.
2. Tab **Graph** mở sẵn: sơ đồ dạng graph của agent — node kéo thả được, mũi tên có nhãn điều kiện (nét đứt = edge điều kiện), Gate #2 nền vàng.
   - **Bấm node** → sửa tên/kind/purpose/prompt/fallback. **Kéo node** → sắp xếp lại bố cục (lưu vào schema, không tính là thay đổi).
   - **Bấm nhãn trên mũi tên** → sửa edge (from/to/điều kiện) hoặc xoá. **＋ Node / ＋ Edge** → thêm mới.
   - Mọi thao tác đụng cấu trúc đều có cảnh báo vàng vì Claude Code sẽ phải đồng bộ `graph.py`.
3. Sửa những gì bạn muốn:
   - **Knobs** (ngưỡng/trần): đổi số trực tiếp.
   - **Prompt** của planner / evaluator / synthesizer: sửa text trong ô lớn.
   - **Tools**: bật/tắt khỏi catalog mà planner được chọn.
   - **Cấu trúc** (node/edge): xem được; sửa được nhưng sẽ bị cảnh báo vì cần implement lại code.
4. Bấm **Copy change-request** để lấy markdown mô tả đúng những gì bạn đổi (so với hiện trạng), hoặc **Tải JSON** để xuất bản schema đã sửa.
5. Dán change-request vào `change-requests/`, rồi nói với Claude Code: *"áp dụng change-request X"*.

**Cầu nối bạn ↔ tôi:** khi tôi áp change-request vào code, tôi cũng cập nhật lại bản vẽ hiện trạng trong chính `editor.html` (object `EMBEDDED_SCHEMA`) và `agent-schema.json` trong cùng commit — nên lần mở sau, trang luôn phản ánh đúng agent mới.

## 5. Luồng làm việc với agent lập trình

```
Bạn sửa trên editor.html
   ↓ xuất change-request vào change-requests/
   ↓ nói với Claude Code: "áp dụng CR ..."
Claude Code sửa code backend (nodes.py / config.py / graph.py …)
   + cập nhật agent-schema.json về trạng thái mới
   → trong CÙNG MỘT commit
```

Schema luôn khớp code: nó là hợp đồng, không phải config runtime — agent **không đọc** file này lúc chạy.

## 6. Biên an toàn không được phá (dù schema đổi thế nào)

- PII: chỉ nội dung đã sanitize được phép đi vào prompt/log/trace.
- Synthesizer chỉ được trích evidence có thật (whitelist server-side).
- Trần vòng lặp + ngân sách LLM luôn được kiểm tra trước mỗi call.
- Text con người gõ ở Gate #2 được re-sanitize trước khi lưu DB.

Chi tiết: xem `safety_rules` trong `agent-schema.json`.
