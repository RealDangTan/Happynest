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
| S4 | sklearn HDBSCAN cosine sane trên 200 toy vectors? | <5s, noise hợp lý | **PASS** — scikit-learn 1.9.0 (ad-hoc `uv run --with`, KHÔNG pin production); cả 3 cấu hình min_cluster_size {5,10,15} tìm đúng 3 cụm, noise 7.5–8.5% (ground truth 10%), fit 0.018–0.108s/cấu hình, tổng **0.165s** ≪ 5s; FutureWarning nhỏ về tham số `copy` (sklearn 1.10 đổi default) | 2026-08-24 | Không |
| S5 | LangGraph interrupt → restart → resume với AsyncPostgresSaver? | resume OK, zero duplicate side effects | **PASS** — `interrupt_before=["b"]` dừng đúng trước node B (next=['b'], side effect 0); process THOÁT hẳn; tiến trình MỚI resume `ainvoke(None)` chạy đủ a→b→c, side effect đúng **1 lần**; setup() idempotent tạo đúng 4 bảng checkpoint khớp filter Alembic env.py; resume ~9s (WAN Supabase). Quirks Windows/API xem entry cùng ngày | 2026-08-24 | Không |
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

## 2026-08-24 — Phase 07: thêm cột `safety_issue` vào bảng `feedbacks`
- Context: Output schema của classifier v1 có field `safety_issue: bool` (cần cho công thức HITL), nhưng execute plan §6 không định nghĩa cột tương ứng trên `feedbacks`. Plan phase 07 §3.1 đã phân tích: giấu flag này trong `rationale` hay suy ra từ categories đều là mất dữ liệu có cấu trúc — `compute_requires_human_review` cần truy vấn được trực tiếp.
- Decision: Thêm cột `safety_issue BOOLEAN NOT NULL DEFAULT false` vào `feedbacks` bằng Alembic revision `0004` (nhỏ, reversible). Model `Feedback` cập nhật đồng bộ. Giá trị do classifier điền lúc classify; feedback chưa classify giữ default `false`.
- Alternatives rejected: (1) parse lại từ `categories`/`rationale` khi cần — logic rải rác, mất dữ liệu cấu trúc, không index/query được; (2) tái dùng cột `pii_detected` với ngữ nghĩa rộng hơn — sai ngữ nghĩa, hai nguồn độc lập trong công thức HITL phải tách bạch; (3) bỏ field khỏi output schema — vi phạm locked decision HITL trigger vốn có mệnh đề `safety_issue`.
- Consequence: Lệch §6 một cột — mọi tài liệu mô tả schema phải phản ánh từ nay; migration chạy trên Supabase dev ngay trong phase này.

## 2026-08-24 — Phase 07: chốt cách dùng ngưỡng `HIGH_SEVERITY_CONFIDENCE_REVIEW_BELOW`
- Context: Env contract §5 khai báo `HIGH_SEVERITY_CONFIDENCE_REVIEW_BELOW=0.75` nhưng locked decision HITL chỉ dùng `confidence<0.60` chung mọi severity — ngưỡng 0.75 không có chỗ dùng, nguy cơ thành biến chết. Plan phase 07 §3.4 đề xuất một cách dùng và yêu cầu chốt trước khi code.
- Decision: Công thức HITL đầy đủ (mở rộng locked formula, giữ nguyên 4 mệnh đề cũ):
  `requires_human_review = severity=="critical" OR safety_issue OR pii_detected OR confidence < CLASSIFY_CONFIDENCE_REVIEW_BELOW OR (severity in {high, critical} AND confidence < HIGH_SEVERITY_CONFIDENCE_REVIEW_BELOW)`
  Ý nghĩa: feedback nghiêm trọng (high/critical) nhưng model thiếu tự tin (<0.75) cũng bắt qua người xem, dù vẫn trên ngưỡng 0.60 chung.
- Alternatives rejected: (1) xóa biến khỏi env contract — mất khả năng tune ngưỡng riêng cho severity cao mà không đụng code; (2) áp ngưỡng 0.75 cho mọi severity — quá tay, review queue phình với cả low/medium; (3) để nguyên không dùng — biến chết trong config là nợ kỹ thuật + điểm trừ khi bảo vệ.
- Consequence: Mọi test HITL phải phủ thêm nhánh thứ 5 này; đổi ngưỡng sau này chỉ cần sửa `.env`, không đổi code.

## 2026-08-24 — S4/S5: quirks scikit-learn ad-hoc + AsyncPostgresSaver trên Windows/Supabase (đều PASS)
- Context: Spike muộn phase 10 chạy HDBSCAN toy (S4) và interrupt/resume LangGraph với checkpoint Supabase (S5). Ba quirk phát hiện khi chạy thật cần ghi lại cho phase clustering và phase HITL graph sau này.
- Decision:
  (1) **S4 — scikit-learn chỉ spike-only**: cài ad-hoc qua `uv run --with scikit-learn` (resolve ra **1.9.0**, scipy đi kèm), KHÔNG đưa vào pyproject; production clustering sẽ chốt lib riêng khi làm (HDBSCAN cosine sane: 3/3 cụm, noise ~8%, 0.165s). Lưu ý sklearn 1.10 sẽ đổi default tham số `copy` trong HDBSCAN (FutureWarning hiện tại, vô hại).
  (2) **S5 — psycopg async trên Windows cần SelectorEventLoop**: `asyncio.run()` mặc định ProactorEventLoop → `psycopg.InterfaceError` ngay khi `AsyncPostgresSaver.from_conn_string`. Fix: `asyncio.run(..., loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))`. Phase HITL sau phải mang pattern này vào app.
  (3) **S5 — saver.conn là AsyncConnection đơn, row_factory=dict_row**: `from_conn_string` KHÔNG trả pool — `saver.conn.cursor()` dùng trực tiếp; mọi query tay trên connection này trả dict thay vì tuple.
- Alternatives rejected: (1) pin scikit-learn vào pyproject "cho chắc" — vi phạm rule §10.7 (ngoài danh sách §1) trong khi chưa chọn lib clustering chính thức; (2) chạy S5 bằng PostgresSaver sync — lệch câu hỏi spike (async runtime của FastAPI); (3) tự quản state machine ngay từ đầu bỏ qua spike — mất bằng chứng resume-no-duplicate cho khóa luận.
- Consequence: Bảng `_spike_side_effects` + 4 bảng checkpoint đã DROP sạch khỏi Supabase dev sau đo (verify information_schema trống); production graph vẫn ngoài scope đến phase HITL — khi đó setup() sẽ tái tạo 4 bảng checkpoint (idempotent) và Alembic vẫn ignore nhờ filter sẵn có.

## 2026-08-24 — Phase 03: Supabase session pooler (PgBouncer) strip libpq `options` → search_path của engine vô hiệu
- Context: Plan chỉ định engine `connect_args={"options": "-csearch_path=extensions,public"}`. Chạy thật qua pooler `aws-0-*.pooler.supabase.com:5432`, `SHOW search_path` trả `"$user", public, extensions` — tức startup parameter `options` bị PgBouncer bỏ qua, KHÔNG áp dụng.
- Decision: Chấp nhận hành vi mặc định của Supabase: search_path mặc định đã chứa `public` TRƯỚC `extensions` → (a) CREATE TABLE/TYPE không schema-qualify vẫn rơi vào `public` như mong muốn (xác nhận: 8 bảng + 8 enum đều ở public); (b) type `vector` vẫn resolve được vì `extensions` nằm trong path (Supabase pre-install pgvector vào schema extensions). Giữ nguyên connect_args cho trường hợp nối thẳng (bypass pooler) — vô hại.
- Alternatives rejected: schema-qualify tay mọi tham chiếu (`extensions.vector`) — rò rỉ chi tiết hạ tầng vào code/migration, khó chuyển về PG thường khi deploy VPS; SET search_path mỗi session qua event listener — thêm phức tạp không cần thiết khi default đã đúng.
- Consequence: Không phụ thuộc được vào connect_args khi đi qua pooler; mọi migration sau phải giả định search_path mặc định Supabase (`"$user", public, extensions`). Nếu ngày nào Supabase đổi default, phải quay lại mục này.

## 2026-08-24 — Phase 08 thực thi khi Phase 05/07 chưa làm → dựng scaffold tối thiểu
- Context: Plan 08 tham chiếu `routes/feedback.py` stub `/similar` (plan 05 tạo), `tracing.py::write_llm_call_log` và "pattern như llm_client" (plan 07 tạo) — chưa tồn tại vì phase 04–07 chưa thực thi; bảng phụ thuộc 00-index lại chỉ ghi 08 blocked-by 03 (lệch giữa graph và văn bản plan). Repo cũng chưa có `app/services/`, `tests/`. Owner đã chọn phương án trước khi code.
- Decision: Dựng đúng đủ scope plan 08 kèm scaffold tối thiểu cho phần phụ thuộc: (a) `app/services/tracing.py` chỉ chứa writer `write_llm_call_log(...)` ĐÚNG chữ ký contract 07 §3.2 — phần Langfuse client/span để 07 bổ sung; (b) `app/api/routes/feedback.py` CHỈ chứa `GET /api/feedbacks/{id}/similar`, chưa guard role vì `get_current_user` thuộc 04 — kèm `app/api/deps.py` mới với `get_db`; (c) test infra lần đầu: `backend/tests/` + marker `integration` đăng ký trong pyproject, mặc định `-m 'not integration'` để `uv run pytest` = unit suite đúng như AGENTS.md mô tả; (d) integration test nối `TEST_DATABASE_URL` nếu env có (ý tưởng project-test-thứ-2 từ entry v1.1), fallback về `DATABASE_URL` dev — insert/cleanup row riêng bằng UUID, không đụng data thật.
- Alternatives rejected: (1) hoãn route `/similar` sang sau phase 05 — phase 08 không nghiệm thu trọn DoD mục 6 (/similar trả neighbors cosine); (2) đảo thứ tự làm 04→07 rồi mới 08 — ngược yêu cầu owner muốn hoàn thành 08 trong phiên này.
- Consequence: Phase 05 phải MỞ RỘNG `feedback.py` (thêm CRUD ingestion + wire auth) thay vì viết lại; phase 07 mở rộng `tracing.py` (Langfuse wrapper + flush lifespan); `/similar` tạm thời công khai ở dev — chấp nhận vì DB chỉ chứa fake data; mọi phase sau dùng chung markers/conftest đã dựng.

## 2026-08-24 — Phase 04: token nhận từ cookie httpOnly HOẶC header Bearer song song
- Context: Plan 04 §6 đã dự liệu "Swagger UI không authorize được vì cookie-based" và cho phép "thêm cơ chế chấp nhận `Authorization: Bearer` song song kèm entry nhỏ". Cookie httpOnly là cơ chế thật cho Next.js proxy, nhưng Swagger UI, curl và pytest cần đường Bearer.
- Decision: `deps.OAuth2PasswordBearerWithCookie` kế thừa `OAuth2PasswordBearer`: đọc cookie `access_token` TRƯỚC, không có thì rơi về hành vi gốc (header Bearer, tự 401 kèm WWW-Authenticate). `POST /api/auth/token` vẫn trả `TokenOut{access_token}` trong body để test/Swagger lấy token. Hai nguồn cùng tồn tại vĩnh viễn, cookie ưu tiên.
- Alternatives rejected: (1) chỉ cookie — Swagger "Authorize" chết, mọi curl/test phải quản lý cookie jar thủ công; (2) chỉ Bearer — mất ý nghĩa httpOnly (XSS đọc được token qua JS); (3) header dạng `access_token=<jwt>` trong cookie rồi strip tiền tố "Bearer " — dư một lớp biến đổi vô ích.
- Consequence: Route guard (`get_current_user`, `require_role`) không phân biệt nguồn token; Phase 11 viết test có thể chọn cookie hoặc header tuỳ tiện. JWT HS256 key = SECRET_KEY (đã enforce: prod thiếu key thật sẽ từ chối khởi động, dev cảnh báo).




## 2026-08-24 — Phase 05: guard router-level che luôn /similar; test ingest dùng marker `integration`; external_ref không dedup
- Context: (1) Entry Phase 08 chấp nhận `/similar` tạm công khai ở dev; docstring file route hẹn Phase 05 "wire auth cho toàn bộ router". (2) Phase 08 đăng ký marker pytest `integration` + `addopts -m 'not integration'` SAU khi plan 05 viết lệnh verify `uv run pytest tests/test_ingest.py` — chạy đúng nguyên văn sẽ bị deselect hết. (3) Cột `external_ref` không có unique constraint (§6), import cùng file 2 lần tạo bản sao.
- Decision: (1) Gắn `dependencies=[Depends(require_role("pm","operations"))]` ở TẦNG ROUTER feedback — mọi endpoint kể cả `/similar` yêu cầu auth từ nay; (2) `tests/test_ingest.py` đánh `pytestmark = pytest.mark.integration`, verify bằng `uv run pytest tests/test_ingest.py -m integration`; test tự dọn row qua fixture (id + tiền tố external_ref `fixture20-`/`badcsv-`/`listtest-`) để không để rác trong DB dev dùng chung; (3) giữ nguyên append-only không dedup — trách nhiệm chống nhân bản thuộc về người gọi (CLI/API), phù hợp scope thesis.
- Alternatives rejected: (1) guard từng endpoint riêng — dễ sót endpoint mới thêm sau này; (2) bỏ marker cho ingest test để khớp chữ plan — phá quy ước unit/integration vừa thiết lập, `uv run pytest` mặc định sẽ đòi internet+DB thật; (3) unique constraint trên external_ref — nguồn ngoài có thể tái sử dụng ref hợp lệ, cấm cứng gây fail import oan.
- Consequence: `/similar` không còn gọi được vô danh (thay đổi so với acceptance Phase 08 — cập nhật test phía đó nếu có); ai chạy test ingest phải nhớ `-m integration`; import CSV trùng file trong DB dev phải dọn tay hoặc đổi ref.

## 2026-08-24 — Phase 06: regex VN_PHONE dùng lookaround; FeedbackOut thêm pii_detected; sanitize pass-through thay NULL
- Context: (1) Regex VN_PHONE của plan không có lookaround nên khớp được cả 10 số con BÊN TRONG CCCD 12 số (ghi chú chồng lấn S1); cách S1 dùng normalize + map offset lại phức tạp. (2) Test wiring cần đọc `pii_detected` qua API nhưng FeedbackOut của Phase 05 không liệt kê trường này. (3) Sau wiring, test Phase 05 khẳng định `sanitized_content is None` cho text sạch — sai với hành vi mới.
- Decision: (1) `_VN_PHONE_REGEX = (?<!\d)(?:\+84|0)[ .-]?(?:3|5|7|8|9)(?:[ .-]?\d){8}(?!\d)` — lookaround chặn khớp trong dãy số dài hơn, đồng thời nhận luôn dạng có space/dot/dash giữa chữ số ("0912 345 678") mà KHÔNG cần bước normalize + map offset như S1; CCCD giữ `\b\d{12}\b` score 0.9. (2) Thêm `pii_detected: bool` vào FeedbackOut — metadata thuần, hữu ích cho badge UI, không rò PII. (3) Text sạch → `sanitized_content == raw_content`, `pii_detected=false` (pass-through), cập nhật assertion Phase 05 theo hành vi mới; row cũ NULL vẫn được `backfill_sanitization.py` xử lý.
- Alternatives rejected: (1) hậu-lọc bỏ phone nằm trong span CCCD sau analyze — hai lớp logic cho điều regex đã giải được; (2) giấu pii_detected khỏi API — mất signal HITL/UI và mâu thuẫn tinh thần DoD mục 4 (sanitized visible mặc định); (3) giữ sanitized_content=NULL cho text sạch — gây hai ngữ nghĩa "chưa sanitize" vs "sạch" khó phân biệt khi query.
- Consequence: recognizer VN_PHONE không còn false-positive trên CCCD/OTP-dài (assert regression trong test_presidio_service); mọi consumer của FeedbackOut nhận thêm 1 field (backward-compatible); engine stanza vi+en thường trú ~1GB RAM trong process app (đã đo S1, chấp nhận theo plan §2).

## 2026-08-25 — Phase 09: resume CÙNG run; marker "đã xử lý" = categories NOT NULL; mở rộng classify_feedback; sửa test /similar bể auth từ Phase 05
- Context: (1) Plan 09 §3.3 để mở "Gọi lại run_analysis (run mới hoặc resume cùng run — chọn 1 cách, ghi rõ)". (2) Runner cần mốc nhận biết item ĐÃ xử lý để resume không classify trùng. (3) `llm_call_logs` có sẵn cột feedback_id/analysis_run_id nhưng `classify_feedback` chưa truyền qua. (4) Chạy full integration lần ĐẦU kể sau Phase 05: 5 test `/similar` (Phase 08) fail 401 vì guard router-level Phase 05 che luôn endpoint này nhưng suite đó không được chạy lại từ lúc ấy.
- Decision: (1) **Resume CÙNG run** — gọi lại `run_analysis(run_id)` trên run đang running|failed; predicate row-chưa-xử-lý = `analysis_run_id IS NULL OR (analysis_run_id = :run_id AND categories IS NULL)` → 1 row run = 1 lô logic, processed_count monotonic xuyên crash, audit trail gọn. (2) Marker "đã xử lý" là `categories IS NOT NULL`: classifier luôn ghi categories (≥1 nhãn) trong CÙNG commit với mọi label khác nên all-or-nothing đáng tin; item lỗi ở bước EMBED (đã có labels) KHÔNG được nhặt lại khi resume — đúng plan "đã claim nên không retry". Item lỗi item-level (LLMStructureError/EmbeddingDimError/APIError) bỏ qua trong lượt; >50% batch lỗi → dừng sớm status failed (fallback §6); crash ngoài danh sách → top-level đánh dấu failed rồi nuốt (BackgroundTasks không giết process). (3) `classify_feedback` thêm kwargs `feedback_id`/`analysis_run_id` passthrough vào chat_structured — backward-compatible. (4) Sửa `test_similarity_roundtrip` thêm fixture `ops_headers` (Bearer operations role) cho mọi call. Kèm theo: runner hoàn tất sạch sau resume → `error=NULL` (chỉ giữ summary lỗi item-level của lượt hiện tại).
- Alternatives rejected: (1) Tạo run mới khi resume — tiến độ chia đôi 2 row run, total snapshot sai, và item bị claim-bởi-run-cũ-rồi-crash-trước-khi-xử-lý sẽ LỘ vĩnh viễn (không run mới nào nhặt được). (2) Marker bằng `embedding IS NOT NULL` — item lỗi embed sẽ bị classify LẠI vô ích, đốt tokens. (3) Nới/bỏ guard cho test cũ pass — đi ngược hardening Phase 05.
- Consequence: Muốn "chạy tiếp" một run fail giữa chừng hiện phải gọi `run_analysis(run_id)` trực tiếp (CLI/script) vì POST luôn tạo run mới — chấp nhận cho quy mô thesis, đã ghi rõ trong docstring module job; `llm_call_logs` từ nay trace đủ theo run; suite integration xanh trọn bộ 19/19.
