# Evidence — HITL checkpoint sống sót restart (kill → restart → resume)

> Phase 13 (plan `13-hitl-langgraph.md` §3.6.1) · Bằng chứng số 1 cho chương
> kết quả luận văn: checkpoint LangGraph trên Supabase giúp review flow tiếp
> diễn sau khi process chết GIỮA interrupt và resume — không mất state,
> KHÔNG nhân bản dòng log, retry của người dùng TỰ-HEAL phần dở dang.
>
> Cơ sở lý thuyết: spike S5 (decisions.md 2026-08-24) đã chứng minh nguyên lý
> trên 2 tiến trình toy; thủ tục dưới đây chứng minh trên API production thật.

## Điều kiện trước khi chụp

- Supabase dev reachable; mật khẩu seed pm hợp lệ
  (`backend/tests/conftest.py::TEST_PASSWORDS`).
- Cách 1 (khuyến nghị — tự động hóa toàn bộ): `cd backend &&
  uv run python scripts/evidence_hitl_checkpoint_resume.py` — script tự
  seed row, boot server thật (port 8010), bắn POST reject, KILL cứng process
  ở đúng cửa sổ, boot process MỚI, retry cùng body và đối chiếu SQL, in kết
  quả từng bước, tự dọn dẹp. Log 2 phiên server nằm ở
  `backend/evidence-server-{1,2}.log` (chụp màn hình làm [Ảnh 2] và [Ảnh 4]).
- Cách 2 (thủ công): 2 terminal + Supabase Studio, theo các bước dưới.

## Thủ tục chụp

### Bước 0 — Seed 1 feedback pending + login

Script tự seed trực tiếp 1 row `review_status='pending'` (source
`hitl-evidence`, không PII) và in ra `feedback_id`. Với cách thủ công:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/token \
  -d "username=pm@thesis.local&password=<pass>" | jq -r .access_token)

curl -s -X POST http://127.0.0.1:8000/api/feedbacks \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"source":"evidence","content":"Tôi là Nguyễn Văn A, số 0900123456, app bị lỗi nặng","external_ref":"hitl-evidence-1"}'
```

Chạy analysis run để classify (PII detected ⇒ `requires_human_review=true` ⇒
`review_status='pending'`) rồi ghi lại `feedback_id`:

```sql
SELECT id, external_ref, review_status FROM feedbacks WHERE external_ref LIKE 'hitl-evidence%';
-- kỳ vọng review_status = 'pending'
```

**[Ảnh 1: kết quả SQL — row pending]**

### Bước 1 — Crash GIỮA hai commits: status đã ghi, log chưa kịp

```bash
curl -s -X POST http://127.0.0.1:8000/api/reviews/<feedback_id> \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"reject","reason":"spam"}'
```

Request treo vài chục giây vì graph ghi checkpoint qua WAN. **Cửa sổ crash
đắt giá nhất**: node `apply_action` commit `review_status` TRƯỚC, node
`record_correction` commit 2 dòng log SAU — giữa hai commits này graph phải
ghi checkpoint qua WAN (~9s) nên cửa sổ khá rộng. Kill process NGAY khi SQL
thấy `review_status != 'pending'` mà `human_reviews` VẪN TRỐNG (script poll
0.2s rồi `TerminateProcess`). **[Ảnh 2: log phiên 1 — request chưa kịp trả về
khi process chết]**

Kiểm chứng state nằm trên Postgres, KHÔNG phụ thuộc process:

```sql
SELECT thread_id FROM checkpoints WHERE thread_id = 'hitl-<feedback_id>';  -- CÓ thread
SELECT review_status FROM feedbacks WHERE id = '<feedback_id>';            -- rejected (đã commit)
SELECT count(*) FROM human_reviews WHERE feedback_id = '<feedback_id>';    -- 0 (chưa kịp)
SELECT count(*) FROM correction_examples WHERE feedback_id = '<feedback_id>'; -- 0
```

**[Ảnh 3: thread tồn tại trong checkpoints; status đã đổi, log còn trống]**

### Bước 2 — Process MỚI + retry cùng body → TỰ-HEAL

Khởi động lại uvicorn (tiến trình HOÀN TOÀN MỚI — state chỉ còn trên
Postgres), gọi lại ĐÚNG body cũ:

```bash
uv run uvicorn app.main:app --port 8000
curl -s -X POST http://127.0.0.1:8000/api/reviews/<feedback_id> \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"reject","reason":"spam"}' | jq .
```

Kỳ vọng: **200** `"review_status": "rejected"` — route đọc thấy row đã rời
`pending` vẫn ĐƯA VÀO GRAPH (decisions.md 2026-08-25: pre-check 409 chỉ dành
cho `unreviewed`); graph đọc checkpoint nhận diện thread đang ở GIỮA đường,
chạy nốt node thiếu mà KHÔNG cần payload mới; node `record_correction`
chạy LẠI nhưng marker `_thread` trong JSONB chặn nhân bản. Đây chính là cơ
chế tự-heal: người dùng chỉ cần bấm lại nút Duyệt. **[Ảnh 4: log phiên 2 +
JSON response 200 rejected]**

### Bước 3 — Chứng minh KHÔNG duplicate + chống review lặp

```sql
SELECT action, original_value->_thread AS thread, created_at
FROM human_reviews WHERE feedback_id = '<feedback_id>';   -- ĐÚNG 1 dòng (bổ sung bởi lần retry)
SELECT corrected_value FROM correction_examples
WHERE feedback_id = '<feedback_id>';                      -- ĐÚNG 1 dòng, nhãn rỗng toàn phần
SELECT review_status FROM feedbacks WHERE id = '<feedback_id>';  -- rejected
```

**[Ảnh 5: SQL đối chiếu — mỗi bảng đúng 1 dòng dù node chạy lại xuyên process]**

Gọi lại lần thứ 3 cùng body → **409** (thread completed —
`ReviewAlreadyCompleted`). **[Ảnh 6]**

## Kết quả thực đo — 2026-08-25, script tự động, PASS TOÀN BỘ

Chạy lần đầu (`feedback_id c6849976`, process thật ×2, checkpoint qua WAN):

| Mốc | Kỳ vọng | Kết quả thực đo | Ảnh |
|---|---|---|---|
| Phiên 1 killed giữa apply_action-commit và record_correction-commit | thread trong `checkpoints`; status đã rời `pending`; 2 bảng log còn TRỐNG | `checkpoints=4`, `review_status='rejected'`, `human_reviews=0` ✓ | 2, 3 |
| Phiên 2 (process mới) retry cùng body | 200 rejected; graph tự chạy nốt; node replay bị chặn bởi marker `_thread` | **HTTP 200**, `review_status: rejected` ✓ | 4 |
| Sau retry | human_reviews/correction_examples ĐÚNG 1 dòng mỗi bảng — không mất, không nhân bản | `human_reviews=1`, `correction_examples=1` ✓ | 5 |
| POST lần 3 | 409 | **409** (`ReviewAlreadyCompleted`) ✓ | 6 |

> [Ảnh 1–6]: chụp lại bất cứ lúc nào bằng cách chạy lại script (tự seed, tự
> dọn) rồi screenshot log `evidence-server-{1,2}.log` + SQL trong Supabase
> Studio tại các bước tương ứng.

> Nếu bước nào lệch kỳ vọng → STOP, entry dated `docs/decisions.md`, fallback
> review-không-graph theo blocker rule plan §5. (Ghi chú lịch sử: chính thủ
> tục này đã bắt được lỗi pre-check 409 chặn self-heal ở lượt chạy thử đầu —
> sửa kèm entry decisions.md cùng ngày trước khi PASS.)

## Dọn dẹp sau khi chụp (DB dev dùng chung)

Script TỰ ĐỘNG dọn (correction_examples → human_reviews → 3 bảng checkpoint →
feedbacks) ngay sau bước 409. Dọn tay khi dùng cách thủ công:

```sql
DELETE FROM correction_examples WHERE feedback_id = '<feedback_id>';
DELETE FROM human_reviews       WHERE feedback_id = '<feedback_id>';
DELETE FROM checkpoints         WHERE thread_id = 'hitl-<feedback_id>';
DELETE FROM checkpoint_blobs    WHERE thread_id = 'hitl-<feedback_id>';
DELETE FROM checkpoint_writes   WHERE thread_id = 'hitl-<feedback_id>';
DELETE FROM feedbacks           WHERE id = '<feedback_id>';
```
