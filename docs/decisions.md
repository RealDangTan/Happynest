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
| S1 | Presidio + Stanza("vi") bắt được PII trong sample VN-EN trộn? | ≥80% recall obvious-type | **PASS** — presidio_full: EMAIL/PHONE/CCCD/URL/IP = 100%, PERSON = 66.7% (usable-with-caveat); regex-only fallback đo được: obvious 100%, PERSON 0% (chi tiết + bug presidio 2.2.364: xem entry cùng ngày) | 2026-08-24 | Có — mở rộng recognizer set tùy chỉnh (không phải regex-only) |
| S2 | Provider có honor `json_schema` response_format? | ≥9/10 calls valid | **PASS** — gemini-3-flash @ api.orimise.com/v1: **10/10 valid**, temperature=0, không retry → production mode = json_schema (sau khi sửa base_url thiếu `/v1`) | 2026-08-24 | Không |
| S3 | Embeddings API + roundtrip pgvector qua Supabase? | self-match rank #1 | **PASS** — text-embedding-3-small dims thực đo **1536 khớp hợp đồng**; insert OK vào `public._spike_vec`; self-match rank #1 cả 10 câu, sim min = 1.0; latency ~280ms/query (WAN tới ap-southeast-2); bảng toy đã drop | 2026-08-24 | Không |
| S4 | sklearn HDBSCAN cosine sane trên 200 toy vectors? | <5s, noise hợp lý | pending | | |
| S5 | LangGraph interrupt → restart → resume với AsyncPostgresSaver? | resume OK, zero duplicate side effects | pending | | |
| S6 | Parity Windows-native backend ↔ Supabase cloud end-to-end? | green | **PARTIAL green** — PostgreSQL 17.6 reachable qua session pooler từ Windows; raw psycopg roundtrip OK; WAN baseline ~253ms/query. Phần Alembic upgrade head + ORM feedbacks insert/query chạy ngay sau Phase 03 theo plan §3.4 | 2026-08-24 | Không (split-run đúng kế hoạch §3.4) |

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

## 2026-08-24 — .env người dùng lệch tên biến hợp đồng §5 → chấp nhận qua alias
- Context: Người dùng điền `backend/.env` với `DB_CONNECT_STRING` (thay `DATABASE_URL`), `EMBEDDING_DIMENSIONS` (thay `EMBEDDING_DIM=1536`), thêm `EMBEDDING_BASE_URL`/`EMBEDDING_API_KEY` riêng cho embeddings (hợp đồng §5 chỉ có `LLM_*` dùng chung). Ngữ nghĩa đều đúng: DB là Supabase **session pooler :5432** đúng quy tắc, dims=1536 khớp hợp đồng.
- Decision: Code chấp nhận CẢ bộ tên theo thứ tự ưu tiên `DATABASE_URL`→`DB_CONNECT_STRING`, `EMBEDDING_DIM`→`EMBEDDING_DIMENSIONS`; embeddings đọc `EMBEDDING_BASE_URL`/`EMBEDDING_API_KEY` nếu có rồi mới fallback `LLM_*`. Spike scripts áp dụng qua `scripts/spikes/_common.py`; Phase 03 khai báo tương ứng bằng `AliasChoices` trong class `Settings`.
- Alternatives rejected: (1) bắt người dùng đổi lại tên theo `.env.example` — ma sát không cần thiết vì ngữ nghĩa đã đúng; (2) hard-code một bộ tên duy nhất — spike S3/S6 gãy ngay trong ngày.
- Consequence: Settings class Phase 03 phải nhớ `AliasChoices` (đã ghi checklist phase); `.env.example` giữ tên chuẩn làm tài liệu. Phát hiện kèm theo: password DB chứa ký tự `@` → mọi parser connection string phải tách userinfo ở ký tự `@` CUỐI (chuẩn RFC 3986) hoặc truyền param rời cho psycopg (`scripts/spikes/_common.py::db_params`).

## 2026-08-24 — S1: Presidio builtin thiếu sót trên tiếng Việt → recognizer set tùy chỉnh (PASS sau fix)
- Context: Chạy spike S1 trên 20 mẫu fake VN–EN. Lần đầu: EMAIL 50%, PHONE 50%, PERSON 0% dù CCCD/URL/IP = 100%. Ba nguyên nhân: (a) builtin `EmailRecognizer` bỏ sót TLD dự phòng `.test`/`.example` mà chính plan §3.1 chọn làm dữ liệu giả; (b) số điện thoại có khoảng trắng (`0912 345 678`) không match vì chưa normalize trước khi match như plan chỉ định; (c) PERSON = 0% do **bug presidio-analyzer 2.2.364**: `StanzaRecognizer.__init__` forwarding kwarg `nlp_engine` lên `SpacyRecognizer.__init__` (không nhận tham số này) → TypeError, không dựng được recognizer NER builtin — trong khi stanza vi thực chất vẫn trả entity `PERSON` đúng trong nlp_artifacts.
- Decision: Giữ NGUYÊN dataset theo plan, mở rộng recognizer set: thêm `VnEmailRecognizer` (pattern email rộng), normalize dấu cách/dot giữa chữ số trước khi match VN_PHONE, tự viết `StanzaViPersonRecognizer` đọc thẳng `nlp_artifacts.entities` (workaround bug upstream). Kết quả cuối: EMAIL/PHONE/CCCD/URL/IP = **100%**, PERSON = **66.7%** usable-with-caveat (đúng kịch bản plan §3.1 — câu "Tôi là Nguyễn Văn A" là điểm yếu thật của NER vlsp). Regex-only fallback đo được để đối chiếu: obvious types 100%, PERSON 0%. **Mode production = presidio_full.**
- Alternatives rejected: (1) đổi dataset sang domain "dễ ăn" (.com/.vn) — giấu lỗi builtin, mất giá trị spike; (2) monkey-patch `StanzaRecognizer` — phụ thuộc nội bộ thư viện, vỡ khi nâng version; (3) hạ pass criterion — sai quy trình nghiệm thu.
- Consequence: Phase 06 đóng gói đúng recognizer set này (4 custom + builtin URL/IP); cần rule ưu tiên CCCD khi overlap VN_PHONE (12 số chứa 10 số con); **pin presidio-analyzer ==2.2.364** hoặc kiểm tra upstream đã fix trước khi nâng version.

## 2026-08-24 — S2: base_url relay thiếu `/v1` trong `.env`; json_schema được honor 10/10 (PASS)
- Context: Lần chạy đầu S2 toàn call 404 từ relay `api.orimise.com`. Probe GET `/models` chứng minh endpoint chuẩn là `https://api.orimise.com/v1/*` và model `gemini-3-flash` tồn tại — `.env` điền thiếu đuôi `/v1`. Tương tự `EMBEDDING_BASE_URL` bị điền dạng full-endpoint `/v1/embeddings` thay vì base `/v1` (openai SDK tự nối `/embeddings`); probe xác nhận POST `/v1/embeddings` HTTP 200, **dims=1536 khớp hợp đồng**.
- Decision: Agent sửa 2 dòng URL trong `backend/.env` về dạng base chuẩn OpenAI-compatible (`…/v1`, không đụng key/password). Sau fix S2 đạt **10/10 valid** với `response_format={"type":"json_schema", strict:true}` temperature=0, không cần retry → **mode production `llm_client.chat_structured` = json_schema**; nhánh prompt-JSON + validate + retry chỉ là fallback dự phòng Phase 07.
- Alternatives rejected: giữ URL lệch và cấu hình SDK đường dẫn riêng — lệch chuẩn OpenAI-compatible, rắc rối cho Phase 07.
- Consequence: Mọi provider sau này phải khai báo dạng base `…/v1`; người dùng cần biết `.env` đã được agent sửa 2 giá trị URL nói trên.

## 2026-08-24 — Phase 03: chốt bộ giá trị enum ai_issue_enum và sentiment_enum
- Context: Execute plan §6 chỉ định cột `ai_issue`/`sentiment` là native PG enum nhưng không liệt kê giá trị. Checklist phase 03 §3.5 yêu cầu chốt TRƯỚC khi viết migration vì native enum không có giá trị mới = phải `ALTER TYPE`.
- Decision: Chốt đúng đề xuất khởi điểm của plan §3.5 — `sentiment_enum = ('positive','negative','neutral','mixed')`; `ai_issue_enum = ('hallucination','inaccuracy','bias','safety','privacy','performance','other')`. Các enum còn lại giữ nguyên spec: `user_role(pm,operations)`, `severity_enum(low,medium,high,critical)`, `review_status(unreviewed,pending,approved,edited,rejected)`, `review_action(approve,edit,reject)`, `run_status(running,completed,failed)`, `llm_call_type(classify,embed,name_cluster,generate_insight)` — tổng **8 types** theo liệt kê §6 (bảng nghiệm thu plan 03 ghi "7" là lệch đếm; verify theo danh sách tên, không theo số).
- Alternatives rejected: mở rộng dự phòng thêm giá trị (`off_topic`, `question`…) — làm loãng taxonomy khi Phase 07 mới chính thức định nghĩa schemas/taxonomy.py; đoán sai từ đầu còn tệ hơn ADD VALUE sau này.
- Consequence: Phase 07 phải map output classifier vào đúng bộ này; cần giá trị mới → migration mới với `ALTER TYPE … ADD VALUE IF NOT EXISTS` (không phá dữ liệu). Định nghĩa Python nằm tại `backend/app/models/enums.py` — một nguồn duy nhất.

## 2026-08-24 — Phase 03: alembic `set_main_option` chết với `%` trong password percent-encoded
- Context: Password DB chứa `@` → URL chuẩn hóa phải percent-encode (`%40`). Khi env.py gọi `config.set_main_option("sqlalchemy.url", …)`, configparser interpolation của alembic coi `%` là cú pháp đặc biệt → `ValueError: invalid interpolation syntax` TRƯỚC khi nối DB.
- Decision: Bỏ hẳn `set_main_option`; env.py truyền URL thẳng từ Settings vào `context.configure(url=…)` cho offline mode, còn online mode tái dùng engine ứng dụng (`app.db.session.engine`) vốn đã mang connect_args đúng.
- Alternatives rejected: escape `%%` trước khi set — rườm rà, dễ quên ở chỗ khác; hardcode URL vào alembic.ini — tuyệt đối không (secret).
- Consequence: `sqlalchemy.url` trong alembic.ini để trống vĩnh viễn; ai sửa env.py sau này phải giữ nguyên pattern truyền URL trực tiếp. Sự cố kèm theo: lần lỗi đầu, traceback in connection string (kèm password thật) ra terminal — password đã nằm trong transcript phiên làm việc; khuyến nghị người dùng reset database password Supabase sau phiên.

## 2026-08-24 — Phase 03: Supabase session pooler (PgBouncer) strip libpq `options` → search_path của engine vô hiệu
- Context: Plan chỉ định engine `connect_args={"options": "-csearch_path=extensions,public"}`. Chạy thật qua pooler `aws-0-*.pooler.supabase.com:5432`, `SHOW search_path` trả `"$user", public, extensions` — tức startup parameter `options` bị PgBouncer bỏ qua, KHÔNG áp dụng.
- Decision: Chấp nhận hành vi mặc định của Supabase: search_path mặc định đã chứa `public` TRƯỚC `extensions` → (a) CREATE TABLE/TYPE không schema-qualify vẫn rơi vào `public` như mong muốn (xác nhận: 8 bảng + 8 enum đều ở public); (b) type `vector` vẫn resolve được vì `extensions` nằm trong path (Supabase pre-install pgvector vào schema extensions). Giữ nguyên connect_args cho trường hợp nối thẳng (bypass pooler) — vô hại.
- Alternatives rejected: schema-qualify tay mọi tham chiếu (`extensions.vector`) — rò rỉ chi tiết hạ tầng vào code/migration, khó chuyển về PG thường khi deploy VPS; SET search_path mỗi session qua event listener — thêm phức tạp không cần thiết khi default đã đúng.
- Consequence: Không phụ thuộc được vào connect_args khi đi qua pooler; mọi migration sau phải giả định search_path mặc định Supabase (`"$user", public, extensions`). Nếu ngày nào Supabase đổi default, phải quay lại mục này.


