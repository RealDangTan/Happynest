# Phase 11 — Test Suite hoàn thiện

> **Nguồn:** execute-plan §2 (IN-SCOPE mục 13) + §9 DoD mục 9
> **Trạng thái:** ✅ 2026-08-25 · **Blocked by:** Phase 04–09
> **Commit mẫu:** `test(suite): conftest strategy, markers, green unit + integration`

## 1 · Mục tiêu

Suite pytest đáng tin: unit chạy không cần PG/không network (LLM mocked), integration đánh dấu rõ chỉ chạy khi PG thật. Đây là phase "chà nhám" — không viết feature mới.

## 2 · Việc CON NGƯỜI

- Không có.

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 Chiến lược DB trong tests (`tests/conftest.py`)
- **Ràng buộc kỹ thuật:** native PG enum + cột `vector` → sqlite KHÔNG dùng được. Mọi test đụng DB cần DB thật — khuyến nghị **free project Supabase thứ 2** (được 2 free projects/account) làm test DB để integration test không xóa data demo; cần internet.
- `conftest.py`:
  - đọc `TEST_DATABASE_URL` env, fallback `DATABASE_URL`;
  - fixture session-scoped: tạo schema sạch mỗi lần chạy test (truncate bảng theo thứ tự FK hoặc drop/create schema);
  - fixture function-scoped `db_session` rollback sau mỗi test;
  - fixture `client` = TestClient với dependency_overrides cho `get_db` và override settings;
  - fixture `fake_llm` / `fake_embedder` deterministic (seed cố định), inject qua monkeypatch vào classifier/runner;
  - **Nếu DB không reachable (mất mạng / project pause):** pytest.skip toàn bộ test DB với message rõ ("Supabase not reachable") — unit thuần vẫn chạy.
- Đăng ký marker trong `pyproject.toml`:
  ```toml
  [tool.pytest.ini_options]
  markers = ["integration: requires real PostgreSQL (Supabase) + internet"]
  addopts = "-m 'not integration'"   # mặc định bỏ integration; bật bằng -m integration
  ```

### 3.2 Rà từng file test tồn tại từ các phase
| File | Phủ | Trạng thái |
|---|---|---|
| `test_auth.py` | login/me/403 | từ Phase 04 · ✅ 2026-08-25 — bổ sung marker `integration` (từng thiếu từ Phase 04, xem decisions.md) |
| `test_presidio_service.py` | recall + placeholder + no-leak | từ Phase 06 · ✅ unit chạy local stanza offline; wiring class đã integration |
| `test_ingest.py` | POST/CSV/filter/raw-flag | từ Phase 05 · ✅ integration, cleanup prefix |
| `test_classifier_unit.py` | fallback chain + HITL formula | từ Phase 07 · ✅ mock trọn (fake client + sqlite sink + tracing off) |
| `test_classifier_idempotency.py` | crash/resume không trùng | từ Phase 09 · ✅ integration + fakes bắt buộc autouse |
| `test_embedder_unit.py` | batch/dim/log | từ Phase 08 · ✅ fake client + recorder factory |
| `test_similarity_roundtrip.py` | `@pytest.mark.integration` | từ Phase 08 · ✅ đã sửa auth Phase 09 |

Việc phase này: chạy toàn bộ, sửa flaky, đảm bảo KHÔNG test nào gọi network thật (grep mock coverage), không test nào phụ thuộc thứ tự chạy.
→ Đã xong 2026-08-25: audit grep xác nhận unit suite không có đường ra network; suite xanh cả 2 chế độ; lệch kế hoạch (auto-wipe → skip-guard + TEST_DATABASE_URL) ghi decisions.md cùng ngày.

### 3.3 Ma trận chạy chuẩn (ghi vào README ở Phase 12)
```powershell
uv run pytest                    # unit-only khi chưa bật marker ngược
uv run pytest -m integration     # Supabase test project phải active + internet
```
Kỳ vọng DoD mục 9: "pytest green except integration marks skipped without PG; integration pass against real PG".

## 4 · Tiêu chí nghiệm thu (map DoD mục 9)

| DoD | Bằng chứng |
|---|---|
| Unit suite xanh không cần PG/network | output pytest |
| Integration xanh trên PG thật | output pytest -m integration |
| Không network call trong unit | review conftest/fakes |

## 5 · Lệnh kiểm chứng

```powershell
cd backend
# 1. Không mạng / chưa có TEST_DATABASE_URL: unit vẫn xanh, integration skip
uv run pytest -q
# 2. Supabase test project active + có internet:
uv run pytest -q -m integration
uv run pytest -q   # tổng
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| Test nào bắt buộc network thật | Chuyển sang integration marker hoặc fake tốt hơn |
| Flaky do thứ tự/timeout | Fix gốc (fixture độc lập), không thêm sleep bừa |
| Muốn sqlite cho unit nhanh | KHÔNG khả thi vì native enum/vector — nếu ai đề xuất, dẫn entry này làm lý do từ chối |
