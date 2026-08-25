# Phase 15 — Insight engine + GET /api/insights + POST /api/insights/run

> **Nguồn:** [`delivery-design-spec.md`](delivery-design-spec.md) §5 P4 + §3 C2/C6 · [`delivery-contracts.md`](delivery-contracts.md) C2/C6 · Ngày viết: 2026-08-25 (viết sớm theo decisions cùng ngày)
> **Thứ tự pha:** P4a của [delivery-execute-plan.md](delivery-execute-plan.md) — **điều kiện cứng: phase 14 đã chạy `/clusters/run` thành công ít nhất 1 lần** (insight sinh theo cụm). **Executor đọc cả spec + contracts.**

## 1 · Bối cảnh & hiện trạng (verify bằng lệnh thật khi mở phase, ghi kết quả)

```bash
cd backend
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/insights   # 501 stub
# qua Supabase Studio hoặc script: SELECT count(*) FROM clusters;  → >0 (nếu 0 → CHẠY PHASE 14 TRƯỚC)
grep -n "generate_insight" app/models/enums.py                              # enum sẵn, chưa ai gọi
```

| Thành phần | Trạng thái | Việc phase này |
|---|---|---|
| Bảng `insights` | Đã tạo migration 0003, rỗng; đủ cột (`cluster_id` FK nullable, `evidence_ids` JSONB, `review_status`) | INSERT từ service |
| `LlmCallType.generate_insight` | Sẵn trong enum từ phase 03 | Gọi qua `chat_structured` |
| Cơ chế structured-output | Mode A/B fallback chain đã khóa (`llm_client.chat_structured`) | Tái dùng NGUYÊN — không viết đường gọi mới |
| Cap chi phí LLM | Chưa có biến môi trường insight | Task 1 thêm `INSIGHT_MAX_CLUSTERS` |

## 2 · Mục tiêu pha + Non-goals

**Mục tiêu:** (1) mỗi cụm ưu tiên cao → 1 call structured-output sinh title/summary/suggested_action kèm dẫn chứng là feedback id THẬT; (2) trigger đồng bộ có cap chống đốt tín dụng; (3) list endpoint mở rộng `evidence_ids` thành object evidence đúng C2.

**Non-goals:** đổi `review_status` của insight (cột tồn tại nhưng KHÔNG có API v1 — non-goal đã freeze); CRUD insight; insight cho feedback không thuộc cụm nào; dịch thuật/ngôn ngữ khác tiếng Việt; tóm tắt lại khi thêm feedback mới (regenerate là thao tác tay).

## 3 · Tasks

### Task 1 — Settings cap

**Files:** Modify `backend/app/core/config.py`

- [ ] Step 1.1: Thêm `INSIGHT_MAX_CLUSTERS: int = 10` vào Settings (đúng tên env contracts C6 quy định). Comment: cap số cụm xử lý mỗi lượt run để kiềm chế chi phí LLM (spec §8 rủi ro "hết tín dụng").
- [ ] Step 1.2: Verify: unit test đọc default qua `get_settings()`; set env override được. Commit: `feat(insights): INSIGHT_MAX_CLUSTERS cost cap`

### Task 2 — Engine `services/insight.py`

**Files:** Create `backend/app/services/insight.py`; Create `backend/app/schemas/insight.py` (schema Pydantic đầu ra LLM)

- [ ] Step 2.1: Schema đầu ra LLM `InsightDraft = {title (≤120 ký tự), summary (≤600), suggested_action (≤400), evidence_feedback_ids: list[uuid]}`. Prompt yêu cầu: tiếng Việt, mỗi nhận định phải dựa trên snippet được cung cấp, chọn tối đa 5 id dẫn chứng ĐẦY ĐỦ từ danh sách cho trước (không bịa id).
- [ ] Step 2.2: Chọn cụm: `ORDER BY suggested_priority DESC NULLS LAST LIMIT settings.INSIGHT_MAX_CLUSTERS`, bỏ cụm không còn member nào.
- [ ] Step 2.3: Payload mỗi cụm (PII boundary): tối đa 8 snippet 200 ký tự cắt từ `sanitized_content` (member mới nhất) + nhãn severity/categories tổng hợp + trend numbers. **Không bao giờ** đưa `raw_content` vào prompt.
- [ ] Step 2.4: **Server-side validate dẫn chứng** sau khi LLM trả: lọc `evidence_feedback_ids` chỉ giữ id thực sự thuộc cụm đó (whitelist từ DB), cắt còn ≤5. LLM bịa id sai → phần sai bị bỏ, không lỗi cả run (ghi log warning). Insight vẫn lưu nếu còn ≥1 dẫn chứng hợp lệ; 0 dẫn chứng hợp lệ → dùng 3 member priority cao nhất làm evidence mặc định (insight không bao giờ thiếu dẫn chứng — tinh thần "evidence-backed" của spec).
- [ ] Step 2.5: Mỗi cụm 1 call `chat_structured(..., call_type=LlmCallType.generate_insight)` tuần tự (dataset nhỏ, đơn giản hoá retry); 1 cụm fail fallback chain → skip cụm đó, đếm vào `skipped`, KHÔNG hỏng các cụm khác.
- [ ] Step 2.6: Hàm tổng `run_insights(db, settings) -> InsightsRunStats`: transaction duy nhất — DELETE insights cũ (toàn bộ — regenerate là replace-all, khớp tinh thần idempotent C5/C6) → INSERT insight mới với `review_status='unreviewed'` → commit. Trả `{insights_generated, skipped, duration_ms}`.
- [ ] Step 2.7: Unit test mock hoàn toàn `chat_structured`: assert cap áp dụng (15 cụm → chỉ 10 call), evidence bị lọc theo whitelist, LLM trả toàn id lạ → fallback 3 member, fail 1 cụm không chặn cụm kia. Verify: `uv run pytest tests/test_insights_unit.py -q` PASS. Commit: `feat(insights): evidence-backed generation engine with cost cap`

### Task 3 — Hai endpoint thay stub

**Files:** Modify `backend/app/api/routes/admin.py` (xoá stub `/insights`), Create schemas response trong `backend/app/schemas/insight.py`

- [ ] Step 3.1: `POST /api/insights/run`: **409** kèm detail "chạy POST /api/clusters/run trước" nếu bảng `clusters` rỗng (check bằng SELECT 1 LIMIT 1 — không phải exception); 200 trả `{insights_generated, duration_ms}` (đủ contract C6 — field `skipped` thêm ngoài contract được phép vì contract không cấm field bổ sung, ghi chú ở api-notes).
- [ ] Step 3.2: `GET /api/insights`: query insights JOIN feedback evidence — mở rộng `evidence_ids` JSONB thành object `{feedback_id, snippet, severity, created_at}`; snippet cắt 200 ký tự từ `sanitized_content` (**không bao giờ raw**); evidence >5 trong JSONB (không thể xảy ra do Task 2 chặn, phòng thủ vẫn cắt); trả `{items: [...]}` đúng C2 field-by-field.
- [ ] Step 3.3: Integration test `-m integration` (`tests/test_insights_api_integration.py`): mock LLM ở mức service (integration chỉ chứng minh đường HTTP→DB→contract, KHÔNG đốt tín dụng thật) → seed 1 cụm giả → POST /run → GET shape C2 từng field → POST /run lần 2 không nhân bản. Riêng **1 test evidence thủ công không-mock** đánh dấu riêng (bỏ qua mặc định qua env `EVIDENCE_LLM_LIVE=1`) chụp response thật cho luận văn. Verify: `uv run pytest -m integration tests/test_insights_api_integration.py -v` PASS. Commit: `feat(insights): insights run + list endpoints replace 501 stub`

## 4 · Acceptance criteria + Evidence cần chụp

- [ ] 409 đúng điều kiện chưa có cụm; message hướng dẫn bước tiếp theo
- [ ] Mọi insight đều có ≥1 evidence trỏ tới feedback id THẬT thuộc đúng cụm (test whitelist)
- [ ] Snippet trong cả prompt lẫn response chỉ từ `sanitized_content` (grep + assert test)
- [ ] `INSIGHT_MAX_CLUSTERS` chặn số call LLM thực tế (assert qua mock call count)
- [ ] Rerun replace-all không duplicate; insight mới luôn `review_status='unreviewed'`
- [ ] `llm_call_logs` có dòng `generate_insight` cho mỗi call, kể cả attempt thất bại
- [ ] Suite unit xanh offline; integration PASS khi có mạng + cụm đã tồn tại
- [ ] **Evidence luận văn:** 1 insight thật trên data demo (chạy live Task 3.3) — chụp JSON response + screenshot dashboard FE khi P4 mount xong

## 5 · Blocker rule

LLM liên tục trả evidence id sai dù prompt ràng buộc (fallback chain sống nhưng chất lượng kém) → hạ kỳ vọng: chuyển sang server tự chọn evidence (member confidence cao nhất) và LLM chỉ sinh text — entry decisions ghi thay đổi thiết kế. Chi phí tín dụng cạn giữa pha → STOP, giữ phần đã commit, chuyển 16-reports (thuần SQL không cần LLM); quay lại khi nạp thêm.
