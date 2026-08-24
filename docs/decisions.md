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

## 2026-08-24 — Phase 01: en_core_web_lg khóa vào pyproject thay vì `uv pip install`
- Context: Thực thi docs/plans/01 §3.3 chỉ định cài model spaCy bằng `uv pip install <wheel>` ngoài pyproject. Với uv, `uv sync` mặc định exact-match lockfile → lần sync kế tiếp sẽ **gỡ bỏ** model vừa cài tay; venv trôi khỏi `uv.lock`, mất khả năng tái lập môi trường.
- Decision: Đưa thẳng direct URL reference vào `[project.dependencies]`: `en_core_web_lg @ https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl` — model bị khóa trong `uv.lock` như mọi dependency khác.
- Alternatives rejected: (1) Giữ nguyên `uv pip install` theo plan + nhớ chạy `uv sync --inexact` mọi lần sau — ràng buộc kỷ luật con người, dễ quên; (2) tải model thủ công vào thư mục riêng + load bằng path — lệch chuẩn spaCy `spacy.load('en_core_web_lg')` mà acceptance criteria phase 01 yêu cầu.
- Consequence: pyproject có 1 dependency dạng direct URL (tải từ GitHub Releases, không phải PyPI) — rebuild cần mạng tới github.com; spacy bị chặn `<3.9` bởi constraint của model wheel 3.8.0 (các lib phụ thuộc spacy hiện hành đều tương thích).

## 2026-08-24 — Phase 01: thêm `pydantic-settings` ngoài danh sách §1
- Context: Plan §3.7 liệt kê `pydantic-settings` nhưng yêu cầu log lý do vì không nằm trong bảng package §1 của execute plan.
- Decision: Dùng `pydantic-settings` cho class `Settings` đọc ~15 biến env của env contract §5 (DATABASE_URL, LLM_*, LANGFUSE_*, thresholds…) — typed, có default, validate lúc startup thay vì parse `os.environ` thủ công rải rác trong code.
- Alternatives rejected: Tự viết wrapper `os.getenv` — không có type coercion/validate, lặp code ở mọi module cần config, lỗi cấu hình phát hiện muộn giữa runtime.
- Consequence: Thêm 1 dependency nhỏ (phụ thuộc pydantic vốn đã đến gián tiếp qua FastAPI); chi phí gần như bằng 0.

## 2026-08-24 — Day-one pins (phase 01, uv resolve đầu tiên → uv.lock)
- Context: Rule §10.1 pin ngày đầu — ghi lại version cụ thể mà uv resolver chọn tại thời điểm dựng `backend/pyproject.toml`, làm mốc đối chiếu khi lockfile thay đổi sau này. Runtime: **CPython 3.12.9** (uv-managed, từ `.python-version` = 3.12).
- Decision: Chốt các version top-level dưới đây trong `backend/uv.lock` (commit cùng nhánh phase 01):

| Nhóm | Package == version ngày đầu |
|---|---|
| Web | fastapi 0.141.1 · uvicorn 0.52.4 · python-multipart 0.0.32 |
| DB | sqlalchemy 2.0.52 · alembic 1.19.1 · psycopg[binary,pool] 3.3.4 · pgvector 0.5.0 |
| Auth | pwdlib[argon2] 0.3.1 (argon2-cffi 25.1.0) · pyjwt 2.13.0 |
| PII | presidio-analyzer 2.2.364 · presidio-anonymizer 2.2.364 · stanza 1.14.0 · spacy 3.8.15 · en-core-web-lg 3.8.0 |
| LLM/trace | openai 3.3.1 · langfuse 3.15.0 · langgraph 1.2.11 · langgraph-checkpoint-postgres 3.1.2 |
| Backoff | tenacity 9.1.4 |
| Settings | pydantic-settings 2.15.0 |
| Dev | pytest 9.1.1 · pytest-asyncio 1.4.0 · httpx 0.28.1 |

- Alternatives rejected: Không áp dụng — mọi bounds trong pyproject giữ theo plan §1 (`>=`/range); con số trên là kết quả resolve, không nâng tay.
- Consequence: Smoke import toàn bộ lib nặng PASS trên Windows (Python 3.12.9); spaCy model load OK. Khi cần nâng version nào, sửa bound + cập nhật entry mới tại đây để giữ dấu vết cho khóa luận. Ghi chú vận hành nhỏ: uv cache nằm ở C: còn venv ở D: → hardlink fail, uv fallback sang copy (warning vô hại).
