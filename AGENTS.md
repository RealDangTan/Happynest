# AGENTS.md — AI Feedback Agent (Undergraduate Thesis)

Standing context for AI coding agents (Claude Code, Cursor, Codex, …) working in this repository. Read this file FIRST, then `docs/README.md`, then the active mission plan referenced below.

## Mandatory rule — all validation is run by the user

- **Agents must never run tests, test cases, or lint.** The user runs all validation personally. This applies to individual cases, full suites, type checks, verification builds, smoke checks, manual UI/API checks, and validation or benchmark scripts.
- Do not trigger these checks indirectly through wrapper scripts, package commands, hooks, CI, or another agent. This rule takes precedence over any validation steps in plans, skills, checklists, and other repository instructions.
- Complete the requested changes and hand them back to the user for validation. Leave verification pending until the user supplies results. Reading source files and reviewing the diff are allowed.

## Git workflow — work directly on main

- Use `main` for routine work. Switch to the existing `main` checkout before editing and integrate any new changes from `origin/main` while preserving local work.
- Create a branch, worktree, or pull request only when the user explicitly asks for one. When the user asks for a commit or push, commit on `main` and push to `origin/main` as requested.

## Project identity

- **Thesis (VI):** "AI Agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng về sản phẩm AI"
- **Thesis (EN):** AI Agent that aggregates, classifies, and detects problems from user feedback about AI products
- **Pipeline (target architecture):** PII sanitize → LLM classify → embed → cluster → trend/emerging/spike detection → evidence-backed insight → HITL review via LangGraph interrupt
- **Dataset:** mixed Vietnamese–English (code-switching). All NLP choices assume this.
- **Constraints:** 8 GB RAM dev machine · cheap VPS deploy target · deadline < 2 months from 2026-08-23.
## Repository map

```text
├── AGENTS.md                  # ← you are here
├── README.md                  # human-facing quickstart (Vietnamese)
├── .gitattributes             # line-ending hygiene (commit #1)
├── docs/
│   ├── plans/00-index.md      # việc còn mở; plan hoàn tất xem plan_report.md
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
└── frontend/                  # ACTIVE từ 2026-08-25: Next.js app (shadcn/ui preset b4IdeDqtkJ)
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
```

## Hard rules

1. **No Docker. Ever.** Not for dev, not as "temporary convenience".
2. **PII boundary:** raw content never enters prompts, logs, traces, test fixtures with real data, or `docs/`. Only `sanitized_content` crosses the sanitize boundary.
3. **Exact pins on day one** in `backend/pyproject.toml`; never add a library beyond the plan's list without logging justification (`tenacity` is pre-approved).
4. **Every deviation** (package conflict, missing apt package, provider quirk) → fix forward AND append dated entry to `docs/decisions.md`: context → decision → alternatives rejected → consequence.
5. **Commits:** small, conventional (`feat(auth): …`). Never commit `.env`, real keys, or raw feedback containing PII.
6. **Windows quirks:** run `uvicorn --reload` alone in its own terminal; never spawn subprocesses under reload; all shell/SQL files LF-only (enforced by `.gitattributes`).
7. **Scope discipline:** if the user reports that a milestone failed acceptance after honest effort, STOP that milestone, record the blocker in `docs/decisions.md`, continue independent milestones, and report at the end. Do not silently expand scope.
8. Spikes S1–S6 are validation evidence for the thesis. Keep their scripts and record outcomes supplied by the user, including when a fallback gets activated.
9. **UI/FE work REQUIRES FE skills:** any task touching UI / frontend design — component, page, layout, styling, design tokens, Figma→code — MUST invoke the relevant FE skill FIRST (`frontend-design`, `shadcn`, `figma:figma-design-to-code`, …) before writing any code. Never hand-roll UI without loading a skill.
10. **API checklist sync:** adding/changing/removing any endpoint, request/response schema, or auth guard → update [`docs/api-checklist.md`](docs/api-checklist.md) in the SAME commit (endpoint + method + auth + trạng thái + tác dụng). Wiring/renaming an API call on the FRONTEND → update its "Trên FE" / "Vị trí trên FE" columns too. The agent making the change updates the checklist itself — no reminder needed.

## Skills & multi-agent handoff
- **In-repo skills:** single source of truth is [`.agents/skills/`](.agents/skills/) (universal — Codex/Cursor/Gemini/Antigravity). `.claude/skills/` is a local NTFS junction pointing there so Claude Code still auto-loads them; it is gitignored — recreate after a fresh clone: `New-Item -ItemType Junction -Path .claude/skills -Target .agents/skills`. Add new skills ONLY under `.agents/skills/`; never keep copies in both places.
- Plan execution is **inline** in one session — no subagent fan-out (LLM API credit is limited, see `docs/plans/00-index.md` §1).
