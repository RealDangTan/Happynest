# DELIVERY PHASE — EXECUTE PLAN (ACTIVE MISSION)

> **For agentic workers:** REQUIRED SUB-SKILL: dùng superpowers:executing-plans để thực thi từng plan theo pha. **Repo cấm subagent fan-out** (tín dụng LLM thấp — `00-index.md` §1): mọi thứ chạy inline trong session sở hữu. Steps dùng checkbox (`- [ ]`).
>
> **Goal:** Đưa hệ thống từ "API backend hoàn chỉnh" lên "sản phẩm end-to-end demo được": frontend Next.js/shadcn + 4 nhóm stub thành production + LangGraph HITL.
>
> **Architecture:** Contract-first vertical slices P0→P5 (spec §1); FE proxy `/api/*` về FastAPI giữ same-origin cookie; mỗi pha khép lại = 1 demo point.
>
> **Tech Stack:** Next.js App Router + Tailwind v4 + shadcn/ui preset `b4IdeDqtkJ` (radix) · TanStack Query · FastAPI/SQLAlchemy/LangGraph (đã có) · Supabase PG.
>
> **Spec:** [`delivery-design-spec.md`](delivery-design-spec.md) — plan này lập luận từ spec; executor đọc CẢ HAI.

## Global Constraints (nguyên văn từ spec §0 — áp cho mọi task)

- Deadline **~2026-10-22**; máy dev **8 GB RAM**; tín dụng LLM thấp → inline, không spawn subagent.
- **No Docker. Ever.** Windows native + Supabase session pooler.
- Không monorepo; single Next.js app trong `frontend/`.
- **PII boundary:** raw content không bao giờ ra khỏi biên sanitize — không vào prompt/log/trace/response mặc định/docs.
- Mọi lệch kế hoạch → entry dated `decisions.md` TRƯỚC khi làm tiếp.
- Commits nhỏ, conventional (`feat(frontend): …`), ký `Assisted-by: claude-code`.
- Lệnh shadcn luôn qua runner dự án: `pnpm dlx shadcn@latest …`.

## 1. Bảng pha

| Pha | Tuần | Nội dung | Plan chi tiết (viết khi nào, ai) | Owner | Demo point khi xong | Status |
|---|---|---|---|---|---|---|
| **P0** | T1 | Freeze contract; roadmap + index; Node ≥20.18.1; pointer trong `AGENTS.md`/`00-index.md` | Đã có: [contracts](delivery-contracts.md) · [FE-00](FE-00-index.md) · [FE-01](FE-01-init-scaffold.md) · [FE-02](FE-02-auth-shell.md) · [UF-00](UF-00-index.md) | cả hai | 2 session khởi động được | ☐ |
| **P1** | T1–2 | FE scaffold → auth/shell → feedback screens → analysis runs ∥ UF specs | FE-01, FE-02 ✅ · **FE-03, FE-04**: session FE viết NGAY TRƯỚC khi code màn tương ứng ∥ **UF-01→03**: session UF theo [UF-00](UF-00-index.md) | FE ∥ UF | CRUD feedback + trigger run từ UI | ☐ |
| **P1.4** | T2 | Cải tiến FE-03b theo feedback owner 2026-08-25: cột bật/tắt localStorage; registry nguồn BE nhẹ (`sources` + GET/POST/PATCH) + wizard đăng ký; import CSV map cột + preview (decisions cùng ngày là phê duyệt) | [FE-03b-source-columns-csv-map.md](FE-03b-source-columns-csv-map.md) — session FE làm NGAY sau FE-03, trước FE-04 | FE | Bảng tuỳ biến cột; đăng ký nguồn mới qua wizard; import CSV cột lệch tên vẫn vào đúng trường | ✅ xong 2026-08-26 |
| **P1.5** | T2–3 | Auth mở rộng: đăng ký email/mật khẩu (role mặc định `operations`) + Google OAuth (email lạ → tự tạo user `operations`) + logout đi kèm | **FE-08**: session FE viết NGAY TRƯỚC khi thực thi; điều kiện: FE-03 xong + owner có Google client ID/secret (hướng dẫn tự tạo: [`../google-oauth-setup.md`](../google-oauth-setup.md)) | FE | Tự đăng ký tài khoản và login Google được từ UI |
| **P2** | T3–4 | HITL production BE + review UI (mock→real) | **[13-hitl-langgraph.md](13-hitl-langgraph.md) đã có** (viết sớm 2026-08-25 — decisions cùng ngày) · **phần BE đã thực thi XONG 2026-08-25** (routes/graph/integration xanh + evidence script `backend/scripts/evidence_hitl_checkpoint_resume.py`) · **FE-05**: session FE viết trước khi code màn; điều kiện: UF-04 spec đã xong (UF đi trước 1 pha) | FE | Duyệt 1 feedback pending qua UI; checkpoint sống sót restart | ☐ |
| **P3** | T5 | Clustering engine + trang clusters | **[14-clusters-api.md](14-clusters-api.md) đã có** (viết sớm 2026-08-25) · **phần clusters của FE-06**: viết khi mount màn; điều kiện: UF-05 (phần clusters) xong | FE | Trang clusters hiện data thật | ☐ |
| **P4** | T6 | Insights + reports + dashboard đầy đủ | **[15-insights-api.md](15-insights-api.md), [16-reports-summary.md](16-reports-summary.md) đã có** (viết sớm 2026-08-25) · **phần còn lại FE-06**: viết khi mount màn | FE | Dashboard PM có chart thật | ☐ |
| **P5** | T7–8 | Polish `[tuỳ chọn]` + data demo + tư liệu báo cáo | Checklist §4 dưới | cả hai | Bản demo bảo vệ | ☐ |
| **P6** | T6–9 (∥/sau P4) | **Agent module** (series 17–20): substrate + migration 0007 + data demo planted-spike → toolbox 5 tool → graph LangGraph fully LLM-routed HITL (`/api/agent/*`) → closed-loop KPIs + demo script. Engine (18/19) vào sau khi P3 xong; Task 1–2 của 20 chỉ cần 17. Trễ deadline → P5 là nơi hy sinh trước, P6 là lõi luận văn không cắt | [17](17-agent-substrate-demo-data.md) · [18](18-agent-toolbox.md) · [19](19-agent-graph-hitl.md) · [20](20-closed-loop-kpis-demo.md) — viết sẵn 2026-08-26 (decisions cùng ngày) | AGENT | Demo bảo vệ: agent tự điều tra cụm nổi bật → đề xuất → người duyệt/reject → đo tác động | ☐ |

Thứ tự cứng: P0 → P1 → P1.5 → P2 → P3 → P4 → P5. Trong P1, FE-01→02→03→04 tuần tự; UF chạy song song theo UF-00. P1.5 chạy ngay sau FE-03 (trong P1, trước P2); nếu GCP credentials chưa sẵn sàng thì P1.5 trượt sang sau P2 mà không chặn HITL.

## 2. Lãnh thổ session (chống ghi đè — BẮT BUỘC)

| Vùng | Session UF (docs) | Session FE (build) |
|---|---|---|
| `docs/plans/UF-*` | ✅ viết/sửa | chỉ đọc |
| `docs/plans/FE-*`, `13–16-*` | chỉ đọc | ✅ viết/sửa |
| `frontend/` | 🚫 cấm | ✅ |
| `backend/` | 🚫 cấm | ✅ |
| `AGENTS.md` · `decisions.md` · `00-index.md` · file này | chỉ append/tick dòng mình, **re-read trước ghi** | chỉ append/tick dòng mình, **re-read trước ghi** |

Kèm theo: commit ngay sau mỗi bước; trước khi ghi file chung `git status` + đọc lại nội dung mới nhất; không bao giờ `git add .` (dùng đường dẫn tường minh — tree có thể chứa file của session kia).

Bổ sung 2026-08-26: lane thứ ba **session AGENT** sở hữu `docs/plans/17–20-*`, `backend/app/agents/`, `backend/scripts/generate_demo_dataset.py`, `backend/scripts/backfill_insight_embeddings.py` — hai lane còn lại chỉ đọc các vùng này. Lane AGENT KHÔNG thực thi migration khi một lane khác đang sửa `models/`/`alembic/` (phối hợp qua `docs/handoffs/`).

Cập nhật 2026-08-26 (thực thi P6): lãnh thổ code agent đổi thành **`backend/happynest_agent/`** theo owner directive "một folder riêng để kiểm soát" — chi tiết decisions.md 2026-08-26. Các vùng còn lại của lane giữ nguyên.

## 3. Quy tắc viết plan just-in-time

Mỗi plan viết trước pha phải theo đúng khuôn mẫu plan cũ của repo (như `09-analysis-runner-progress-api.md`):

```markdown
# <Số/tên> — <Phạm vi>
> Nguồn: delivery-design-spec.md §<mục> + delivery-contracts.md <C-mục> · Ngày viết
## 1. Bối cảnh & hiện trạng (verify bằng lệnh thật, ghi kết quả)
## 2. Mục tiêu pha + Non-goals
## 3. Tasks đánh số — mỗi task: Files / Steps checkbox / Verify (lệnh + kỳ vọng) / Commit msg đề xuất
## 4. Acceptance criteria (checkbox) + Evidence cần chụp cho luận văn
## 5. Blocker rule: fail sau nỗ lực hợp lý → STOP, ghi decisions.md, chuyển việc độc lập khác
```

Plan mới xong → cập nhật dòng pha tương ứng ở bảng §1 (re-read trước ghi).

## 4. Checklist tiến độ tổng

- [ ] P0 Contract freeze + hạ tầng plan + Node bump
- [ ] P1 FE vận hành trên API đã ship ∥ UF-01→03
- [ ] P1.5 Auth mở rộng (register + Google login + logout)
- [ ] P2 HITL end-to-end (BE graph + UI)
- [ ] P3 Clusters end-to-end
- [ ] P4 Insights + Reports + dashboard
- [ ] P5 Demo data + polish + evidence chụp đủ
- [ ] P6 Agent module end-to-end (substrate → toolbox → graph HITL → closed-loop KPIs)

Preconditions owner treo từ Phase 12: Node ≥20.18.1 (chặn FE-01) · rotate SECRET_KEY + reset password Supabase trước deploy prod (không chặn dev).

## 5. Rủi ro & đệm (mirror spec §8)

Checkpoint LangGraph×pooler quirk → S5 là bằng chứng, fallback review-không-graph + decisions.md · Hết tín dụng LLM → cap calls naming/insight (env, default 10/lượt), cache, reports thuần SQL · RAM 8GB → lúc code chỉ chạy 1 dev server, `pnpm build` định kỳ · Trễ → mọi mục P5 đánh dấu `[tuỳ chọn]` sẵn.
