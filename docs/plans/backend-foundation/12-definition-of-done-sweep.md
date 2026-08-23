# Phase 12 — Definition of Done Sweep + Docs cuối

> **Nguồn:** execute-plan §9 (10 dòng DoD) + §2 (OUT-OF-SCOPE rà lại) + Hard rules
> **Trạng thái:** ⬜ · **Blocked by:** Tất cả phase 01–11
> **Commit mẫu:** `docs(dod): final readme, api notes, dod sweep results`

## 1 · Mục tiêu

Rà từng dòng §9 trên máy THẬT, điền kết quả vào bảng checklist, hoàn thiện docs người đọc ngoài (README tiếng Việt, api-notes), quét secrets, chốt giai đoạn backend foundation. Phase này KHÔNG sửa feature trừ khi DoD hở.

## 2 · Việc CON NGƯỜI

- Xác nhận với agent: đã sẵn sàng chạy end-to-end thật (LLM tokens cho 20 rows).
- Nhìn lại bảng kết quả sweep và quyết định: declare done hay kéo phase nào lại làm.

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 Sweep 10 dòng DoD — bảng bắt buộc điền ✅/⛔ + bằng chứng

| # | Điều kiện (§9) | Cách kiểm | Kết quả |
|---|---|---|---|
| 1 | Fresh-machine path đúng: WSL script → `uv sync` → `alembic upgrade head` → seed → uvicorn boots green | Làm đủ chuỗi lệnh theo README vừa viết | ☐ |
| 2 | Login cả 2 role; role sai bị 403 | curl 3 lần | ☐ |
| 3 | Import CSV 20 rows mixed VN-EN (fake PII) OK | CLI/API + report | ☐ |
| 4 | raw ≠ sanitized; pii_entities có; sanitized qua API mặc định, raw cần flag | query DB + curl 2 chế độ | ☐ |
| 5 | 1 run đầy đủ trên 20 rows: labels+severity+confidence+review flag+embeddings(model+dim); crash→resume không trùng (test chứng minh) | POST run + test idempotency | ☐ |
| 6 | `/similar` trả ranked neighbors cosine | curl k=5 | ☐ |
| 7 | llm_call_logs populated; Langfuse EU thấy trace CHỈ sanitized (inspect 1 trace); kill switch hoạt động | dashboard + env flip | ☐ |
| 8 | 6 spike scripts chạy xong; outcomes + fallback ghi decisions.md | đọc decisions.md | ☐ |
| 9 | pytest green (unit luôn; integration khi PG có) | pytest output | ☐ |
| 10 | Không secrets trong git history; `.env.example` đủ; README phủ Windows-dev+WSL-PG+run/test/deploy-placeholder | mục 3.3 dưới | ☐ |

### 3.2 Docs cuối
- **README.md** cập nhật (giữ tiếng Việt): quickstart đúng thứ tự fresh-machine (WSL setup → uv sync → .env → alembic → seed → uvicorn riêng terminal → pytest), ma trận test, placeholder mục "Deploy VPS (phase sau)".
- **docs/api-notes.md** viết: bảng endpoint thực tế đã ship (method, path, role, body/response chính), mode structured-output hiện hành, PROMPT_VERSION hiện tại.
- Rà OUT-OF-SCOPE §2: không có code clustering/insight/graph/frontend lọt vào; `frontend/README.md` placeholder tồn tại ("phase B1"); stubs 501 (clusters, insights, reviews, corrections, reports) còn nguyên docstring.

### 3.3 Secrets & hygiene sweep
```powershell
git ls-files                       # .env không nằm trong
git log --all -p -S "sk-" --name-only   # rà key pattern (kết quả sạch mới tick)
git log --all -p -S "LLM_API_KEY="      # không ai commit giá trị thật
```
- Kiểm tra `.env.example` khớp contract §5 từng biến.

### 3.4 Báo cáo kết thúc giai đoạn
Viết mục "Backend Foundation — kết quả" vào decisions.md hoặc file báo cáo riêng `docs/backend-foundation-report.md`: những gì pass, blocker nào còn treo, fallback nào được kích hoạt, số liệu spike — tư liệu chương "kết quả xây dựng hệ thống" của khóa luận.

## 4 · Tiêu chí nghiệm thu

Bảng 3.1 đủ 10 dòng có trạng thái + bằng chứng; mọi dòng ⛔ đều có entry decisions.md tương ứng giải thích.

## 5 · Lệnh kiểm chứng tổng

```powershell
cd backend
uv run pytest -q ; uv run pytest -q -m integration
wsl -d Ubuntu-24.04 -- bash -lc "sudo -u thesis psql -d feedback_agent -c 'SELECT count(*) FROM feedbacks' -c 'SELECT count(*) FROM llm_call_logs'"
git status --short   # sạch
```

## 6 · Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| Dòng DoD nào ⛔ | Entry dated: context → vì sao chưa đạt → kế hoạch gỡ |
| Phải sửa code để pass DoD | Commit fix riêng (`fix(...)`) rồi sweep lại dòng đó |
