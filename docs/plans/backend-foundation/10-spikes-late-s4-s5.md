# Phase 10 — Spike muộn S4 (HDBSCAN toy) · S5 (LangGraph interrupt/resume)

> **Nguồn:** execute-plan §8 (S4, S5) + §2 OUT-OF-SCOPE (chỉ spike script được đụng langgraph)
> **Trạng thái:** ⬜ · **Blocked by:** Phase 03 (DB + deps). S5 thêm cần internet + Supabase active — checkpoint tables do langgraph tự tạo trên đó.
> **Commit mẫu:** `test(spikes): S4 hdbscan toy evidence, S5 langgraph interrupt resume`

## 1 · Mục tiêu

Hai spike phục vụ **các phase sau** (clustering, HITL graph): trả lời bằng chứng chạy thật rồi ghi decisions.md — production code KHÔNG viết ở giai đoạn này.

## 2 · Việc CON NGƯỜI

- Không có. (S4/S5 không tốn LLM tokens — vector toy tự sinh; S5 chỉ chạy graph local.)

## 3 · Việc AGENT làm — checklist chi tiết

### 3.1 S4 — `s4_hdbscan_toy.py` · sklearn HDBSCAN cosine sane trên toy?

- **Câu hỏi:** HDBSCAN với metric cosine có chạy nhanh và cho noise hợp lý trên dữ liệu toy không (chuẩn bị cho phase clustering)?
- **Thiết kế:**
  - Sinh 200 vector 1536-d: 3 cụm giả (center ngẫu nhiên cố định seed=42 + noise nhỏ) + ~20 điểm nhiễu thật;
  - `sklearn.cluster.HDBSCAN(metric="cosine")`, sweep `min_cluster_size ∈ {5, 10, 15}` → in số cluster tìm được + % noise mỗi cấu hình;
  - Đo thời gian chạy (pass <5s).
- **⚠️ Dependency:** scikit-learn KHÔNG nằm trong pin §1 → cài ad-hoc spike-only:
  ```powershell
  cd backend
  uv run --with scikit-learn python ../scripts/spikes/s4_hdbscan_toy.py
  ```
  Ghi vào decisions.md: "scikit-learn chỉ dùng spike; production clustering sẽ quyết định lib sau".
- **Pass:** <5s, noise fraction hợp lý (không 0%, không >50% trên dữ liệu có cụm rõ), cluster count ≈ 3 ở min_cluster_size vừa.
- **Fallback nếu fail/quirk:** ghi trade-off note KMeans-primary (KMeans luôn có sẵn trong sklearn, bắt buộc gán mọi điểm).

### 3.2 S5 — `s5_langgraph_interrupt.py` · interrupt → restart → resume?

- **Câu hỏi:** LangGraph interrupt + AsyncPostgresSaver có resume đúng sau khi process chết, KHÔNG nhân đôi side effect? (nền tảng HITL review phase sau)
- **Thiết kế:**
  - Graph tối giản: node A → node B (`interrupt_before=["B"]`) → node C;
  - Side-effect counter: bảng `_spike_side_effects(id serial, ts)` — node B INSERT 1 row khi thực thi;
  - Checkpointer: `AsyncPostgresSaver.from_conn_string(DATABASE_URL)` nối thẳng Supabase; setup() tạo 4 bảng checkpoint trên đó (đã bị Alembic filter loại từ Phase 03 — kiểm chứng lại chúng xuất hiện và bị ignore);
  - Kịch bản: run 1 đến interrupt → **thoát process hẳn** (script nhận flag `--phase resume` chạy lần 2 như tiến trình mới) → run 2 resume → node B chạy đúng MỘT lần → assert counter == 1.
- **Pass:** resume OK, side effect đúng 1 lần.
- **Fallback nếu fail:** note "DB state machine tự quản" cho HITL phase — production graph vẫn ngoài scope giai đoạn này.
- Chạy: `uv run python ../scripts/spikes/s5_langgraph_interrupt.py --phase start` rồi `--phase resume`.

### 3.3 Record
- [ ] Cập nhật dòng S4, S5 bảng Spike outcomes trong decisions.md (Kết quả + Ngày + fallback?)
- [ ] Dọn bảng toy `_spike_*` khỏi DB sau khi đo xong.

## 4 · Tiêu chí nghiệm thu

| Tiêu chí | Bằng chứng |
|---|---|
| 2 script tồn tại + chạy được, kết quả JSON lưu | files |
| Spike outcomes table đủ 6/6 dòng có kết quả | decisions.md |
| Không production clustering/graph code lọt vào `backend/app/` | review diff |

## 5 · Lệnh kiểm chứng

```powershell
cd backend
uv run --with scikit-learn python ../scripts/spikes/s4_hdbscan_toy.py
uv run python ../scripts/spikes/s5_langgraph_interrupt.py --phase start
uv run python ../scripts/spikes/s5_langgraph_interrupt.py --phase resume
```

## 6 · Fallback / Khi nào ghi Decision Log

| Sự kiện | Hành động |
|---|---|
| HDBSCAN sklearn API lệch version | Ghim version ad-hoc rõ trong entry |
| AsyncPostgresSaver setup lỗi quyền/schema trên Supabase | Entry + thử sync saver hoặc chỉ định schema riêng cho checkpoint |
| Resume nhân đôi side effect | Đây chính là câu trả lời spike — ghi fail + fallback state machine, KHÔNG fix lan sang production code |
