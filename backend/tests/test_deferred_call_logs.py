"""Capture real metadata writers without worker DB sessions or lost errors."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from app.models.enums import LlmCallType
from app.services import embedder, llm_client, tracing


def _attempt(factory, *, error=None):
    llm_client._record_attempt(
        name="synthetic", input_text_sanitized="synthetic safe text", output_text="",
        schema_name="EnrichmentOut", call_type=LlmCallType.enrich,
        prompt_version="jev-v1", model="synthetic", latency_ms=50,
        usage={"prompt": 10, "completion": 0}, error=error,
        feedback_id=None, analysis_run_id=None, session_factory=factory,
    )


def test_worker_captures_enrich_and_embed_metadata_with_attribution(monkeypatch):
    def forbidden():
        raise AssertionError("worker must not open a DB session")

    monkeypatch.setattr(tracing, "trace_llm_call", lambda **kwargs: None)
    monkeypatch.setattr(embedder, "_session_factory", forbidden)
    run_id, feedback_id = uuid4(), uuid4()
    with tracing.capture_call_logs(analysis_run_id=run_id, feedback_id=feedback_id) as logs:
        _attempt(forbidden, error="synthetic rate limit")
        embedder._log_call(latency_ms=90, prompt_tokens=5)
    assert len(logs) == 2
    assert [row["call_type"] for row in logs] == [LlmCallType.enrich, LlmCallType.embed]
    assert all(row["analysis_run_id"] == run_id and row["feedback_id"] == feedback_id for row in logs)
    assert logs[0]["error"] == "synthetic rate limit"
    assert logs[1]["latency_ms"] == 90
    assert all("synthetic safe text" not in str(row) for row in logs)


def test_capture_is_thread_local_and_restored_after_exception():
    ids = [uuid4(), uuid4()]

    def worker(fid):
        with tracing.capture_call_logs(feedback_id=fid) as logs:
            tracing.record_call_log(lambda: None, call_type=LlmCallType.embed,
                prompt_version="v1", model="test", latency_ms=7)
        return logs

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, ids))
    assert [[row["feedback_id"] for row in rows] for rows in results] == [[ids[0]], [ids[1]]]
    with tracing.capture_call_logs(feedback_id=ids[0]) as outer:
        with pytest.raises(ValueError):
            with tracing.capture_call_logs(feedback_id=ids[1]):
                raise ValueError("synthetic")
        tracing.record_call_log(lambda: None, call_type=LlmCallType.embed,
            prompt_version="v1", model="test", latency_ms=7)
    assert len(outer) == 1 and outer[0]["feedback_id"] == ids[0]


def test_standalone_metadata_is_still_committed_immediately():
    class Session:
        def __init__(self):
            self.rows, self.committed = [], False
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            return False
        def add(self, row):
            self.rows.append(row)
        def commit(self):
            self.committed = True

    session = Session()
    tracing.record_call_log(lambda: session, call_type=LlmCallType.enrich,
        prompt_version="jev-v1", model="test", latency_ms=70)
    assert session.committed and len(session.rows) == 1
    assert session.rows[0].latency_ms == 70


def test_parallel_first_calls_initialize_one_trace_exporter(monkeypatch):
    import sys
    import time
    from threading import Barrier
    from types import SimpleNamespace

    settings = tracing.get_settings()
    monkeypatch.setattr(settings, "LANGFUSE_TRACING_ENABLED", True)
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "synthetic")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "synthetic")
    monkeypatch.setattr(tracing, "_langfuse", None)
    barrier = Barrier(3)

    def build_exporter(**kwargs):
        time.sleep(.02)  # real SDK initialization can release the GIL
        return object()

    monkeypatch.setitem(sys.modules, "langfuse", SimpleNamespace(Langfuse=build_exporter))

    def first_call(_):
        barrier.wait(timeout=3)
        return tracing.get_langfuse()

    with ThreadPoolExecutor(max_workers=3) as pool:
        clients = list(pool.map(first_call, range(3)))
    assert all(client is clients[0] for client in clients)
