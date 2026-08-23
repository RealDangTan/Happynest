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
| S3 | Embeddings API + roundtrip pgvector qua WSL2? | self-match rank #1 | pending | | |
| S4 | sklearn HDBSCAN cosine sane trên 200 toy vectors? | <5s, noise hợp lý | pending | | |
| S5 | LangGraph interrupt → restart → resume với AsyncPostgresSaver? | resume OK, zero duplicate side effects | pending | | |
| S6 | Parity Windows-native ↔ PG-in-WSL2 end-to-end? | green | pending | | |

## Deviations / amendments

_(chưa có)_
