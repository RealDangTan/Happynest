# Evidence — HITL checkpoint sống sót restart (kill → restart → resume)

> Phase 13 (plan `13-hitl-langgraph.md` §3.6.1) · Bằng chứng số 1 cho chương
> kết quả luận văn: checkpoint LangGraph trên Supabase giúp review flow tiếp
> diễn sau khi process chết GIỮA interrupt và resume — không mất state,
> KHÔNG nhân bản dòng log.
>
> Cơ sở lý thuyết: spike S5 (decisions.md 2026-08-24) đã chứng minh nguyên lý
> trên 2 tiến trình toy; thủ tục dưới đây chứng minh trên API production thật.

## Điều kiện trước khi chụp

- Server dev chạy được: `cd backend && uv run uvicorn app.main:app --reload`
  (log phải thấy `checkpoint saver setup OK`).
- Supabase dev reachable; user pm/operations login được.
- 2 cửa sổ terminal + Supabase Studio (bảng SQL).

## Thủ tục chụp

### Bước 0 — Seed 1 feedback pending

```bash
# login lấy token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/token \
  -d "username=pm@thesis.local&password=<pass>" | jq -r .access_token)

# tạo feedback sẽ đủ điều kiện HITL sau khi classify
curl -s -X POST http://127.0.0.1:8000/api/feedbacks \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"source":"evidence","content":"Tôi là Nguyễn Văn A, số 0900123456, app bị lỗi nặng","external_ref":"hitl-evidence-1"}'
```

Chạy analysis run để classify (PII detected ⇒ `requires_human_review=true` ⇒
`review_status='pending'`):

```bash
RUN=$(curl -s -X POST http://127.0.0.1:8000/api/analysis/runs \
  -H "Authorization: Bearer $TOKEN" | jq -r .run_id)
# chờ vài giây rồi xem progress
curl -s http://127.0.0.1:8000/api/analysis/runs/$RUN -H "Authorization: Bearer $TOKEN"
```

Ghi lại `feedback_id` của row vừa classify (Supabase Studio:
`SELECT id, external_ref, review_status FROM feedbacks WHERE external_ref='hitl-evidence-1';`
— kỳ vọng `pending`). **[Ảnh 1: kết quả SQL]**

### Bước 1 — Gây ra interrupt rồi KILL process

```bash
curl -s -X POST http://127.0.0.1:8000/api/reviews/<feedback_id> \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"reject","reason":"spam"}'
```

Request này sẽ treo vài chục giây (graph ghi checkpoint qua WAN): **ngay khi
log server in `hitl hitl-<feedback_id>: thread mới — invoke tới interrupt.`
và request chưa trả về → Ctrl+C kill server** (đúng cửa sổ giữa interrupt và
resume). **[Ảnh 2: log phiên 1 dừng ở invoke tới interrupt]**

Kiểm chứng state ĐÃ nằm trên Postgres (không phụ thuộc process):

```sql
SELECT thread_id FROM checkpoints WHERE thread_id = 'hitl-<feedback_id>';
SELECT count(*) FROM human_reviews;   -- kỳ vọng CHƯA có dòng cho feedback này
```

**[Ảnh 3: thread tồn tại trong checkpoints, human_reviews còn trống]**

### Bước 2 — Khởi động lại server, resume cùng request

Khởi động lại uvicorn (tiến trình MỚI — state chỉ còn trên Postgres), gọi lại
ĐÚNG body cũ:

```bash
uv run uvicorn app.main:app --port 8000
curl -s -X POST http://127.0.0.1:8000/api/reviews/<feedback_id> \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"reject","reason":"spam"}' | jq .
```

Kỳ vọng: **200** với `"review_status": "rejected"` (server tự nhận diện thread
đang đậu ở interrupt và resume bằng payload mới — log
`resume với action=reject.`). **[Ảnh 4: log phiên 2 + JSON response]**

### Bước 3 — Chứng minh KHÔNG duplicate

```sql
SELECT action, original_value->_thread AS thread, created_at
FROM human_reviews WHERE feedback_id = '<feedback_id>';   -- ĐÚNG 1 dòng
SELECT corrected_value FROM correction_examples
WHERE feedback_id = '<feedback_id>';                      -- ĐÚNG 1 dòng, nhãn rỗng toàn phần
SELECT review_status FROM feedbacks WHERE id = '<feedback_id>';  -- rejected
```

**[Ảnh 5: SQL đối chiếu — mỗi bảng đúng 1 dòng]**

Gọi lại lần thứ 3 cùng body → **409** (`review_status` không còn `pending`,
thread completed) — chốt bằng chứng chống review lặp. **[Ảnh 6]**

## Kết quả mong đợi (điền sau khi chụp)

| Mốc | Kỳ vọng | Ảnh |
|---|---|---|
| Phiên 1 killed tại interrupt | thread tồn tại trong `checkpoints`, 0 dòng log | 2, 3 |
| Phiên 2 resume | 200 rejected, log `resume với action=` | 4 |
| Sau resume | 1 dòng human_reviews + 1 dòng correction_examples | 5 |
| POST lần 3 | 409 | 6 |

> Nếu bước nào lệch kỳ vọng → STOP, entry dated `docs/decisions.md`, fallback
> review-không-graph theo blocker rule plan §5.

## Dọn dẹp sau khi chụp (DB dev dùng chung)

```sql
DELETE FROM correction_examples WHERE feedback_id = '<feedback_id>';
DELETE FROM human_reviews       WHERE feedback_id = '<feedback_id>';
DELETE FROM checkpoints         WHERE thread_id = 'hitl-<feedback_id>';
DELETE FROM checkpoint_blobs    WHERE thread_id = 'hitl-<feedback_id>';
DELETE FROM checkpoint_writes   WHERE thread_id = 'hitl-<feedback_id>';
DELETE FROM feedbacks           WHERE id = '<feedback_id>';
```
