"""Behavioral checks for API measurements and the telemetry PII boundary."""

import json
import logging
import uuid

from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("METRICS_TOKEN", "test-machine-token")
    monkeypatch.setenv("OBSERVABILITY_LOG_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    return app, TestClient(app, raise_server_exceptions=False)


def scrape(client):
    return client.get("/metrics", headers={"Authorization": "Bearer test-machine-token"})


def test_scrape_requires_machine_token_not_query_or_cookie(monkeypatch, tmp_path):
    _, client = make_client(monkeypatch, tmp_path)
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics?token=test-machine-token").status_code == 401
    client.cookies.set("access_token", "test-machine-token")
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
    response = scrape(client)
    assert response.status_code == 200
    assert "happynest_http_requests_total" in response.text
    get_settings.cache_clear()


def test_unconfigured_scrape_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("METRICS_TOKEN", "")
    monkeypatch.setenv("OBSERVABILITY_LOG_DIR", str(tmp_path))
    get_settings.cache_clear()
    client = TestClient(create_app())
    assert client.get("/metrics").status_code == 404
    get_settings.cache_clear()


def test_requests_use_route_templates_and_never_log_input(monkeypatch, tmp_path):
    app, client = make_client(monkeypatch, tmp_path)

    @app.post("/api/_obs/items/{item_id}")
    def item(item_id: str):
        return {"ok": True}

    secret = "synthetic-private-payload"
    ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    for item_id in ids:
        response = client.post(
            f"/api/_obs/items/{item_id}?q={secret}",
            json={"feedback": secret},
            headers={"Authorization": secret, "X-Request-ID": secret},
        )
        assert response.status_code == 200
        uuid.UUID(response.headers["X-Request-ID"])
    client.get(f"/api/not-found/{secret}")
    metrics = scrape(client).text
    assert 'route="/api/_obs/items/{item_id}"' in metrics
    assert 'route="__unmatched__"' in metrics
    assert all(item_id not in metrics for item_id in ids)
    logs = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert secret not in logs
    assert all(item_id not in logs for item_id in ids)
    events = [json.loads(line) for line in logs.splitlines()]
    assert any(row.get("event") == "http_request" and row.get("status_code") == 404 for row in events)
    get_settings.cache_clear()


def test_unhandled_error_records_500_without_exception_payload(monkeypatch, tmp_path):
    app, client = make_client(monkeypatch, tmp_path)

    @app.get("/api/_obs/error")
    def error():
        raise ValueError("synthetic-secret-in-exception")

    response = client.get("/api/_obs/error")
    assert response.status_code == 500
    assert 'route="/api/_obs/error",status_code="500"' in scrape(client).text
    logs = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert "synthetic-secret-in-exception" not in logs
    assert '"error_type": "ValueError"' in logs
    get_settings.cache_clear()


def test_api_timing_excludes_background_work(monkeypatch, tmp_path):
    from app.core import observability

    clock = [0.0]
    monkeypatch.setattr(observability, "perf_counter", lambda: clock[0])
    app, client = make_client(monkeypatch, tmp_path)

    def job():
        clock[0] = 100.0

    @app.get("/api/_obs/background")
    def background(tasks: BackgroundTasks):
        tasks.add_task(job)
        clock[0] = 0.02
        return {"accepted": True}

    assert client.get("/api/_obs/background").status_code == 200
    metrics = scrape(client).text
    assert 'happynest_http_request_duration_seconds_sum{method="GET",route="/api/_obs/background"} 0.02' in metrics
    assert "happynest_http_requests_in_progress 0.0" in metrics
    get_settings.cache_clear()


def test_json_formatter_drops_free_text_and_unknown_extras():
    from app.core.logging import SafeJsonFormatter

    record = logging.LogRecord("app.worker", logging.ERROR, __file__, 42, "secret=%s", ("private",), None)
    record.feedback_text = "private"
    record.error = "private"
    record.request_id = "private"
    data = json.loads(SafeJsonFormatter().format(record))
    assert "private" not in json.dumps(data)
    assert data["event"] == "application_log"
    assert data["level"] == "ERROR"


def test_llm_metrics_capture_attempts_tokens_and_errors():
    from app.core.observability import Telemetry

    monitor = Telemetry()
    monitor.record_llm(call_type="enrich", latency_ms=250, prompt_tokens=20, completion_tokens=5)
    monitor.record_llm(call_type="enrich", latency_ms=100, error=True)
    metrics = monitor.render().decode()
    assert 'happynest_llm_calls_total{call_type="enrich",outcome="ok"} 1.0' in metrics
    assert 'happynest_llm_calls_total{call_type="enrich",outcome="error"} 1.0' in metrics
    assert 'happynest_llm_tokens_total{call_type="enrich",direction="input"} 20.0' in metrics
    assert 'happynest_llm_call_duration_seconds_sum{call_type="enrich"} 0.35' in metrics


def test_llm_metrics_preserve_understand_and_act_call_types():
    from app.core.observability import Telemetry
    from app.models.enums import LlmCallType

    monitor = Telemetry()
    monitor.record_llm(call_type=LlmCallType.plan, latency_ms=1)
    monitor.record_llm(call_type=LlmCallType.act_generate, latency_ms=1)
    metrics = monitor.render().decode()
    assert 'call_type="plan"' in metrics
    assert 'call_type="act_generate"' in metrics


def test_pipeline_error_is_measured_and_run_context_is_reset():
    import pytest
    from app.core.logging import run_id_context
    from app.core.observability import Telemetry

    monitor = Telemetry()
    with pytest.raises(ValueError):
        with monitor.operation("understand", uuid.uuid4()):
            raise ValueError("synthetic-private-error")
    assert run_id_context.get() is None
    assert 'happynest_pipeline_executions_total{outcome="error",pipeline="understand"} 1.0' in monitor.render().decode()


def test_snapshot_failure_keeps_last_counts_and_marks_data_unavailable(monkeypatch):
    from app.core import observability

    monitor = observability.Telemetry()
    monkeypatch.setattr(observability, "load_pipeline_snapshot", lambda: [("listen", "completed", 2, 7)])
    monitor.refresh_snapshot()
    assert 'happynest_pipeline_processed_feedbacks 7.0' in monitor.render().decode()
    monkeypatch.setattr(observability, "monotonic", lambda: float("inf"))

    def unavailable():
        raise RuntimeError("synthetic-private-db-error")

    monkeypatch.setattr(observability, "load_pipeline_snapshot", unavailable)
    monitor.refresh_snapshot()
    metrics = monitor.render().decode()
    assert 'happynest_pipeline_processed_feedbacks 7.0' in metrics
    assert 'happynest_database_snapshot_available 0.0' in metrics
