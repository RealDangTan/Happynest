# Phase 20 — Closed-loop impact check + KPI 3-latency + demo script

> **Nguồn:** brainstorm 2026-08-25 (closed-loop "did the action work?" + KPI time-to-listen/insight/action là điểm khác biệt luận văn) · decisions 2026-08-26 · Ngày viết: 2026-08-26
> **Thứ tự pha:** P6-D của [delivery-execute-plan.md](delivery-execute-plan.md) — phần Task 1–2 (KPI/impact) làm được độc lập sau **17**; Task 3–4 (demo trọn) cần **19 ✅**. Phần reports C4 (phase 16) KHÔNG bị đụng — KPI là endpoint RIÊNG.

## 1 · Bối cảnh & hiện trạng (verify bằng lệnh thật khi mở phase, ghi kết quả)

```bash
cd backend
grep -n "class ImpactCheck" app/models/impact_check.py      # bảng từ migration 0007
curl -s http://127.0.0.1:8000/api/reports/summary -o /dev/null -w "%{http_code}\n"   # 200 nếu phase 16 xong, 501 nếu chưa — KPI không phụ thuộc
uv run pytest -q
```

| Thành phần | Trạng thái | Việc phase này |
|---|---|---|
| `impact_checks` | Bảng sẵn (0007), rỗng | Service điền |
| Timestamps KPI | `feedbacks.created_at` · `analysis_runs.started_at` · `insights.created_at` · `action_drafts.created_at` — ĐỦ để tính 3 latency, không cần thêm cột | Query thuần SQL |
| Auto vs HITL marker | Insight auto = KHÔNG có row `insight_reviews`; insight HITL = CÓ | Định nghĩa KPI dựa trên điều này (khớp thiết kế 19 §2.7) |
| `GET /api/reports/summary` | Thuộc C4, thuần SQL, shape freeze | Không đụng — thêm `/api/reports/kpis` song song |

## 2 · Mục tiêu pha + Non-goals

**Mục tiêu:** (1) job impact check: cụm có action được duyệt ≥N ngày → đo volume trước/sau → ghi `impact_checks`; (2) `GET /api/reports/kpis`: median 3 latency + tỉ lệ insight→action + tỉ lệ HITL/auto + tổng hợp impact — THUẦN SQL, không một call LLM; (3) `docs/demo-script.md` kịch bản bảo vệ từng lệnh thật; (4) chỉnh `docs/ai-agent-success-story.md` khớp thực tế đã build.

**Non-goals:** scheduler tự chạy impact check (trigger tay như mọi thứ khác); chart BE (FE tự vẽ); xuất PDF/CSV; sửa shape C4 hay endpoint phase 16; FE màn approval agent.

## 3 · Tasks

### Task 1 — Impact check service

**Files:** Create `backend/app/services/impact.py`; Modify `backend/app/core/config.py`

- [ ] Step 1.1: Settings thêm `IMPACT_WINDOW_DAYS:int=7`.
- [ ] Step 1.2: `run_impact_checks(db, settings) -> dict`: chọn insights `review_status IN ('approved','edited')` CÓ ≥1 draft kind=`draft_ticket`, `created_at <= now() - IMPACT_WINDOW_DAYS`, CHƯA có row trong `impact_checks` (theo insight_id). Mỗi insight: `t = action_drafts.created_at MIN`; `before = COUNT feedbacks WHERE cluster_id=c AND created_at ∈ [t−W, t)`; `after = COUNT ... [t, t+W)`; `delta_ratio = (after − before) / GREATEST(before,1)` làm tròn 3 chữ số; INSERT `impact_checks(insight_id, cluster_id snapshot, cluster_name, checked_at=t+W, window_days=W, before_count, after_count, delta_ratio)`. Trả `{checks_inserted, items:[{cluster_name, before, after, delta_ratio}]}`.
- [ ] Step 1.3: Unit/integration test: seed insight approved cũ giả + member feedback trải 2 bên mốc → assert counts/delta đúng; insight mới hơn window → bị bỏ qua; rerun không nhân bản (idempotent theo insight_id). Verify PASS. Commit: `feat(agents): closed-loop impact check over approved actions`

### Task 2 — `GET /api/reports/kpis`

**Files:** Modify `backend/app/api/routes/admin.py` (router admin hiện có, guard pm|operations như cũ); Create `backend/app/schemas/report.py` (bổ sung class nếu 16 đã tạo file); Modify `docs/api-checklist.md` (**hard rule #10 — cùng commit**)

- [ ] Step 2.1: Công thức KPI (chốt cứng, mỗi dòng 1 aggregate SQL riêng, gộp vào 1 response):
  - `time_to_listen_median_s` = `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (r.started_at − f.created_at)))` JOIN `feedbacks f JOIN analysis_runs r ON f.analysis_run_id=r.id` WHERE `r.pipeline_version <> 'agent-router-v1' AND f.categories IS NOT NULL` (đường classify sản xuất).
  - `time_to_insight_median_s` = median(`i.created_at − c.last_seen`) JOIN insights×clusters WHERE cluster_id IS NOT NULL.
  - `time_to_action_median_s` = median(MIN(draft.created_at) − i.created_at) GROUP BY insight; NULL nếu chưa có draft nào.
  - `insights_total`, `insights_with_action` (DISTINCT insight_id trong drafts), `pct_insight_with_action` (% 2 chữ số).
  - `hitl_count` = insights finalized (`approved/edited/rejected`) CÓ insight_reviews; `auto_count` = finalized KHÔNG có; `hitl_share` %.
  - `impact = {checks_count, avg_delta_ratio}` từ bảng impact_checks.
  - `generated_at` ISO.
- [ ] Step 2.2: Integration test `-m integration` (`tests/test_reports_kpis_integration.py`): data demo + 1 insight approved giả kèm draft + review rows → assert từng field kiểu/hợp lý (median > 0, pct ∈ [0,100]); **assert không mock LLM nào bị chạm** (service không import llm_client — cùng tinh thần phase 16). Verify PASS. Commit: `feat(reports): sql-only three-latency kpi endpoint`

### Task 3 — Demo script + success story alignment

**Files:** Create `docs/demo-script.md`; Modify `docs/ai-agent-success-story.md`

- [ ] Step 3.1: `demo-script.md` — kịch bản bảo vệ ~15 phút, mỗi bước là LỆNH THẬT đã chạy được + số liệu mong đợi từ dataset 17: (1) login → dashboard PM; (2) trigger agent run trên planted Google-login cluster → xem progress/budget; (3) interrupt payload: insight + quotes + precedent ("cụm tương tự từng bị rate P2…"); (4) APPROVE → drafts hiện ra (copy-paste Jira); (5) chạy lại scenario false-alarm email-trễ → REJECT kèm reason → chỉ ra rejection trở thành precedent âm; (6) impact check + `/api/reports/kpis` đọc 3 con số latency; (7) kill-restart-resume (trỏ evidence script 19). Mỗi bước ghi "nếu lỗi thì nói gì" (fallback line cho phòng thủ).
- [ ] Step 3.2: Sửa success story cho khớp thực tế: mọi nhắc Zendesk/Jira/Slack → "draft artifact copy-paste"; các giai thoại cần tenant/release/CSAT metadata → viết lại trên evidence feedback-only (volume/severity/trend); bổ sung đoạn fully-routed router + budget cap + critic checklist (điểm mạnh thật của hệ thống). KHÔNG thêm claim mới chưa có API chứng minh.
- [ ] Step 3.3: Commit: `docs(demo): defense walkthrough script + align success story with shipped reality`

### Task 4 — Evidence chụp

**Files:** Create `docs/evidence/kpi-sample.json`, `docs/evidence/impact-check-sample.json`

- [ ] Step 4.1: Chạy live: impact check lần đầu trên data demo (sau khi 19 approve ≥1 insight và đủ window — nếu chưa đủ N ngày, giảm tạm `IMPACT_WINDOW_DAYS` qua env CHO TRẬN DEMO rồi trả nguyên giá trị, ghi chú rõ) + lưu 2 JSON mẫu. Chụp screenshot `/api/reports/kpis` đối chiếu Supabase Studio.
- [ ] Step 4.2: Commit: `docs(evidence): kpi and impact-check samples on demo dataset`

## 4 · Acceptance criteria + Evidence cần chụp

- [ ] Impact check idempotent; delta_ratio đúng công thức trên fixture; insight chưa đủ tuổi bị bỏ qua
- [ ] `/api/reports/kpis` đủ field §2.1, zero LLM call, <1s local; sai role 403; checklist cập nhật
- [ ] Demo script chạy được TỪ ĐẦU ĐẾN CUỐI trên máy dev bằng đúng các lệnh trong file (owner tự chạy thử 1 lần — đây là tiêu chí nghiệm thu chính của phase)
- [ ] Success story không còn claim nào vượt thực tế (rà từng mục: integration, metadata, con số)
- [ ] **Evidence:** 2 JSON mẫu + screenshot KPI; bộ 3-latency đưa thẳng vào chương kết quả luận văn

## 5 · Blocker rule

PERCENTILE_CONT quirk trên pooler/PG17 → thay bằng `ORDER BY ... LIMIT 2 OFFSET n/2` tự tính median Python-side (vẫn thuần SQL fetch + aggregate client nhỏ, entry decisions ghi hạ cấp). Data demo chưa sinh được insight approved vì 19 dở → Task 1–2 vẫn nghiệm thu trên fixture seed giả; Task 3–4 đánh dấu blocked, handoff nêu rõ. Mọi blocker khác: STOP task, entry decisions, chuyển việc độc lập kế.
