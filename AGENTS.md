# AGENTS.md — AI Feedback Agent (Undergraduate Thesis)

Standing context for AI coding agents (Claude Code, Cursor, Codex, …) working in this repository. Read this file FIRST, then the active mission plan referenced below.

## Project identity

- **Thesis (VI):** "AI Agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng về sản phẩm AI"
- **Thesis (EN):** AI Agent that aggregates, classifies, and detects problems from user feedback about AI products
- **Pipeline (target architecture):** PII sanitize → LLM classify → embed → cluster → trend/emerging/spike detection → evidence-backed insight → HITL review via LangGraph interrupt
- **Dataset:** mixed Vietnamese–English (code-switching). All NLP choices assume this.
- **Constraints:** 8 GB RAM dev machine · cheap VPS deploy target · deadline < 2 months from 2026-08-23.

## ⚠️ CURRENT PHASE — Backend Foundation ONLY

The active mission is documented in **[docs/plans/backend-foundation-execute-plan.md](docs/plans/backend-foundation-execute-plan.md)** — read it before writing any code and follow its milestone order exactly.

Explicitly OUT OF SCOPE until a later phase is declared:

- Any frontend/UI code (Next.js comes later; leave `frontend/` untouched)
- Clustering / trend / emerging-topic / insight production code
- Production LangGraph graph and correction→few-shot loop
- **Docker of any kind — permanently banned** (dev = FastAPI native on Windows + **Supabase** managed PostgreSQL; prod = native Ubuntu VPS with systemd)

## Locked stack

Do NOT substitute any of these without a dated entry in `docs/decisions.md`.

| Concern | Choice |
|---|---|
| Runtime | Python **3.12** via `uv` (`backend/.python-version` committed) |
| Database | **Supabase** managed PostgreSQL 17 qua session pooler (`aws-0-<region>.pooler.supabase.com:5432`); extension `vector` trong schema `extensions`; NO ANN index (dataset ≤ 1500 rows) — *v1.1, xem decisions.md* |
| Vectors | `VECTOR(1536)`; OpenAI-compatible `/v1/embeddings`; store `embedding_model` + `embedding_dim` per row |
| LLM | `openai` SDK with `base_url` override; env-driven provider; `temperature=0` |
| Structured output | try `response_format json_schema` → fallback prompt-JSON + Pydantic validate + ONE retry |
| PII | Presidio + `StanzaNlpEngine("vi")` + regex recognizers (email/url/ip/VN-phone/CCCD); `<TYPE>` placeholders; analyzer instantiated once at startup |
| HITL trigger rule | `requires_human_review = severity=="critical" OR safety_issue OR pii_detected OR confidence<0.60` (compute now, graph later) |
| Auth | FastAPI OAuth2 password flow; `pwdlib[argon2]`; JWT in httpOnly SameSite=Lax cookie; roles `pm` \| `operations` |
| Tracing | Langfuse Cloud Hobby EU + permanent `llm_call_logs` Postgres table (vendor-independent evidence) |
| Migrations | Alembic with `include_object` filter excluding the 4 langgraph checkpoint tables from day one |

## Repository map

```text
├── AGENTS.md                  # ← you are here
├── README.md                  # human-facing quickstart (Vietnamese)
├── .gitattributes             # line-ending hygiene (commit #1)
├── docs/
│   ├── plans/backend-foundation-execute-plan.md   # ACTIVE MISSION (§0–§10)
│   └── decisions.md           # Decision Log — every deviation goes here
├── infra/
│   ├── supabase_setup.md      # agent tạo: note setup 1 lần trên Supabase (extension vector, connection string)
│   ├── setup_vps.sh           # placeholder until deploy phase
│   └── systemd/
├── backend/                   # uv project — ALL application code lives here
│   ├── app/{core,db,models,schemas,services,api,jobs}
│   ├── alembic/
│   ├── scripts/               # seed_users.py, import_csv.py
│   └── tests/
├── scripts/spikes/            # S1–S6 validation scripts, kept as thesis evidence
└── frontend/                  # placeholder only — do not touch this phase
```

## Environment contract

- `.env.example` at repo root is THE single source of truth for required variables. Copy to `backend/.env`, fill real values, never commit it.
- Windows user-level env vars: `STANZA_RESOURCES_DIR=D:\stanza_resources`, `PIP_CACHE_DIR=D:\.pip-cache`.
- Models pre-downloaded before first run: `stanza.download('vi')` + `('en')`; spaCy `en_core_web_lg` wheel installed directly.
- Database URL shape (session pooler — KHÔNG dùng transaction pooler :6543 vì phá prepared statements của Alembic):
  `postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
- Free tier Supabase tự pause sau 7 ngày low-activity → mỗi tuần mở dashboard hoặc chạy ≥1 query.

## Commands

```bash
# one-time (trình duyệt): tạo Supabase project → lấy session-pooler connection string
# Dashboard → Connect → Session pooler; dán vào backend/.env (DATABASE_URL)

# backend (Windows terminal, from backend/)
uv sync                          # install pinned deps
uv run alembic upgrade head      # migrations (creates vector extension too)
uv run python scripts/seed_users.py
uv run uvicorn app.main:app --reload    # run ALONE in its own terminal (Windows quirk)

# tests
uv run pytest                    # unit suite (LLM mocked)
uv run pytest -m integration     # requires real PG reachable
```

## Hard rules

1. **No Docker. Ever.** Not for dev, not as "temporary convenience".
2. **PII boundary:** raw content never enters prompts, logs, traces, test fixtures with real data, or `docs/`. Only `sanitized_content` crosses the sanitize boundary.
3. **Exact pins on day one** in `backend/pyproject.toml`; never add a library beyond the plan's list without logging justification (`tenacity` is pre-approved).
4. **Every deviation** (package conflict, missing apt package, provider quirk) → fix forward AND append dated entry to `docs/decisions.md`: context → decision → alternatives rejected → consequence.
5. **Commits:** small, conventional (`feat(auth): …`). Never commit `.env`, real keys, or raw feedback containing PII.
6. **Windows quirks:** run `uvicorn --reload` alone in its own terminal; never spawn subprocesses under reload; all shell/SQL files LF-only (enforced by `.gitattributes`).
7. **Scope discipline:** if a milestone's acceptance fails after honest effort, STOP that milestone, record the blocker in `docs/decisions.md`, continue independent milestones, report at the end. Do not silently expand scope.
8. Spikes S1–S6 are validation evidence for the thesis — keep their scripts and record outcomes even when a fallback gets activated.

## Skills & multi-agent handoff

- **Handoff protocol (binding for every agent):** before starting AND before ending any session, follow [`.claude/skills/agent-handoff/SKILL.md`](.claude/skills/agent-handoff/SKILL.md) — check/leave append-only records in [`docs/handoffs/`](docs/handoffs/), sign commits with `Assisted-by: <agent-name>`, verify incoming claims (`git log`, tests) before trusting them.
- **In-repo skills:** `.claude/skills/` (Claude Code auto-loads) and `.agents/skills/` (universal — Codex/Cursor/Gemini/Antigravity). Both directories are required-reading references; list them when planning work, don't duplicate their content elsewhere.
- Plan execution is **inline** in one session — no subagent fan-out (LLM API credit is limited, see `docs/plans/00-index.md` §1).
