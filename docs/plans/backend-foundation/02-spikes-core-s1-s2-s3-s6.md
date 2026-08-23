# Phase 02 — Spike cốt lõi S1 · S2 · S3 · S6

> **Nguồn:** execute-plan §8 (bảng spike) + rule §10.8 (spike trước khi build module production)
> **Trạng thái:** ⬜ · **Blocked by:** Phase 01 (deps + models). Riêng **S3 cần PG thật** (WSL đã cài); **S2 cần key LLM** trong `.env`.
> **Commit mẫu:** `test(spikes): add S1-S3,S6 evidence scripts and record outcomes`

## 1 · Mục tiêu

Trả lời 4 câu hỏi kỹ thuật bằng bằng chứng chạy thật, TRƯỚC khi viết module production tương ứng. Script giữ lại tại `scripts/spikes/` làm minh chứng khóa luận. Kết quả ghi vào bảng "Spike outcomes" trong `docs/decisions.md` (cột Kết quả / Ngày / Fallback kích hoạt?).

Vị trí script: **root repo** `scripts/spikes/` (ngoài uv project). Chạy từ `backend/`:
```powershell
cd backend
uv run python ../scripts/spikes/s1_presidio_vi.py
```
Mỗi script in báo cáo JSON ra stdout VÀ lưu `scripts/spikes/results/<tên>_result.json` (thư mục results thêm vào `.gitignore` nếu chứa dữ liệu nhạy — chỉ commit code + kết quả tổng hợp dạng số).

## 2 · Việc CON NGƯỜI

- Đảm bảo `.env` đã có `LLM_*` + `EMBEDDING_MODEL` thật (cho S2/S3).
- Đảm bảo WSL Ubuntu + PG16 đã lên (cho S3/S6) — nếu chưa: agent vẫn làm được **S1**, và tạm hoãn S3/S6 sang khi sẵn sàng (ghi blocker vào decisions.md, nhảy sang Phase 03 theo rule §10.6).

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 S1 — `s1_presidio_vi.py` · Presidio + Stanza("vi") bắt PII VN-EN?

- **Câu hỏi:** StanzaNlpEngine("vi") + regex có bắt đủ PII trong 20 mẫu trộn Việt–Anh với fake PII cài sẵn không?
- **Dataset (fake 100%, tự sinh trong script, KHÔNG dùng data thật):** 20 string mẫu kiểu feedback thực tế, mỗi mẫu cài ≥1 fake PII, phủ các loại:
  - email: `nguyen.van.a@example.com`, `hotro247@spam.test`
  - phone VN: `0901234567`, `+84912345678`, `0912 345 678` (có/không khoảng trắng)
  - CCCD 12 số giả: `012345678901`
  - URL: `https://example.com/bai-viet`, IP `192.168.1.10`
  - person name tiếng Việt giữa câu: "Tôi là **Nguyễn Văn A** …"
- **Recognizer set:** builtin EMAIL/URL/IP + 2 `PatternRecognizer` tự viết:
  - `VN_PHONE`: regex `(?:\+84|0)(?:3|5|7|8|9)\d{8}` (cho phép space/dot phân cách → normalize trước match)
  - `CCCD_12`: regex `\b\d{12}\b`
- **Flow:** dựng AnalyzerEngine với StanzaNlpEngine("vi") (chậm lần đầu ~vài chục giây) → analyze từng mẫu → so ground truth theo type → tính recall per-type.
- **Pass:** recall ≥80% với các obvious type (email/phone/CCCD); person name đánh giá "usable-with-caveat" (ghi nhận precision thấp chấp nhận được).
- **Fallback nếu fail:** mode regex-only (bỏ NLP engine) — đo lại recall regex-only để so sánh, ghi cả hai số.
- [ ] Viết script + chạy + lưu result JSON
- [ ] Cập nhật dòng S1 bảng Spike outcomes

### 3.2 S2 — `s2_llm_schema.py` · Provider có honor `json_schema` response_format?

- **Câu hỏi:** Provider ở `LLM_BASE_URL` trả đúng JSON khớp schema khi truyền `response_format={"type":"json_schema", ...}` không?
- **Thiết kế:** 10 call độc lập, `temperature=0`, schema nhỏ (sentiment + severity của 10 câu feedback VI ngắn khác nhau). Đếm số call parse+validate Pydantic thành công.
- **Pass:** ≥9/10 valid → mode production = `json_schema`.
- **Fail path (quan trọng — đây chính là prototype fallback chain của Phase 07):** rơi xuống prompt-injected JSON ("Return ONLY a JSON object matching…"), strip code fence, Pydantic validate; lỗi validate → retry MỘT lần kèm text lỗi. Đo tỉ lệ thành công mode này.
- **Ghi:** mode nào thắng + tỉ lệ + ví dụ lỗi provider trả về (nếu có) vào decisions.md. Đây quyết định nhánh mặc định của `llm_client.chat_structured`.
- [ ] Script + chạy 10 call + record
- ⛔ Nếu chưa có key: đánh dấu blocked trong decisions.md, quay lại sau khi người dùng điền `.env`.

### 3.3 S3 — `s3_embedding_pgvector.py` · Embeddings API + roundtrip pgvector qua WSL2?

- **Câu hỏi:** `/v1/embeddings` hoạt động? Vector đi vào PG-in-WSL2 và query cosine về đúng?
- **Thiết kế:**
  1. Call embeddings cho 10 câu VI; in **model name mà server report** + số chiều thực tế; đối chiếu `EMBEDDING_DIM=1536` — lệch → dừng, ghi Decision Log (đổi `EMBEDDING_DIM` + `VECTOR(n)` tương ứng).
  2. Tạo bảng toy (`CREATE TABLE _spike_vec (id serial, v vector(1536))`) trên DB `feedback_agent` qua psycopg thuần.
  3. Insert 10 vector; lấy câu #1 query `ORDER BY v <=> :q LIMIT 3` → self-match phải rank #1 với score ≈ 1.0 (cosine similarity `1 - distance`).
- **Pass:** self-match rank #1 mọi câu; ghi model name + dims thực đo.
- **Fallback:** provider embedding thay thế (đổi env); nếu pgvector extension lỗi tạo bảng → xem Phase 03 mục migration.
- [ ] Script + chạy + record; drop bảng toy xong việc.

### 3.4 S6 — `s6_parity.py` · Parity Windows-native ↔ PG-in-WSL2 end-to-end?

- **Câu hỏi:** Toàn bộ chuỗi dev chạy từ Windows side: Alembic migrate + insert/query vector qua SQLAlchemy + pgvector-python OK không?
- **Thiết kế:** (1) `uv run alembic upgrade head` từ `backend/` target WSL PG; (2) insert 1 row `feedbacks` có embedding bằng ORM; (3) query ngược so khớp; (4) đo thời gian 20 query cosine tuần tự (tham khảo hiệu năng localhost↔WSL).
- **⚠️ Thứ tự thực tế:** S6 cần migrations của Phase 03 tồn tại mới chạy đủ. Cho phép: chạy phần "PG reachable + raw psycopg roundtrip" ngay phase này, phần Alembic/ORM hoàn tất ngay sau Phase 03 (ghi rõ trong decisions.md ngày chạy từng phần). Pass criterion cuối: green toàn phần.
- **Fallback nếu fail:** chuyển toàn bộ dev vào WSL2 (nặng) — chỉ cân nhắc khi parity hỏng thật sự, phải entry dated.
- [ ] Script + chạy phần khả dụng + record

## 4 · Tiêu chí nghiệm thu

| Tiêu chí | Bằng chứng |
|---|---|
| 4 script tồn tại `scripts/spikes/`, chạy được bằng `uv run` | file + output |
| Bảng Spike outcomes trong `decisions.md`: S1, S2, S3, S6 có Kết quả + Ngày (S6 được 2 dòng nếu tách phần) | diff decisions.md |
| Fallback kích hoạt (nếu có) được mô tả + mode production tương ứng chốt | decisions.md |
| Không có fake PII hay key thật nằm trong committed scripts | review diff |

## 5 · Lệnh kiểm chứng

```powershell
cd backend
uv run python ../scripts/spikes/s1_presidio_vi.py   # exit 0, JSON report
uv run python ../scripts/spikes/s2_llm_schema.py    # 9+/10 valid hoặc fallback đo được
uv run python ../scripts/spikes/s3_embedding_pgvector.py  # rank #1
uv run python ../scripts/spikes/s6_parity.py        # green phần khả dụng
git log --oneline -3                                # thấy commit spikes
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| S1 < 80% recall | Kích hoạt regex-only, ghi cả 2 con số |
| S2 < 9/10 | Mode production = prompt-JSON+validate+retry, Phase 07 dùng nhánh này làm mặc định |
| S3 dims ≠ 1536 | Entry dated: đổi EMBEDDING_DIM + cột VECTOR(n), cập nhật `.env.example` |
| WSL/PG chưa sẵn sàng | Ghi blocker, làm S1 rồi nhảy Phase 03 (rule §10.6) |
| Provider từ chối `json_schema` hoàn toàn (HTTP 400 cố định) | Ghi response lỗi nguyên văn (che key) vào entry |
