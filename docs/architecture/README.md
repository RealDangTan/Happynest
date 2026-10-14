# Kiến trúc hệ thống — AI Feedback Agent (VoC OS)

Bộ sơ đồ phân tích & thiết kế hệ thống cho khóa luận
**"AI Agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng về sản phẩm AI"**.

Tất cả sơ đồ viết bằng **Mermaid** — render trực tiếp trên GitHub / VS Code / Typora.

## Danh mục sơ đồ

| # | File | Nội dung | Loại sơ đồ |
|---|------|----------|------------|
| 1 | [01-system-overview.md](01-system-overview.md) | Bối cảnh hệ thống (C4-L1) + kiến trúc thành phần (C4-L2) | Context + Component |
| 2 | [02-data-flow.md](02-data-flow.md) | Luồng dữ liệu LISTEN → UNDERSTAND → ACT, ranh giới PII | Data Flow (DFD mức 0–1) |
| 3 | [03-sequence-ingestion-analysis.md](03-sequence-ingestion-analysis.md) | Nhập CSV + Cổng #1, batch phân loại + embedding, phân cụm HDBSCAN | Sequence |
| 4 | [04-sequence-understand-hitl.md](04-sequence-understand-hitl.md) | UNDERSTAND agent + Cổng #2 (interrupt LangGraph), ACT + Cổng #3 | Sequence |
| 5 | [05-langgraph-state-machine.md](05-langgraph-state-machine.md) | Máy trạng thái graph LangGraph, trạng thái insight/action/import | State Machine |
| 6 | [06-erd.md](06-erd.md) | Mô hình thực thể — quan hệ đầy đủ (15 bảng + 4 bảng checkpoint) | ERD |
| 7 | [07-api-module-diagram.md](07-api-module-diagram.md) | Tổ chức module API, luồng xác thực JWT cookie, truy cập dùng chung | Package + Sequence |
| 8 | [08-deployment.md](08-deployment.md) | Triển khai: dev Windows, prod Ubuntu VPS + systemd + Caddy | Deployment |
| 9 | [09-frontend-architecture.md](09-frontend-architecture.md) | Kiến trúc Next.js App Router, ánh xạ trang ↔ endpoint | Component |

## Các quyết định kiến trúc cốt lõi

- **Kiến trúc 3 lớp chức năng:** LISTEN (thu thập + chuẩn hóa) → UNDERSTAND (phân tích + agent) → ACT (đề xuất hành động + đo tác động), với **3 cổng Con-người-trong-vòng (HITL Gate #1/#2/#3)**.
- **Ranh giới PII:** nội dung thô `raw_content` chỉ nằm trong DB; chỉ `feedback_text` (đã sanitize bằng Presidio + Stanza) được đưa vào prompt, log, trace và API response.
- **LLM structured output:** `response_format json_schema` → fallback prompt-JSON + Pydantic validate + 1 lần retry; `temperature=0`; routing model theo use-case qua biến môi trường.
- **Persist graph:** LangGraph + `AsyncPostgresSaver` (4 bảng checkpoint ngoài Alembic), interrupt tại `persist_insight` cho Cổng #2.
- **Truy vết kép:** Langfuse Cloud (observability) + bảng `llm_call_logs` trong Postgres (bằng chứng độc lập nhà cung cấp — chỉ metadata, không nội dung).
- **Không Docker:** dev = FastAPI native trên Windows; prod = Ubuntu VPS + systemd + Caddy; DB = Supabase PostgreSQL 17 + pgvector qua session pooler.
