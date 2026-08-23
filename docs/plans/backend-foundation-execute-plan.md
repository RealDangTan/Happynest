# BACKEND FOUNDATION EXECUTION PLAN

> **Thesis:** AI Agent tổng hợp, phân loại và phát hiện vấn đề từ phản hồi người dùng về sản phẩm AI
> **Standing context:** read [`AGENTS.md`](../../AGENTS.md) first — project identity, locked stack, hard rules live there.
> **Plan version:** v1.0 · authored 2026-08-23
> **Phạm vi:** CHỈ nền backend + hạ tầng. Không UI, không clustering/trend/insight production, không LangGraph production graph (chỉ spike xác minh).

---

## 0. ROLE & MISSION

You are the lead engineer for an undergraduate thesis project: **AI Agent for User Feedback Intelligence for AI-enabled Digital Products** (feedback mostly Vietnamese with English code-switching).

Your current mission: **build and verify the backend foundation ONLY** — repo, database, auth, ingestion, PII sanitization, LLM classification service, embeddings + pgvector, batch analysis job runner. Everything must run WITHOUT Docker: FastAPI natively on Windows, PostgreSQL inside WSL2 Ubuntu, future deploy = native Ubuntu VPS with systemd.

Do NOT build UI. Do NOT build clustering/trends/insights/reports. Those are later phases that will plug into the contracts you create here.

## 1. LOCKED DECISIONS (do not re-litigate, implement as specified)

| Area | Decision |
|---|---|
| Runtime | Python **3.12** pinned via `uv` (`.python-version` committed); Node 24 LTS exists but NO frontend this phase |
| Database | PostgreSQL 16 **inside WSL2 Ubuntu** (apt), host `localhost:5432`; extension `vector`; NO ANN index (dataset ≤1500 rows, exact scan only) |
| Vector | `pgvector>=0.5,<0.6` + SQLAlchemy 2.x; column `VECTOR(1536)`; always store `embedding_model` + `embedding_dim` per row |
| LLM | `openai` python SDK with `base_url` override; env-driven (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`); `temperature=0` |
| Structured output | Try `response_format={"type":"json_schema",...}`; on provider rejection/error fall back to prompt-JSON + Pydantic validate + ONE retry including the validation error; record which mode worked in Decision Log |
| Embeddings | OpenAI-compatible `/v1/embeddings` via same SDK client pattern; batch up to 2048 inputs/call; model name from `EMBEDDING_MODEL` env |
| PII | Microsoft Presidio + `StanzaNlpEngine("vi")` (+ regex recognizers EMAIL/URL/IP/VN-PHONE/CCCD-12-digit); operators replace with `<TYPE>` placeholders; analyzer instantiated ONCE at startup; raw PII NEVER sent to LLM, NEVER logged/traced |
| HITL trigger (compute now, graph later) | `requires_human_review = severity=="critical" OR safety_issue OR pii_detected OR confidence<0.60` stored on feedback row |
| Observability | Langfuse Cloud Hobby EU region; wrap every LLM/embedding call; `langfuse.shutdown()` on teardown; `LANGFUSE_TRACING_ENABLED=false` kill switch; PLUS permanent `llm_call_log` Postgres table |
| Auth | FastAPI-owned OAuth2 password flow; `pwdlib[argon2]`; JWT in httpOnly SameSite=Lax cookie; roles `pm` \| `operations`; Next.js will proxy later — expose clean `/api/*` routes |
| Migrations | Alembic with `include_object` filter excluding the 4 langgraph checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) from day one |
| Versions | Pin exact in `pyproject.toml`: fastapi, sqlalchemy>=2, alembic, pgvector 0.5.x, presidio-analyzer, presidio-anonymizer, stanza, spacy, openai, langgraph>=1.2,<2, langgraph-checkpoint-postgres 3.1.x, psycopg[binary,pool], langfuse v3, pwdlib[argon2], pyjwt, python-multipart, uvicorn>=0.30 |

## 2. STRICT SCOPE

### IN SCOPE (this phase)

1. Repo skeleton + git hygiene + env contract
2. Spike scripts S1–S6 (validation evidence, kept in `scripts/spikes/`)
3. Postgres-in-WSL2 bootstrap script + DB/user creation
4. FastAPI app skeleton: settings, health, CORS, exception handlers, logging
5. All core SQLAlchemy models + Alembic migrations
6. Auth (register disabled; login; current-user; role guard; seed script)
7. Feedback ingestion: manual POST + CSV import CLI/API
8. Presidio sanitization service
9. LLM client + taxonomy Pydantic models + classification step
10. Embedding client + storage + similarity query endpoint
11. Idempotent batch analysis runner + progress/status endpoints
12. `llm_call_log` writing + Langfuse tracing wrapper
13. pytest suite for the above (LLM calls mocked)
14. `docs/decisions.md` Decision Log seeded with every choice above

### OUT OF SCOPE (do NOT build, do NOT stub elaborately — 501 stubs allowed where listed)

- Any frontend/Next.js code (leave `frontend/README.md` placeholder only)
- HDBSCAN/KMeans clustering, cluster naming, trend/emerging/spike engines, priority score
- Insight generation, reports
- Production LangGraph graph (only the S5 spike script touches langgraph)
- Correction→few-shot loop
- Docker files of any kind (explicitly banned)

## 3. PRECONDITIONS (human/admin actions — verify, guide if missing)

Check these before coding; print instructions if any fail (do not silently proceed):

1. WSL2 Ubuntu 24.04 available (`wsl -l -v`) with systemd; `.wslconfig` capped (`memory=2GB`)
2. In WSL: `postgresql-16` + `postgresql-16-pgvector` packages exist (`apt-cache policy postgresql-16-pgvector`); if missing → build pgvector from source (`postgresql-server-dev-16`, `make && make install`) and RECORD it in Decision Log
3. Windows env vars set (user level OK): `STANZA_RESOURCES_DIR=D:\stanza_resources`, `PIP_CACHE_DIR=D:\.pip-cache`
4. Models downloaded: `stanza.download('vi')` and `('en')`; spaCy `en_core_web_lg` wheel installed directly
5. `.env` present with real values for: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL` (name confirmed by calling provider `/v1/embeddings` once), `DATABASE_URL`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`
6. Git identity configured; `.gitattributes` committed FIRST (already done — see commit #1)

## 4. REPO LAYOUT

```text
thesis/
├── .gitattributes              # DONE (commit #1)
├── .gitignore                  # .env, __pycache__, node_modules, *.pyc, .venv, dist/
├── .env.example                # THE contract (see §5)
├── README.md                   # setup: Windows dev + WSL2 PG + run commands
├── docs/
│   ├── decisions.md            # Decision Log (seeded; append every deviation)
│   └── api-notes.md
├── infra/
│   ├── wsl_pg_setup.sh         # apt install, create db+user, enable systemd svc (idempotent)
│   ├── setup_vps.sh            # placeholder skeleton now (Ubuntu native deploy, filled in later phase)
│   └── systemd/                # empty dir, placeholders later
├── backend/
│   ├── pyproject.toml          # uv project, requires-python ==3.12.*, exact pins
│   ├── .python-version         # 3.12
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              # include_object filter for langgraph tables
│   │   └── versions/
│   ├── app/
│   │   ├── main.py             # app factory, lifespan (analyzer, langfuse shutdown)
│   │   ├── core/config.py      # pydantic-settings reading .env
│   │   ├── core/security.py    # argon2 hash/verify, jwt encode/decode
│   │   ├── core/logging.py
│   │   ├── db/session.py       # engine, SessionLocal
│   │   ├── db/base.py
│   │   ├── models/             # user, feedback, cluster, insight, human_review,
│   │   │                       # analysis_run, correction_example, llm_call_log
│   │   ├── schemas/            # pydantic: taxonomy.py (enums), feedback.py, auth.py, ...
│   │   ├── services/
│   │   │   ├── presidio_service.py   # singleton analyzer; sanitize(text)->(sanitized, entities)
│   │   │   ├── llm_client.py         # chat_completion(messages, schema) with fallback chain
│   │   │   ├── embedder.py           # THE only module calling /v1/embeddings
│   │   │   ├── classifier.py         # prompt v1 + severity rubric + HITL rule
│   │   │   └── tracing.py            # langfuse wrappers + llm_call_log writer
│   │   ├── api/
│   │   │   ├── deps.py               # get_db, get_current_user, require_role
│   │   │   └── routes/               # auth, feedback, analysis, admin(stub)
│   │   └── jobs/
│   │       └── analysis_runner.py    # idempotent batch job
│   ├── scripts/
│   │   ├── seed_users.py
│   │   └── import_csv.py
│   └── tests/
│       ├── conftest.py               # sqlite-or-pg fixture, fake LLM client
│       ├── test_auth.py
│       ├── test_presidio_service.py  # fake PII with known ground truth
│       ├── test_classifier_idempotency.py
│       └── test_similarity_roundtrip.py   # @pytest.mark.integration (needs real PG)
├── scripts/spikes/             # s1..s6, kept as thesis evidence
└── frontend/README.md          # placeholder: "phase B1"
```

## 5. ENV CONTRACT (`.env.example` — complete, nothing else)

```ini
# --- App ---
APP_ENV=dev                      # dev|prod
SECRET_KEY=changeme-openssl-rand-hex-32
CORS_ORIGINS=http://localhost:3000

# --- Database (PG in WSL2, reached from Windows via localhost) ---
DATABASE_URL=postgresql+psycopg://thesis:thesis@localhost:5432/feedback_agent

# --- LLM provider (OpenAI-compatible) ---
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_MODEL=
EMBEDDING_DIM=1536

# --- Pipeline thresholds (configurable per thesis spec) ---
CLASSIFY_CONFIDENCE_REVIEW_BELOW=0.60
HIGH_SEVERITY_CONFIDENCE_REVIEW_BELOW=0.75

# --- Tracing (Langfuse Cloud EU) ---
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_TRACING_ENABLED=true    # false = offline demo kill switch
PROMPT_VERSION=v1
```

## 6. DATABASE MODELS (minimum fields; Alembic migration per logical group)

- `users`: id uuid pk, email unique, password_hash, role enum(pm, operations), created_at
- `feedbacks`: id uuid pk, external_ref (nullable), source str, created_at (event time), imported_at
  - `raw_content` text, `sanitized_content` text, `pii_detected` bool, `pii_entities` jsonb
  - `categories` jsonb (list), `ai_issue` enum nullable, `sentiment` enum nullable, `severity` enum nullable, `confidence` float nullable
  - `requires_human_review` bool default false, `review_status` enum(unreviewed, pending, approved, edited, rejected) default unreviewed
  - `embedding VECTOR(1536)` nullable, `embedding_model` str nullable, `embedding_dim` int nullable
  - `analysis_run_id` fk nullable
- `clusters`: id, name, summary, feedback_count, first_seen, last_seen, current_count, previous_count, growth_ratio, is_emerging, is_spike, suggested_priority — **table created now, unused this phase**
- `insights`: id, cluster_id fk, title, summary, suggested_action, evidence_ids jsonb, review_status — created now, unused
- `human_reviews`: id, feedback_id fk, original_value jsonb, edited_value jsonb, action enum(approve/edit/reject), reason, reviewer_id fk, created_at — created now, unused
- `correction_examples`: id, feedback_id, original_prediction jsonb, corrected_value jsonb, reason, created_at — created now, unused
- `analysis_runs`: id, pipeline_version, llm_model, prompt_version, embedding_model, started_at, completed_at, status enum(running/completed/failed), processed_count, total_count, error
- `llm_call_logs`: id, analysis_run_id nullable, feedback_id nullable, call_type enum(classify/embed/name_cluster/generate_insight), prompt_version, model, latency_ms, prompt_tokens, completion_tokens, error nullable, created_at

Rules: `CREATE EXTENSION IF NOT EXISTS vector` inside the first migration via `op.execute()`. All enums as native PG enums via SQLAlchemy `Enum(name=...)`. Timestamps timezone-aware.

## 7. SERVICE CONTRACTS (module boundaries — later phases depend on THESE signatures)

```python
# services/presidio_service.py
def sanitize(raw: str) -> SanitizeResult  # {sanitized_text, pii_detected: bool, entities: list[dict]}

# services/llm_client.py
def chat_structured(system: str, user: str, schema: type[BaseModel]) -> BaseModel
# behavior: try json_schema response_format -> validate; on failure: prompt-injected JSON ->
# parse -> validate; ONE retry appending validator errors; raise LLMStructureError after;
# writes llm_call_logs row + langfuse span every call (input ALWAYS sanitized-only)

# services/embedder.py
def embed_texts(texts: list[str]) -> list[list[float]]     # batches <=2048, retries w/ backoff
def embed_one(text: str) -> list[float]

# services/classifier.py  (prompt_version recorded)
def classify_feedback(sanitized_text: str, few_shot: list[dict] | None = None) -> Classification
# Classification = categories, ai_issue, sentiment, severity, confidence, rationale(short)
# few_shot param exists NOW (empty usage) because correction-loop plugs into it later

# jobs/analysis_runner.py
def run_analysis(run_id: uuid) -> None
# picks feedbacks WHERE analysis_run_id IS NULL (idempotent/resumable),
# per item: classify -> compute requires_human_review -> embed -> UPDATE row;
# updates analysis_runs.processed_count every item; commits per item (crash-safe)
```

API routes (REST, prefix `/api`):

- `POST /api/auth/token` (OAuth2PasswordRequestForm → sets httpOnly cookie; also returns token for testing), `GET /api/auth/me`
- `POST /api/feedbacks` (single, role pm|operations), `POST /api/feedbacks/import-csv` (upload; columns: source,content,created_at), `GET /api/feedbacks` (paginated, filter by review_status/severity/category), `GET /api/feedbacks/{id}`
- `POST /api/analysis/runs` (creates run, launches background task), `GET /api/analysis/runs/{id}` (progress), `GET /api/analysis/runs/{id}/results`
- `GET /api/feedbacks/{id}/similar?k=5` — cosine nearest neighbors via pgvector (exact scan)
- `GET /api/health` (checks DB + reports which LLM structured-output mode is active)
- `501 stubs` with docstrings: clusters, insights, reviews, corrections, reports

## 8. SPIKES (run BEFORE building the corresponding production module; results → docs/decisions.md)

| # | Script | Question | Pass criterion | Fallback to record |
|---|---|---|---|---|
| S1 | s1_presidio_vi.py | Does StanzaNlpEngine("vi")+regex catch PII in 20 mixed VN-EN samples with planted fake PII? | ≥80% obvious-type recall (email/phone/CCCD), person names usable-with-caveat | Regex-only + documented limitation |
| S2 | s2_llm_schema.py | Does provider honor json_schema response_format? 10 calls | ≥9/10 valid | Prompt-JSON+validate+retry mode |
| S3 | s3_embedding_pgvector.py | Provider `/v1/embeddings` works? roundtrip through PG-in-WSL2? | self-match rank #1; record served model name + dims | Alternate embedding provider |
| S4 | s4_hdbscan_toy.py | sklearn HDBSCAN cosine sane on 200 toy vectors? | runs <5s, sensible noise on sweep | KMeans-primary trade-off note |
| S5 | s5_langgraph_interrupt.py | interrupt→server restart→resume with AsyncPostgresSaver? | resume OK, zero duplicated side effects | DB state machine note (production graph still later phase) |
| S6 | s6_parity.py | Windows-native backend ↔ PG-in-WSL2 end-to-end incl. Alembic + vector insert/query? | green | Move whole dev into WSL2 |

## 9. DEFINITION OF DONE (this phase)

- [ ] Fresh-machine path documented & true: WSL script → `uv sync` → `alembic upgrade head` → `seed_users` → `uvicorn app.main:app` boots green
- [ ] Login as both seeded roles; role-guarded route rejects wrong role (403)
- [ ] CSV import of 20 mixed VN-EN rows (with planted fake PII) succeeds
- [ ] `raw_content ≠ sanitized_content`; `pii_entities` populated; sanitized text visible via API, raw only with explicit flag
- [ ] One full `POST /api/analysis/runs` over those 20 rows completes: labels + severity + confidence + `requires_human_review` computed; embeddings stored with model+dim; crash mid-run → re-running resumes without duplicating work (test proves idempotency with mocked LLM)
- [ ] `GET /api/feedbacks/{id}/similar` returns ranked neighbors with cosine scores
- [ ] `llm_call_logs` populated; Langfuse traces visible in EU dashboard (only sanitized text — verified by inspecting one trace); kill switch env works
- [ ] All 6 spike scripts executed; outcomes + activated fallbacks written in docs/decisions.md
- [ ] pytest green except integration marks skipped without PG; integration tests pass against real PG
- [ ] No secrets in git history; `.env.example` complete; README covers Windows-dev + WSL-PG + run/test/deploy-placeholder

## 10. RULES OF ENGAGEMENT

1. Pin exact dependency versions on day one; never `latest`.
2. Windows quirks: run `uvicorn --reload` alone in its own terminal; never spawn subprocesses under reload; all shell scripts LF-only.
3. Raw PII never enters: prompts, logs, traces, or `docs/`. Only `sanitized_content` leaves the sanitize boundary.
4. Every deviation from this plan (package conflict, missing apt package, provider quirk) → fix forward AND append a dated entry to `docs/decisions.md` with reason + fallback chosen.
5. Commit discipline: small conventional commits per milestone (`feat(auth): ...`), never commit `.env`.
6. If a milestone's acceptance fails after honest effort, STOP that milestone, record blocker in decisions.md, continue with independent milestones, report at the end.
7. Do not add libraries beyond §1 pins without recording justification (e.g., `tenacity` for backoff is pre-approved).
8. Milestone order: §3 preconditions → S1/S2/S3/S6 spikes → repo skeleton+migrations → auth → ingestion → presidio service → llm client+classifier → embedder → analysis runner → S4/S5 spikes → tests polish → DoD sweep.
