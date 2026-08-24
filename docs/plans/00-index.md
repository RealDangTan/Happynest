# BACKEND FOUNDATION — PHÂN RÃ THỰC THI THEO PHASE

> **Nguồn gốc:** [`../backend-foundation-execute-plan.md`](../backend-foundation-execute-plan.md) v1.0 (**amendment v1.1: DB = Supabase**) · bối cảnh gốc: [`../../../AGENTS.md`](../../../AGENTS.md)
> **Cách dùng:** mỗi lần thực thi = đúng 1 phase. Làm xong tick checkbox trong file phase + cập nhật cột Status ở bảng dưới. Lệch kế hoạch → ghi entry dated vào [`../../../docs/decisions.md`](../../../docs/decisions.md) TRƯỚC khi làm tiếp.
> **Ngày phân rã:** 2026-08-23

---

## 1. Hiện trạng máy (đã khảo sát 2026-08-23)

| Hạng mục | Trạng thái | Ảnh hưởng |
|---|---|---|
| Git identity + commit #1 `.gitattributes` | ✅ Xong | — |
| Repo | Gần trống: chỉ có AGENTS.md, README.md, docs/ | Phải dựng toàn bộ |
| Database | 🔄 Chuyển sang **Supabase** (v1.1) — project chưa tạo | Phase 01 việc người dùng; thay cho PG-in-WSL2 gốc (xem decisions.md) |
| uv | ❌ Chưa cài (python hệ thống 3.11.9) | Phase 01 cài |
| Env vars Windows `STANZA_RESOURCES_DIR`, `PIP_CACHE_DIR` | ❌ Chưa đặt | Phase 01 đặt |
| Models stanza (vi, en) + spaCy `en_core_web_lg` | ❌ Chưa tải | Phase 01 tải |
| `.env` / `.env.example` | ❌ Chưa tồn tại | Phase 01 tạo example, người dùng điền key |
| Tín dụng API (OpenRouter) | ⚠️ Rất thấp (subagent từng lỗi 402) | Thực thi inline, không spawn subagent |

## 2. Bảng phase

| # | File | Phạm vi | Blocked by | Status | Commit |
|---|---|---|---|---|---|
| 01 | [01-preconditions-environment.md](01-preconditions-environment.md) | §3 preconditions + §5 env contract + cài uv/pyproject pins | — | ✅ 2026-08-24 | `chore(env): pin deps day one, add .env.example` |
| 02 | [02-spikes-core-s1-s2-s3-s6.md](02-spikes-core-s1-s2-s3-s6.md) | §8 spike S1, S2, S3, S6 | 01 (S3/S6 cần PG) | ✅ 2026-08-24 (S4/S5 dời phase 10) | `test(spikes): add S1-S3,S6 evidence scripts and record outcomes` |
| 03 | [03-repo-skeleton-models-migrations.md](03-repo-skeleton-models-migrations.md) | §4 layout + §6 models + Alembic | 01 | ✅ 2026-08-24 | `feat(db): app skeleton, all core models, alembic baseline` |
| 04 | [04-auth-rbac.md](04-auth-rbac.md) | Auth + RBAC | 03 | ✅ 2026-08-24 | `feat(auth): oauth2 password flow, jwt cookie, role guard, seed users` |
| 05 | [05-feedback-ingestion.md](05-feedback-ingestion.md) | Ingestion POST/CSV/list/detail | 03, 04 | ✅ 2026-08-24 | `feat(feedback): manual post, csv import, paginated list/detail` |
| 06 | [06-pii-presidio-service.md](06-pii-presidio-service.md) | Presidio sanitize + wiring | 05, 01 (models đã tải) | ✅ 2026-08-24 | `feat(pii): presidio sanitize service wired into ingestion` |
| 07 | [07-llm-client-classifier.md](07-llm-client-classifier.md) | LLM client + classifier + tracing | 03, 01 (key .env) | ✅ 2026-08-24 | code trong `feat(services)` 0df1e4b (sweep phiên song song) + `test(llm): …` |
| 08 | [08-embedder-pgvector-similarity.md](08-embedder-pgvector-similarity.md) | Embedder + `/similar` | 03, 01 (key .env) | ✅ 2026-08-24 | `feat(embedding): embedder service, vector storage, similar endpoint` |
| 09 | [09-analysis-runner-progress-api.md](09-analysis-runner-progress-api.md) | Batch runner + progress API | 06, 07, 08 | ✅ 2026-08-25 | `feat(analysis): idempotent batch runner, run progress endpoints` |
| 10 | [10-spikes-late-s4-s5.md](10-spikes-late-s4-s5.md) | §8 spike S4, S5 | 03, 01 (PG) | ✅ 2026-08-24 | `test(spikes): S4/S5 evidence scripts, outcomes 6/6 PASS` |
| 11 | [11-test-suite-polish.md](11-test-suite-polish.md) | Suite pytest hoàn thiện | 04–09 | ⬜ | `test(suite): …` |
| 12 | [12-definition-of-done-sweep.md](12-definition-of-done-sweep.md) | §9 DoD sweep + docs cuối | Tất cả | ⬜ | `docs(dod): …` |

Thứ tự chạy = đúng mốc §10.8 của execute plan: **01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12**.

Đồ thị phụ thuộc rút gọn:

```text
01 ─┬─ 02 (S3/S6 đợi PG thật) ────────────────┐
    ├─ 03 ─┬─ 04 ─ 05 ─ 06 ─┐                 │
    │      ├─ 07 ────────────┼─ 09 ─ 11 ─ 12   │
    │      ├─ 08 ────────────┘                 │
    │      └─ 10 (S5 cần PG)                   │
    └─ (việc người dùng: Supabase project, .env, Langfuse) ─┴─ chặn S3/S6/S5 + mọi verify cần DB (cần internet)
```

## 3. Quy tắc làm việc chung (áp cho mọi phase)

1. **Mỗi phase ≥ 1 conventional commit** (`feat(auth): …`, `fix(db): …`), nhỏ, không commit `.env` hay key thật.
2. **Blocker rule (§10.6):** phase fail sau nỗ lực hợp lý → STOP phase đó, ghi blocker vào `docs/decisions.md`, chuyển sang phase độc lập khác, báo cáo cuối phiên.
3. **Deviation rule:** mọi lệch (conflict package, thiếu apt package, quirk provider) → fix forward + entry dated theo format trong `decisions.md`.
4. **Không Docker** dưới mọi hình thức. Dev = FastAPI native Windows + **Supabase** managed PostgreSQL (v1.1).
9. **Anti-pause Supabase:** free tier tự pause sau 7 ngày low-activity — mỗi tuần mở dashboard hoặc chạy ≥1 query. DB cần internet mọi phiên làm việc.
5. **PII boundary:** raw content không bao giờ vào prompt, log, trace, docs. Chỉ `sanitized_content` ra khỏi biên sanitize.
6. **Windows quirks:** `uvicorn --reload` chạy RIÊNG một terminal, không spawn subprocess dưới reload; mọi file `.sh`/`.sql` LF-only (`.gitattributes` đã ép).
7. **Pin đúng ngày đầu** trong `backend/pyproject.toml`; thêm thư viện ngoài danh sách §1 → phải log lý do (`tenacity` đã được duyệt sẵn).
8. **Không spawn subagent** khi thực thi (tín dụng API thấp) — làm inline.

## 4. Checklist tiến độ tổng

- [x] 01 Môi trường + preconditions
- [x] 02 Spike S1/S2/S3/S6
- [x] 03 Skeleton + models + migrations
- [x] 04 Auth + RBAC
- [x] 05 Ingestion
- [x] 06 Presidio PII
- [x] 07 LLM client + classifier
- [x] 08 Embedder + similarity
- [x] 09 Analysis runner
- [x] 10 Spike S4/S5
- [ ] 11 Test suite polish
- [ ] 12 DoD sweep
