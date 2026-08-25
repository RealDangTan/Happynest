# DELIVERY CONTRACTS — API đóng băng v1 (freeze 2026-08-25)

> **Nguồn:** [`delivery-design-spec.md`](delivery-design-spec.md) §3 (đã owner duyệt) · bám 100% cột/enums có sẵn: `clusters`, `insights`, `ReviewAction`, `LlmCallType.name_cluster|generate_insight`, `ReviewStatus`.
> **Luật sửa:** sau freeze, MỌI thay đổi shape/field → entry dated `decisions.md` TRƯỚC, rồi cập nhật file này + đánh số phiên. FE và BE cùng đọc file này — không bên nào được "tự hiểu".
> **Áp dụng chung mọi endpoint mới:** auth `pm|operations` (guard router-level như feedback); bộ lỗi chuẩn `401/403/404/409/422`; **không response nào chứa `raw_content` hay text PII** — snippet chỉ cắt từ `sanitized_content`; call LLM ghi `llm_call_logs`.

---

## C1 · GET /api/clusters

Query: `?sort=growth_ratio|recent` (tuỳ chọn; mặc định `feedback_count` giảm dần).

```jsonc
// 200
{ "items": [ {
  "id": "uuid", "name": "…", "summary": "…",
  "feedback_count": 12, "first_seen": "ISO", "last_seen": "ISO",
  "current_count": 8, "previous_count": 4, "growth_ratio": 1.0,
  "is_emerging": false, "is_spike": true,
  "suggested_priority": 0.82,              // null khi chưa chốt scale
  "sample_feedback_ids": ["uuid"]          // ≤5 phần tử, để FE link chi tiết
} ] }
```
Chưa từng chạy clustering → `200 {"items": []}` (không phải lỗi).

## C2 · GET /api/insights

```jsonc
// 200 — evidence_ids được server mở rộng thành object, ≤5 evidence/insight
{ "items": [ {
  "id": "uuid", "cluster_id": "uuid|null",
  "title": "…", "summary": "…", "suggested_action": "…",
  "evidence": [ { "feedback_id": "uuid",
                  "snippet": "cắt từ sanitized_content",
                  "severity": "high", "created_at": "ISO" } ],
  "review_status": "unreviewed"
} ] }
```

## C3 · HITL

Queue dùng lại endpoint ĐÃ SHIP: `GET /api/feedbacks?review_status=pending`.

### POST /api/reviews/{feedback_id} — phê duyệt NỘI DUNG
```jsonc
// Request
{ "action": "approve" | "edit" | "reject",
  "edited_content": "…" }        // BẮT BUỘC khi action=edit; ngược lại → 422
// Response 200: FeedbackOut sau cập nhật (review_status = approved|edited|rejected)
```
Quy tắc PII: `edited_content` do người dùng gõ có thể chứa PII → backend chạy lại Presidio trước khi lưu thành `sanitized_content`. Side effect: `edit`/`reject` tự ghi 1 dòng `correction_examples`.

### POST /api/corrections/{feedback_id} — sửa NHÃN
```jsonc
// Request: ít nhất 1 trong { categories[], ai_issue, severity, sentiment } (+ "note"?)
//          rỗng toàn bộ → 422
// Response 200: FeedbackOut cập nhật nhãn + { "correction_recorded": true }
// Effect: ghi correction_examples (input đã-sanitize + output-sửa) — nền few-shot v2
```
Không phụ thuộc review_status — áp dụng cho mọi feedback đã classify.

## C4 · GET /api/reports/summary

Query: `?days=7|30|90` (default 30). Thuần SQL aggregate — KHÔNG gọi LLM.

```jsonc
// 200
{ "generated_at": "ISO", "window_days": 30,
  "totals": { "feedback_count": 22, "pending_review_count": 4, "pii_detected_count": 4 },
  "by_severity": { "low": 5, "medium": 9, "high": 6, "critical": 2 },
  "by_sentiment": { "positive": 8, "neutral": 10, "negative": 4 },
  "top_categories": [ { "category": "hallucination", "count": 7 } ],   // ≤10
  "emerging": [ /* cluster có is_emerging|is_spike=true, ≤5, shape con của C1 */ ] }
```

## C5 · POST /api/clusters/run

Đồng bộ (dataset ≤1500). Idempotent: rerun xoá insights cũ → clusters cũ → tạo mới trong **1 transaction**.

```jsonc
// 200
{ "clusters_upserted": 6, "assigned_count": 18, "unassigned_count": 4, "duration_ms": 8123 }
// unassigned_count = noise HDBSCAN (-1) + row chưa có embedding (bị loại, báo count)
```

## C6 · POST /api/insights/run

```jsonc
// 409 nếu chưa có cluster nào ("chạy POST /api/clusters/run trước")
// 200
{ "insights_generated": 5, "duration_ms": 21000 }
```
Cap số cụm xử lý mỗi lượt qua env (`INSIGHT_MAX_CLUSTERS`, default 10) — kiềm chế chi phí LLM.

---

## Non-goals v1 (đừng hỏi endpoint cho những thứ này)

CRUD cluster/insight · đổi `review_status` của insight (cột tồn tại, chưa có API) · WebSocket/SSE · phân trang clusters/insights · multi-tenant/auth mở rộng · **logout endpoint** (v1 chấp nhận thiếu — cookie hết hạn theo tuổi thọ token; ghi nhận là limitation ở UF spec).

## Migration duy nhất cả giai đoạn

Thêm cột `feedbacks.cluster_id UUID FK→clusters.id NULLABLE + index` — bảng `clusters` không có chỗ lưu membership. Alembic revision thường; 4 bảng checkpoint LangGraph vẫn nằm ngoài filter Alembic như cũ.
