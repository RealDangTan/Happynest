# Decision Log — AI Feedback Agent

Quy tắc bất di bất dịch: **MỌI** lệch khỏi plan đã chốt (conflict package, thiếu apt package, quirk của LLM provider, spike fail…) phải có entry dated ngay tại đây trước khi sang việc khác. Đây là bằng chứng quy trình cho khóa luận.

## Format entry

```markdown
## YYYY-MM-DD — <tên quyết định ngắn>
- Context: (vấn đề gặp phải / câu hỏi cần trả lời)
- Decision: (chọn gì)
- Alternatives rejected: (bỏ phương án nào, vì sao)
- Consequence: (hệ quả chấp nhận, rủi ro còn lại)
```

---

## Locked decisions (seeded 2026-08-23, từ execute plan v1)

Bảng quyết định gốc đã chốt với owner của đề tài — KHÔNG re-litigate, chỉ amend qua entry mới:

| Area | Decision |
|---|---|
| Runtime | Python 3.12 qua `uv`; FastAPI native trên Windows |
| Database | PostgreSQL 16 bên trong WSL2 Ubuntu (apt) — localhost:5432; extension `vector`; KHÔNG ANN index (≤1500 rows) |
| Vectors | `VECTOR(1536)`; OpenAI-compatible embeddings API; lưu `embedding_model` + `embedding_dim` mỗi row |
| LLM | openai SDK + `base_url` override (provider rẻ tự chọn); `temperature=0`; structured output: json_schema → fallback prompt-JSON + Pydantic validate + 1 retry |
| PII | Presidio + Stanza vi + regex (EMAIL/URL/IP/VN-PHONE/CCCD); placeholder `<TYPE>`; raw PII không bao giờ ra khỏi biên sanitize |
| HITL trigger | `requires_human_review = severity=="critical" OR safety_issue OR pii_detected OR confidence<0.60` |
| Auth | OAuth2 password flow; pwdlib[argon2]; JWT httpOnly cookie; roles pm \| operations |
| Tracing | Langfuse Cloud Hobby EU + bảng `llm_call_logs` vĩnh viễn trong Postgres |
| Migrations | Alembic + `include_object` filter loại 4 bảng checkpoint langgraph từ ngày đầu |
| Deploy | Native Ubuntu VPS + systemd + Caddy. **Docker bị cấm hoàn toàn.** |

## Spike outcomes (điền khi chạy S1–S6)

| # | Câu hỏi | Pass criterion | Kết quả | Ngày | Fallback kích hoạt? |
|---|---|---|---|---|---|
| S1 | Presidio + Stanza("vi") bắt được PII trong sample VN-EN trộn? | ≥80% recall obvious-type | pending | | |
| S2 | Provider có honor `json_schema` response_format? | ≥9/10 calls valid | pending | | |
| S3 | Embeddings API + roundtrip pgvector qua Supabase? | self-match rank #1 | pending | | |
| S4 | sklearn HDBSCAN cosine sane trên 200 toy vectors? | <5s, noise hợp lý | pending | | |
| S5 | LangGraph interrupt → restart → resume với AsyncPostgresSaver? | resume OK, zero duplicate side effects | pending | | |
| S6 | Parity Windows-native backend ↔ Supabase cloud end-to-end? | green | pending | | |

## Deviations / amendments

## 2026-08-23 — Database chuyển từ PostgreSQL 16-in-WSL2 sang Supabase (amendment v1.1)
- Context: Máy dev chưa có WSL (lệnh `wsl` không tồn tại); cài WSL2 cần quyền admin + khả năng phải restart máy. Owner đề xuất Supabase vì hỗ trợ cả Postgres thuần lẫn pgvector. Đã phản biện hai chiều trước khi chốt.
- Decision: Dùng **Supabase** (managed PostgreSQL **17**, extension `vector`) làm DB duy nhất cho dev. Kết nối từ backend qua **session pooler** `aws-0-<region>.pooler.supabase.com:5432` (IPv4 ổn định; tránh transaction pooler :6543 vì phá prepared statements của Alembic). Extension cài bare `CREATE EXTENSION IF NOT EXISTS vector` vào schema `extensions` (quy ước Supabase) — engine đặt `options=-csearch_path=extensions,public`. Pool nhỏ `pool_size=2, max_overflow=2`. Integration tests dùng **free project thứ 2** làm `TEST_DATABASE_URL`.
- Alternatives rejected: (1) Cài WSL2 Ubuntu theo locked stack gốc — bị loại vì cần admin + restart, rào cản ngay giai đoạn đầu; (2) PostgreSQL native Windows installer — vẫn tự host PG16 localhost nhanh hơn nhưng vẫn phải cài phần mềm local và không giải quyết nhu cầu demo từ máy khác; (3) Giữ nguyên plan chờ cài WSL sau — chặn toàn bộ chuỗi verify cần PG.
- Consequence: (a) Free tier **tự pause sau 7 ngày low-activity** → quy tắc vận hành mới: mở dashboard/chạy ≥1 query mỗi <7 ngày; (b) PG **17 thay vì 16**; (c) **không pin được version extension pgvector** nữa (Supabase deprecated pinning từ 2026-08-05); (d) mọi phiên dev cần internet, mất kịch bản offline demo hoàn toàn; (e) raw feedback (chưa sanitize) nằm trên cloud nước ngoài → chọn region **Singapore** (gần VN) hoặc EU (đồng bộ Langfuse), chỉ dùng fake/synthetic data trong dev, ghi rõ khi bảo vệ; (f) lệch dev=prod: deploy mục tiêu vẫn Ubuntu VPS tự quản — chấp nhận bất đối xứng, sẽ ghi chú ở phase deploy; (g) latency query ~50–200ms so với ~1–5ms localhost — chấp nhận vì dataset ≤1500 rows và thời gian LLM call chiếm ưu thế.
