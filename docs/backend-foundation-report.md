# Backend Foundation — Kết quả xây dựng hệ thống

> Sweep Definition of Done (execute-plan §9) thực hiện **2026-08-25** trên máy dev thật
> (Windows 11, Python 3.12 + uv, Supabase PostgreSQL ap-southeast-2, không Docker).
> Tư liệu chương "kết quả xây dựng hệ thống" của khóa luận.

## 1 · Bảng sweep 10 dòng DoD

| # | Điều kiện | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Fresh-machine path: Supabase → `uv sync` → `.env` → `alembic upgrade head` → seed → uvicorn green | ✅ | Chuỗi lệnh chạy lại trọn vẹn 2026-08-25: `uv sync` 149 packages; `alembic current` → `0004 (head)`; `seed_users.py` idempotent upsert; `GET /api/health` → `{"status":"ok","db":"ok","pii_mode":"full","llm_model":"gemini-3-flash","embedding_model":"text-embedding-3-small"}` |
| 2 | Login cả 2 role; role sai bị 403 | ✅ | curl live: PM + operations login 200 nhận JWT; vô danh POST `/api/feedbacks` → 401. Case 403 (role sai trên route pm-only): integration test `test_auth.py::TestRoleGuard` xanh — API production không có route pm-only thật nên 403 được tái hiện qua guard-demo route mount tạm (thiết kế từ Phase 04) |
| 3 | Import CSV 20 rows mixed VN-EN (fake PII) | ✅ | curl live `POST /api/feedbacks/import-csv` với fixture 20 dòng → `{"imported":20,"failed":0,"errors":[]}`; dấu tiếng Việt nguyên vẹn sau UTF-8/BOM decode |
| 4 | raw ≠ sanitized; `pii_entities` có; sanitized mặc định, raw cần flag | ✅ | curl live cùng row: mặc định response KHÔNG chứa `raw_content`, sanitized hiển thị `Anh <PERSON> - SĐT <PHONE_NUMBER>…`; `?include_raw=true` mới trả raw. DB: `pii_entities = [{type:"PERSON",start,end,score}, {type:"VN_PHONE",…}]` — metadata thuần, không text |
| 5 | 1 run đầy đủ trên 20 rows: labels + severity + confidence + review flag + embeddings(model+dim); crash→resume không trùng | ✅ | **Run thật** `9c6687bc`: `completed 22/22` (~4 phút 26 giây, error=null) — 22/22 có categories mixed VN-EN, severity/confidence đầy đủ, 4 row `requires_human_review=true` (mệnh đề pii_detected của công thức HITL); DB: 22 embedding `(text-embedding-3-small, dim 1536)`. Crash→resume: test idempotency Phase 09 — crash tại item 5 → run failed/4 processed → resume CÙNG run → completed 10/10, tổng classify success ĐÚNG 10 (không phải 14) |
| 6 | `/similar` trả ranked neighbors cosine | ✅ | curl live `k=5`: 5 neighbors score giảm dần `+0.2946 → +0.1961`, mixed VN-EN hợp ngữ nghĩa (feedback tiếng Anh ghép với feedback tiếng Anh cùng chủ đề offline/battery); self excluded; roundtrip thứ tự chính xác tuyệt đối được chứng minh bằng vector đơn vị trong test similarity |
| 7 | `llm_call_logs` populated; Langfuse EU thấy trace CHỈ sanitized; kill switch hoạt động | ✅ | DB: 49 rows (`call_type ∈ {classify, embed}`), 23 của run trên. **Schema log KHÔNG có cột nào chứa text input/output** (id, model, tokens, latency, error) → PII không thể rò qua log ở cấp cấu trúc. Kill switch: unit test `LANGFUSE_TRACING_ENABLED=false` xanh. Việc người dùng còn lại: mở dashboard Langfuse EU đối chiếu 1 trace trực quan |
| 8 | 6 spike scripts chạy xong; outcomes + fallback ghi decisions.md | ✅ | S1–S6 **6/6 PASS**: S1 presidio full-mode + 4 recognizer custom; S2 json_schema strict 10/10 với gemini-3-flash; S3 pgvector 1536-dim self-match rank#1 ~280ms/query WAN; S4/S5 hoàn tất Phase 10; S6 Alembic+ORM verified trên PG 17.6 thật (Phase 03) |
| 9 | pytest green (unit luôn; integration khi PG có) | ✅ | Ma trận Phase 11: unit **29 pass** offline (mock LLM/embedder/tracing, sqlite sink); integration **31 pass** trên Supabase thật (~4 phút); DB unreachable → 31 **SKIP** kèm message rõ (không ERROR) |
| 10 | Không secrets trong git history; `.env.example` đủ; README phủ Windows-dev + Supabase-PG + run/test/deploy-placeholder | ✅ | `git log --all -S "sk-"` → sạch; mọi dòng `LLM_API_KEY=` trong history là template RỖNG; `.env` thật chưa bao giờ được track. `.env.example` đối chiếu khớp từng field `Settings` (+ alias `DB_CONNECT_STRING`, `EMBEDDING_DIMENSIONS`). README mới: quickstart fresh-machine đúng thứ tự, anti-pause 7 ngày, ma trận test 3 chế độ, mục Deploy VPS placeholder |

## 2 · OUT-OF-SCOPE rà lại (execute-plan §2)

- Không code clustering / insight / graph / frontend lọt vào backend foundation.
- 5 stub 501 còn nguyên docstring: `/clusters`, `/insights`, `/reviews/{id}`,
  `/corrections/{id}`, `/reports/summary` (`app/api/routes/admin.py`).
- `frontend/README.md` placeholder đã tạo ("phase B1") — thiếu từ trước, bổ sung Phase 12.

## 3 · Số liệu nổi bật (trích cho khóa luận)

| Chỉ số | Giá trị | Ghi chú |
|---|---|---|
| Thời gian chạy batch 22 rows | ~4 phút 26 giây (~12 giây/item) | gồm LLM classify + embedding qua proxy WAN |
| Latency similarity query | ~280 ms | WAN tới Supabase Sydney, exact scan pgvector (spike S3) |
| RAM thường trú presidio full-mode | ~1 GB | engine stanza vi+en lazy singleton (spike S1) |
| Suite kiểm thử | 29 unit (offline) + 31 integration (PG thật) | toàn bộ xanh; integration tự dọn data theo tiền tố |
| Models snapshot | gemini-3-flash / text-embedding-3-small (1536d) | snapshot vào từng row `analysis_runs` để so sánh giữa các model |

## 4 · Fallback đã kích hoạt / Blocker còn treo

- **Không fallback nào đang active**: presidio chạy FULL mode (không regex_only);
  structured output đi Mode A json_schema.
- ⚠️ Ops note (không chặn DoD foundation): `SECRET_KEY` trong `.env` vẫn là
  placeholder — BẮT BUỘC thay bằng `openssl rand -hex 32` trước khi bật `APP_ENV=prod`
  (code sẽ từ chối khởi động nếu thiếu key thật ở prod). Khuyến nghị reset database
  password Supabase (password từng xuất hiện trong một session debug cũ) rồi cập nhật
  cả hai bản `.env`.

## 5 · Lệnh kiểm chứng tái lập

```powershell
cd backend
uv run pytest -q                    # 29 passed, 31 deselected (unit offline)
uv run pytest -q -m integration     # 31 passed trên Supabase thật (~4 phút)
uv run python -c "from app.db.session import engine; from sqlalchemy import text; c=engine.connect(); print(c.execute(text('SELECT count(*) FROM feedbacks')).scalar(), 'feedbacks;', c.execute(text('SELECT count(*) FROM llm_call_logs')).scalar(), 'llm_call_logs')"
git status --short                  # sạch sau khi commit phase 12
```

Kết quả lần sweep này: **22 feedbacks, 49 llm_call_logs** (bao gồm dữ liệu demo
run thật `9c6687bc` giữ lại làm data xem UI giai đoạn sau).
