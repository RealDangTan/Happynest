# Phase 16 — GET /api/reports/summary (báo cáo PM thuần SQL)

> **Nguồn:** [`delivery-design-spec.md`](delivery-design-spec.md) §5 P4 + §3 C4 · [`delivery-contracts.md`](delivery-contracts.md) C4 · Ngày viết: 2026-08-25 (viết sớm theo decisions cùng ngày)
> **Thứ tự pha:** P4b của [delivery-execute-plan.md](delivery-execute-plan.md) — độc lập với phase 15 về code, nhưng phần `emerging` của response CHỈ có dữ liệu sau khi phase 14 đã chạy `/clusters/run` (trước đó trả `emerging: []` là hợp lệ theo thiết kế). **Executor đọc cả spec + contracts.**

## 1 · Bối cảnh & hiện trạng (verify bằng lệnh thật khi mở phase, ghi kết quả)

```bash
cd backend
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/reports/summary   # 501 stub
uv run pytest -q                                                                   # suite xanh trước khi đụng
```

| Thành phần | Trạng thái | Việc phase này |
|---|---|---|
| `GET /api/reports/summary` | STUB 501 `admin.py:45` | Thay bằng route thật |
| Dữ liệu nguồn | 22 row demo đã classify (`run 9c6687bc`: 4 review=True, pii 4) đủ để aggregate thật | Không seed thêm |
| Migration/model mới | **Không cần** — mọi cột đã tồn tại | Task duy nhất là route + query |
| LLM | **CẤM gọi** — C4 ghi rõ thuần SQL (đệm rủi ro hết tín dụng của spec §8) | Assert bằng test không mock nào bị chạm |

## 2 · Mục tiêu pha + Non-goals

**Mục tiêu:** 1 endpoint aggregate đúng C4 field-by-field, chạy nhanh (<1s trên dataset ≤1500), không phụ thuộc LLM/embedding.

**Non-goals:** xuất CSV/PDF; chart phía BE (FE tự vẽ từ số liệu); chọn khoảng ngày tuỳ ý (chỉ 7/30/90); so sánh 2 cửa sổ (trend đã nằm ở clusters qua `growth_ratio`); endpoint báo cáo riêng cho operations role.

## 3 · Tasks

### Task 1 — Query service `services/reports.py`

**Files:** Create `backend/app/services/reports.py`

- [x] Step 1.1: Hàm `build_summary(db, days: int, now) -> dict`, **mọi aggregate tính trên cửa sổ `created_at ≥ now − days`** (event time — nhất quán với công thức trend phase 14; KHÔNG dùng `imported_at`). Các mảnh:
  - `totals`: 3 scalar query gộp 1 lượt SELECT với FILTER (WHERE riêng từng biểu thức): tổng feedback trong cửa sổ; `review_status='pending'`; `pii_detected=true`. *(thực thi: totals + 2 bộ enum gộp chung MỘT select FILTER — siết round-trip pooler)*
  - `by_severity` / `by_sentiment`: GROUP BY enum — chỉ đếm row KHÔNG NULL (row chưa classify không lọt); key là value enum đúng thứ tự contracts (`low/medium/high/critical`, `positive/neutral/negative`), nhóm thiếu số liệu vẫn ra key với `0`. *(lệch có chủ đích: sentiment thêm key `mixed` — decisions 2026-08-26)*
  - `top_categories`: `categories` là JSONB array — 1 câu SQL `text()` dùng `jsonb_array_elements_text` unnest rồi GROUP BY + ORDER BY count DESC LIMIT 10; trả `[{"category": …, "count": …}]`. *(guard `jsonb_typeof='array'` đặt TRONG lateral chống ô json-null — root cause + decisions cùng ngày)*
  - `emerging`: SELECT clusters `is_emerging OR is_spike` ORDER BY `suggested_priority DESC NULLS LAST` LIMIT 5, mỗi dòng ghép shape con của C1 (kèm `sample_feedback_ids` ≤5 tái dùng logic phase 14 — nếu hàm đó nằm private thì extract thành helper dùng chung, KHÔNG copy-paste). *(đã extract `sample_feedback_ids_by_cluster` trong clustering.py, dùng chung với GET /api/clusters)*
- [x] Step 1.2: Unit test DB-backed theo chiến lược conftest Phase 11 (fixture dọn rác theo prefix `rep-it-`): seed vài row giả lập phủ case — severity NULL bị loại, categories nhiều phần tử trùng nhau gộp đúng, cửa sổ loại row ngoài `days`. Mock **không cần** vì không có LLM; test chạm Supabase dev như các suite hiện hành. Verify: `uv run pytest tests/test_reports_service.py -q` PASS (4/4). *(pattern baseline-delta vì DB dev dùng chung có sẵn row demo trong cửa sổ; rollback fixture thay cho xoá tay)* Commit: `feat(reports): sql-only summary aggregation service`

### Task 2 — Route thay stub

**Files:** Modify `backend/app/api/routes/admin.py` (xoá stub `/reports/summary`), Create `backend/app/schemas/report.py`

- [x] Step 2.1: `GET /api/reports/summary?days=7|30|90` — param `days: Literal[7, 30, 90] = 30` (giá trị khác → FastAPI tự 422, đúng bộ lỗi chuẩn). Guard router-level `require_role("pm", "operations")` như cả router admin đang có. *(thực thi: `SummaryWindow(IntEnum)` thay Literal thuần — pydantic v2 không coerce query-string `'7'` cho Literal số; hợp đồng quan sát được không đổi, decisions 2026-08-26)*
- [x] Step 2.2: Response schema Pydantic mirror nguyên vẹn C4: `generated_at` (ISO lúc build), `window_days`, `totals{feedback_count, pending_review_count, pii_detected_count}`, `by_severity{low,medium,high,critical}`, `by_sentiment{positive,neutral,negative}`, `top_categories[]≤10`, `emerging[]≤5`. Không field nào chứa text feedback — chỉ con số, id và snippet-đã-sanitize trong emerging sample (ids thôi, đúng C1 con). *(`schemas/report.py`; by_sentiment 4 key gồm mixed)*
- [x] Step 2.3: Integration test `-m integration` (`tests/test_reports_api_integration.py`): gọi qua `client` login pm với data demo 22 row hiện hữu → assert shape C4 field-by-field + tổng `by_severity == feedback_count` khi không còn row NULL (hoặc ≤ khi có) + `days=7` cho kết quả khác `days=90` trên dataset có spread ngày. Verify: `uv run pytest -m integration tests/test_reports_api_integration.py -v` PASS (4/4). Commit: `feat(reports): summary endpoint replaces 501 stub`

### Task 3 — Docs + evidence

**Files:** Modify `docs/api-notes.md` (dòng 501 → 200 + role pm/operations); Create `docs/evidence/reports-summary-sample.json`

- [x] Step 3.1: Chạy live trên data demo, lưu JSON response mẫu làm evidence chương kết quả + tài liệu tham chiếu FE khi dựng dashboard P4. *(`docs/evidence/reports-summary-sample.json`, days=30: totals 17/1/4, top-1 "hiệu năng", emerging rỗng — đúng thiết kế vì chưa có cụm)*
- [x] Step 3.2: Commit: `docs(reports): summary api notes + sample evidence` *(api-notes.md đã bị bỏ theo decisions OQ-1 2026-08-26 → cập nhật docs/api-checklist.md thay thế)*

## 4 · Acceptance criteria + Evidence cần chụp

- [ ] Shape response khớp C4 100% field-by-field; thiếu dữ liệu vẫn 200 (mảng rỗng/key 0) — không bao giờ lỗi vì "chưa có cụm"
- [ ] `days` sai giá trị → 422; không token → 401; role sai → 403 (test auth tái dùng pattern suite hiện có)
- [ ] Không một call LLM nào phát sinh (assert qua việc không import/mock gì llm_client trong service)
- [ ] Aggregate nhất quán: mọi con số đếm được đối chiếu lại bằng 1 câu SQL tay trên Supabase Studio cùng cửa sổ
- [ ] Thời gian phản hồi <1s local (log duration nếu quá — dataset 22 row phải tức khắc)
- [ ] **Evidence luận văn:** JSON mẫu + screenshot dashboard FE (P4) hiển thị đúng số liệu đối chiếu với Supabase Studio

## 5 · Blocker rule

Unnest JSONB vướng driver/phiên bản PG trên pooler → hạ cấp: kéo `categories` về Python và aggregate Counter (vẫn không-LLM, ghi entry decisions "thuần SQL" hạ xuống "aggregate client-side cho 1 mảnh"). Lỗi khác sau nỗ lực hợp lý → STOP, entry decisions, chuyển việc độc lập khác của P4/P5.
