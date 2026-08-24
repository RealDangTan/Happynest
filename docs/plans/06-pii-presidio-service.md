# Phase 06 — PII Sanitization (Presidio + Stanza "vi")

> **Nguồn:** execute-plan §1 (PII) + §7 contract `sanitize()` + DoD mục 4 + Hard rule #2
> **Trạng thái:** ⬜ · **Blocked by:** Phase 05 (+ models stanza đã tải từ Phase 01)
> **Commit mẫu:** `feat(pii): presidio sanitize service wired into ingestion`

## 1 · Mục tiêu

Mọi feedback khi vào hệ thống được sanitize NGAY: `raw_content` giữ nguyên trong DB, nhưng **mọi thứ rời khỏi biên sanitize** (prompt LLM, log, trace, API mặc định) là `sanitized_content` với PII thay bằng placeholder `<TYPE>`.

Contract khóa (§7):
```python
def sanitize(raw: str) -> SanitizeResult
# {sanitized_text: str, pii_detected: bool, entities: list[dict]}
```

## 2 · Việc CON NGƯỜI

- Không có (models đã tải ở Phase 01). Nếu chạy lần đầu thấy RAM căng (>6GB) → đóng app khác; entry nếu phải hạ model.

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 Service — `app/services/presidio_service.py`
- **Analyzer khởi tạo ĐÚNG MỘT LẦN** tại startup (lifespan trong `main.py` gọi `init_presidio()`), không tạo lại mỗi request (Stanza pipeline nặng ~1 GB RAM).
  - NlpEngine: `StanzaNlpEngine(models={"vi": "vi", "en": "en"})` — hỗ trợ code-switching.
  - Recognizers: builtin `EmailRecognizer`, `UrlRecognizer`, `IpAddressRecognizer` + 2 custom `PatternRecognizer`:
    - `"VN_PHONE"` regex `(?:\+84|0)(?:[ .-]?)(?:3|5|7|8|9)(?:[ .-]?\d){8}` score ~0.9;
    - `"CCCD_12"` regex `\b\d{12}\b` score ~0.85 (12 số liền).
  - Person name: dùng NLP engine (score thấp, chấp nhận caveat theo S1).
- Anonymizer: `OperatorConfig("replace", {type: f"<{type}>"})` — mapping tên hiển thị:
  `EMAIL_ADDRESS→<EMAIL>`, `PHONE_NUMBER/VN_PHONE→<PHONE_NUMBER>`, `URL→<URL>`, `IP_ADDRESS→<IP_ADDRESS>`, `CCCD_12→<CCCD>`, `PERSON→<PERSON>`.
- `SanitizeResult` pydantic/dataclass. `entities` chỉ chứa **metadata `{type, start, end, score}` — KHÔNG chứa chuỗi raw** (raw substring không được nằm trong jsonb `pii_entities`, vì cột này có thể bị đọc qua API).

### 3.2 Wiring vào ingestion — sửa `ingest_service.py`
- Trong `ingest_one`: sau khi có raw → `result = sanitize(raw)` → lưu `sanitized_content=result.sanitized_text`, `pii_detected=result.pii_detected`, `pii_entities=[e.dict() for e in result.entities]`.
- Áp cho cả POST đơn lẻ lẫn CSV import (vì cùng đi qua `ingest_one`/service layer).
- Script backfill: `backend/scripts/backfill_sanitization.py` — quét các row có `sanitized_content IS NULL`, sanitize từng row, commit từng row (an toàn khi crash). Chạy một lần sau deploy wiring.

### 3.3 Rà biên PII (hard rule)
- Exception handler + logging không in payload;
- `GET /api/feedbacks/{id}` mặc định trả sanitized; raw chỉ với `include_raw=true` (đã làm Phase 05);
- Docstring module ghi rõ: "output của hàm này là thứ DUY NHẤT được phép đi tiếp vào LLM/log/trace".

### 3.4 Tests — `backend/tests/test_presidio_service.py`
- Fixture ground truth fake PII (tái dùng dataset S1): email, VN phone (3 dạng format), CCCD, URL, IP, person name.
- Assert:
  - recall obvious-type ≥80% (đồng bộ pass criterion S1);
  - `sanitized_content` KHÔNG còn chứa chuỗi raw nào của PII (assert từng substring);
  - placeholder đúng loại xuất hiện (`<EMAIL>` v.v.);
  - `pii_entities` chỉ có type/start/end/score — assert không key nào mang text;
  - text sạch (không PII) → `pii_detected=false`, content giữ nguyên.
- Test wiring: ingest qua API 1 dòng có PII → DB có `pii_detected=true` + sanitized khác raw.

## 4 · Tiêu chí nghiệm thu (map DoD mục 4)

| DoD | Bằng chứng |
|---|---|
| `raw_content ≠ sanitized_content` sau import | query DB / test |
| `pii_entities` populated (metadata-only) | test assert schema |
| Sanitized text visible qua API mặc định, raw chỉ với flag | test + curl |

## 5 · Lệnh kiểm chứng

```powershell
cd backend
uv run pytest tests/test_presidio_service.py
uv run python scripts/backfill_sanitization.py   # nếu đã import CSV trước đó
# smoke tay:
uv run python -c "from app.services.presidio_service import sanitize; r=sanitize('Liên hệ tôi qua nguyenvan@example.com hoặc 0901234567 nhé'); print(r.sanitized_text, r.pii_detected)"
# kỳ vọng: 'Liên hệ tôi qua <EMAIL> hoặc <PHONE_NUMBER> nhé True'
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| Stanza vi engine lỗi init trên Windows (thường gặp) | Fallback regex-only (kết quả S1 đã đo sẵn), entry dated ghi rõ mất khả năng nhận diện PERSON |
| Recall thực tế < S1 do engine version khác | Entry + cân nhắc thêm pattern |
| RAM không đủ giữ Stanza thường trú | Cân nhắc lazy-load + unload sau batch (đổi kiến trúc → entry bắt buộc) |
| Placeholder format cần khác (ví dụ `[EMAIL]`) | Chỉnh mapping nhất quán 1 nơi, cập nhật tests |
