# Schema Guide — giải thích từng field (không kỹ thuật)

File `agent-schema.json` gồm 9 khối. Bảng dưới giải thích từng khối: nó là gì, sửa nó thì ảnh hưởng gì lên agent.

---

## `$schema_version` và `agent`
- `$schema_version`: số phiên bản của định dạng schema này (không phải của agent). Tăng khi tôi (Claude Code) thêm field mới vào định dạng.
- `agent`: tên agent mà schema mô tả — hiện chỉ có `understand`.

## `meta`
Thông tin chung: phiên bản pipeline (`understand-v1`), file code nào chứa graph/nodes/runner/tools/config, model LLM đọc từ env `LLM_MODEL`, và các cách chạy agent. **Chỉ để tra cứu — sửa không có tác dụng cho tới khi tôi đồng bộ code.**

## `nodes[]` — 7 bước của agent
Mỗi node là 1 trạm làm việc:

| Field | Nghĩa |
|---|---|
| `name` | Tên trạm (khóa liên kết với `edges`). |
| `kind` | `deterministic` = code chạy chắc chắn, không tốn tiền LLM. `llm` = gọi AI. `hitl` = dừng chờ con người. |
| `source` | Vị trí trong code (file:dòng) — để tôi biết sửa chỗ nào khi bạn yêu cầu. |
| `purpose` | Trạm này làm gì, bằng ngôn ngữ thường. |
| `llm.call_type` | Loại call ghi vào bảng `llm_call_logs`: `plan` / `evaluate` / `synthesize`. |
| `llm.user_payload_shape` | Cái gì được nhét vào prompt (input cho AI). |
| `inputs` / `outputs` | Node nhận gì từ state, trả gì vào state. |
| `prompt` | **Text chỉ dẫn cho AI** — đây là phần bạn sửa nhiều nhất: đổi cách agent nghĩ, chọn tool, viết báo cáo. |
| `output_schema` | Khuôn JSON mà câu trả lời AI bắt buộc phải khớp (xem `output_schemas`). |
| `fallback` | Nếu AI trả lời sai khuôn → hành vi an toàn thay thế. |

**Sửa prompt = thay "tính cách"/ưu tiên của trạm đó.** Ví dụ thêm vào prompt của planner "ưu tiên compare_periods sớm" sẽ khiến agent so sánh theo thời gian trước khi đào sâu.

## `edges[]` — đường đi giữa các trạm
`from` → `to` kèm điều kiện `when`. Hai điểm rẽ nhánh quan trọng:
- `planner`: chọn `dispatch` (gọi tool) hay `synthesizer` (viết báo cáo).
- `apply_decision`: nếu bạn chọn `investigate_more` → quay lại `planner`; ngược lại → `END`.

**Cảnh báo:** thêm/bớt node hay edge = thay đổi cấu trúc graph → tôi phải sửa `graph.py` + có thể phải reset checkpoint của các run đang dở. Editor sẽ nhắc bạn điều này.

## `tools[]` — hộp công cụ của planner
9 công cụ SQL/pgvector agent được phép dùng. `params` là khuôn tham số planner phải điền (validate bằng pydantic — sai là tool từ chối).

| Tool | Dùng khi nào |
|---|---|
| `get_schema` | Liệt kê các chiều dữ liệu của sản phẩm + độ phủ. |
| `profile_field` | Xem 1 trường: độ phủ, bao nhiêu giá trị khác nhau, top values. |
| `aggregate_feedback` | Đếm/tính trung bình tin cậy theo nhóm (group-by). |
| `compare_periods` | So sánh 1 vấn đề giữa 2 khoảng thời gian (tăng/giảm bao nhiêu %). |
| `segment_feedback` | Chia một nhóm vấn đề theo tối đa 5 chiều (ai gặp, ở đâu, lúc nào…). |
| `semantic_search` | Tìm feedback gần nghĩa với 1 câu truy vấn (pgvector). |
| `representative_feedback` | Lấy vài feedback tiêu biểu, đa dạng theo nguồn. |
| `inspect_cluster` | Xem chi tiết 1 cluster: số thành viên, severity, tăng trưởng. |
| `search_similar_cases` | Tìm insight cũ tương tự (tiền lệ đã xử lý). |

**Tắt 1 tool = planner không còn thấy nó trong catalog** (khi tôi áp vào code).

## `knobs[]` — các núm vặn
Trần giới hạn hành vi của agent. Số nhỏ hơn = agent đi nhanh, tốn ít tiền, nhưng điều tra nông; số lớn hơn = điều tra sâu hơn, tốn hơn.

| Knob | Vặn lên | Vặn xuống |
|---|---|---|
| `UNDERSTAND_MAX_ITERATIONS` (8) | Điều tra nhiều vòng hơn | Nhanh chốt hơn, nông hơn |
| `UNDERSTAND_LLM_BUDGET_PER_RUN` (18) | Cho phép nhiều call LLM hơn | Rẻ hơn, dễ bị ép synthesize sớm |
| `MAX_RAW_FEEDBACK_PER_TOOL` (30) | Tool trả dữ liệu dày hơn | Prompt gọn hơn, rẻ hơn |
| `MAX_TOTAL_VERBATIMS` (80) | Nhiều trích dẫn gốc hơn | Ít context hơn |
| `_STATEMENT_MAX` (300) | Evidence chi tiết hơn | Evidence gọn hơn |
| `_PROMPT_STATEMENT_MAX` (200) | AI thấy rõ hơn từng evidence | Prompt ngắn hơn |
| `_MAX_CLUSTERS_CONTEXT` (5) | AI thấy nhiều cluster lúc mở màn | Ít nhiễu lúc đầu |

Ghi chú: knob có tiền tố `UNDERSTAND_`/`MAX_` là **env var** (đổi được không cần sửa code — đặt trong `backend/.env`), knob có tiền tố `_` là **hằng số trong code** (tôi phải sửa `nodes.py`).

## `output_schemas` — khuôn câu trả lời của AI
Ba khuôn: `PlannerOut` (chọn bước), `EvaluateOut` (đánh giá bằng chứng), `InsightDraft` (báo cáo cuối). Mỗi field có ràng buộc (max ký tự, 0.0–1.0, bắt buộc…). Sửa khuôn = tôi phải sửa class Pydantic tương ứng + có thể ảnh hưởng DB/API.

## `state_fields` — bộ nhớ tạm của agent trong 1 run
Những gì agent ghi nhớ từ đầu tới cuối phiên. Các list `evidence`, `evaluations`, `tool_history` chỉ cộng dồn, không mất mát giữa các vòng.

## `hitl` — Gate #2 (chốt human-in-the-loop)
Node `persist_insight` luôn dừng chờ bạn. 4 lựa chọn, endpoint resume, audit trail, và 2 luật: text bạn gõ được re-sanitize PII; chọn `investigate_more` thì agent quay lại điều tra nhưng vẫn chịu trần iteration/budget.

## `safety_rules[]` — 7 luật không được phá
Bảo vệ PII, whitelist evidence, trần ngân sách, và fallback an toàn khi LLM lỗi. **Khi yêu cầu tôi sửa agent, các luật này mặc định được giữ nguyên** — muốn mở ngoại lệ nào phải nói rõ và tôi sẽ ghi decisions.md.
