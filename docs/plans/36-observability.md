# HappyNest Observability Implementation Plan

> **For agentic workers:** Use `test-driven-development` and `verification-before-completion`. Execute INLINE; no subagents. Preserve the existing uncommitted application work.

**Goal:** Give the owner a Grafana Cloud dashboard for API performance, safe searchable logs, host resources and pipeline execution, plus reproducible k6 evidence.

**Architecture:** FastAPI exports authenticated Prometheus metrics and an allowlisted rotating JSON log. Native Grafana Alloy scrapes locally and forwards metrics/logs to Grafana Cloud. Langfuse and Supabase remain the existing specialist dashboards.

**Tech Stack:** Python 3.12, pinned prometheus-client, native Alloy and k6; no Docker.

**Spec:** Owner request in this chat, 2026-10-14: set up the cloud-free observability approach discussed after repository inspection.

## Global constraints

- No raw feedback, request bodies, headers, query strings, exception messages or local variables in exported logs.
- Metric labels use route templates and bounded categories; request/run IDs belong only in logs.
- API duration ends when the response body is sent, excluding BackgroundTasks. UNDERSTAND duration measures each active graph segment, excluding time between human decisions.
- `/metrics` requires a dedicated Bearer machine token and is unavailable when its token is empty. No database credentials are sent to Grafana.
- Cloud onboarding requires the owner's signed-in free Grafana account. Finish local work independently of that step.

## Tasks

- [ ] Add failing behavior tests in `backend/tests/test_observability.py`: metrics token validation, route normalization, 500 accounting, background timing and PII-safe JSON.
- [ ] Add the metric registry/middleware and safe JSON formatter, configure settings, and integrate request, LLM and pipeline measurements. Verify with `uv run pytest tests/test_observability.py -q` and the existing unit suite.
- [ ] Add native Windows installation/start scripts, Alloy Windows/Linux configs, portable dashboard JSON and read-only k6 benchmark with exported summary. Validate Alloy with the installed binary and smoke-test k6 against the local backend.
- [ ] Update `.env.example`, API checklist, decision log and a Vietnamese operator guide. Keep all tokens/runtime files ignored.
- [ ] Connect the owner's free cloud stack when signed in; verify metrics/log ingestion and dashboard. Otherwise document the exact remaining account step without claiming cloud is live.
- [ ] Record test results, benchmark conditions and the append-only handoff; leave unrelated changes untouched.
