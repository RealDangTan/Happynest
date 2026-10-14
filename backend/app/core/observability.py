"""Small native Prometheus registry and PII-safe request/operation telemetry."""

import hmac
import logging
import uuid
from contextlib import contextmanager
from functools import wraps
from inspect import signature
from threading import Lock
from time import monotonic, perf_counter, time

from fastapi import HTTPException, Request
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

from app.core.logging import request_id_context, run_id_context
from app.models.enums import LlmCallType

logger = logging.getLogger("happynest.telemetry")
HTTP_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120)
JOB_BUCKETS = (0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600, 1800)
CALL_TYPES = {item.value for item in LlmCallType}


def load_pipeline_snapshot():
    """Read only aggregate operational state; never export tenants or content."""
    from sqlalchemy import text
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        db.execute(text("SET LOCAL statement_timeout = '2000ms'"))
        rows = db.execute(text("""
            SELECT CASE WHEN pipeline_version = 'understand-v1' THEN 'understand'
                        ELSE 'listen' END AS pipeline, status::text AS status,
                   count(*) AS runs, coalesce(sum(processed_count), 0) AS processed
            FROM analysis_runs GROUP BY 1, 2
        """)).all()
    return rows


class Telemetry:
    def __init__(self):
        self.registry = CollectorRegistry()
        opts = {"registry": self.registry}
        self.requests = Counter("happynest_http_requests_total", "Responses sent; labelled by route template.", ["method", "route", "status_code"], **opts)
        self.duration = Histogram("happynest_http_request_duration_seconds", "Time to final response body; excludes background jobs.", ["method", "route"], buckets=HTTP_BUCKETS, **opts)
        self.inflight = Gauge("happynest_http_requests_in_progress", "Requests whose response is not yet complete.", **opts)
        self.llm_calls = Counter("happynest_llm_calls_total", "Provider attempts since this process started, including retries.", ["call_type", "outcome"], **opts)
        self.llm_duration = Histogram("happynest_llm_call_duration_seconds", "Provider attempt latency.", ["call_type"], buckets=JOB_BUCKETS, **opts)
        self.tokens = Counter("happynest_llm_tokens_total", "Reported tokens; absent provider usage is not estimated.", ["call_type", "direction"], **opts)
        self.executions = Counter("happynest_pipeline_executions_total", "LISTEN invocations or active UNDERSTAND segments, not distinct runs.", ["pipeline", "outcome"], **opts)
        self.execution_duration = Histogram("happynest_pipeline_execution_duration_seconds", "Active invocation duration; excludes time between human decisions.", ["pipeline"], buckets=JOB_BUCKETS, **opts)
        self.runs = Gauge("happynest_pipeline_runs", "Persisted runs by state; running can include human review waits.", ["pipeline", "status"], **opts)
        self.processed = Gauge("happynest_pipeline_processed_feedbacks", "Persisted processed_count for LISTEN runs.", **opts)
        self.db_up = Gauge("happynest_database_snapshot_available", "Last operational snapshot query succeeded.", **opts)
        self.snapshot_at = Gauge("happynest_database_snapshot_timestamp_seconds", "Unix time of last successful aggregate snapshot.", **opts)
        self._snapshot_after = 0.0
        self._snapshot_lock = Lock()

    def render(self) -> bytes:
        return generate_latest(self.registry)

    def refresh_snapshot(self):
        with self._snapshot_lock:
            if monotonic() < self._snapshot_after:
                return
            self._snapshot_after = monotonic() + 30
            try:
                rows = load_pipeline_snapshot()
                self.runs.clear()
                processed = 0
                for pipeline, status, count, n_processed in rows:
                    if status not in {"running", "completed", "failed", "cancelled", "pending_approval"}:
                        status = "other"
                    self.runs.labels(pipeline, status).set(count)
                    if pipeline == "listen":
                        processed += n_processed
                self.processed.set(processed)
                self.db_up.set(1)
                self.snapshot_at.set(time())
            except Exception:
                self.db_up.set(0)
                logger.exception("Operational snapshot unavailable")

    def record_llm(self, *, call_type, latency_ms, prompt_tokens=None, completion_tokens=None, error=False, run_id=None):
        call_type = getattr(call_type, "value", call_type)
        call_type = call_type if call_type in CALL_TYPES else "other"
        outcome = "error" if error else "ok"
        self.llm_calls.labels(call_type, outcome).inc()
        self.llm_duration.labels(call_type).observe(max(latency_ms, 0) / 1000)
        for direction, value in (("input", prompt_tokens), ("output", completion_tokens)):
            if value is not None and value >= 0:
                self.tokens.labels(call_type, direction).inc(value)
        logger.log(logging.WARNING if error else logging.INFO, "Provider attempt", extra={
            "event": "llm_call", "call_type": call_type, "outcome": outcome,
            "duration_ms": latency_ms, "run_id": run_id or run_id_context.get(),
            "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
        })

    @contextmanager
    def operation(self, pipeline: str, run_id=None):
        token = run_id_context.set(str(run_id) if run_id else None)
        started = perf_counter()
        state = {"outcome": "ok"}
        try:
            yield state
        except BaseException as exc:
            state["outcome"] = "error"
            state["error_type"] = type(exc).__name__
            raise
        finally:
            duration = max(0, perf_counter() - started)
            outcome = state["outcome"]
            self.executions.labels(pipeline, outcome).inc()
            self.execution_duration.labels(pipeline).observe(duration)
            logger.log(logging.ERROR if outcome in {"failed", "error", "missing"} else logging.INFO,
                       "Pipeline invocation", extra={"event": "pipeline_execution", "pipeline": pipeline,
                        "outcome": outcome, "duration_ms": round(duration * 1000, 3), "error_type": state.get("error_type")})
            run_id_context.reset(token)


telemetry = Telemetry()


def observe_pipeline(pipeline):
    def decorate(function):
        parameters = signature(function)

        @wraps(function)
        def measured(*args, **kwargs):
            bound = parameters.bind(*args, **kwargs)
            with telemetry.operation(pipeline, bound.arguments.get("run_id")):
                return function(*args, **kwargs)
        return measured
    return decorate


class RequestTelemetryMiddleware:
    def __init__(self, app, monitor):
        self.app = app
        self.monitor = monitor

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/"):
            return await self.app(scope, receive, send)
        request_id = str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_context.set(request_id)
        started = perf_counter()
        method = scope["method"] if scope["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} else "OTHER"
        status_code = 500
        finished = False
        self.monitor.inflight.inc()

        def finish(error_type=None):
            nonlocal finished
            if finished:
                return
            finished = True
            route = getattr(scope.get("route"), "path", "__unmatched__")
            elapsed = max(0, perf_counter() - started)
            self.monitor.requests.labels(method, route, str(status_code)).inc()
            self.monitor.duration.labels(method, route).observe(elapsed)
            self.monitor.inflight.dec()
            logger.log(logging.ERROR if status_code >= 500 else logging.INFO, "Request finished", extra={
                "event": "http_request", "method": method, "route": route,
                "status_code": status_code, "duration_ms": round(elapsed * 1000, 3), "error_type": error_type,
            })

        async def measured_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message = dict(message)
                message["headers"] = list(message.get("headers", [])) + [(b"x-request-id", request_id.encode())]
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                finish()

        try:
            await self.app(scope, receive, measured_send)
        except BaseException as exc:
            finish(type(exc).__name__)
            raise
        finally:
            if not finished:
                finish("IncompleteResponse")
            request_id_context.reset(token)


def attach_observability(app, settings):
    app.add_middleware(RequestTelemetryMiddleware, monitor=telemetry)

    @app.get("/metrics", include_in_schema=False)
    def metrics(request: Request):
        if not settings.METRICS_TOKEN:
            raise HTTPException(404)
        provided = request.headers.get("authorization", "")
        if not hmac.compare_digest(provided.encode(), f"Bearer {settings.METRICS_TOKEN}".encode()):
            raise HTTPException(401, headers={"WWW-Authenticate": "Bearer"})
        telemetry.refresh_snapshot()
        return Response(telemetry.render(), headers={"Content-Type": CONTENT_TYPE_LATEST, "Cache-Control": "no-store"})
