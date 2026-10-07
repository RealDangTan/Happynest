"""Tests HAX trust — trace endpoint metadata-only (G4/G16) + ACT error surface (G14)
+ llm_budget trong progress (G9). API tests dùng DB thật (marker `integration`),
unit test ACT chạy offline thuần."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.analysis_run import AnalysisRun
from app.models.enums import LlmCallType, RunStatus, UserRole
from app.services import act_agent
from app.services.llm_client import LLMStructureError
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS


# --------------------------------------------------------------- unit (offline)


def test_act_generate_returns_generation_error(monkeypatch) -> None:
    """HAX G14: LLMStructureError KHÔNG nuốt im lặng — trả error string."""

    def _boom(*args, **kwargs):
        raise LLMStructureError("model omitted required field: functions")

    class _FakeInsight:
        title = "t"
        finding = "f"
        finding_confidence = 0.9
        hypothesis = {}
        affected_context = {}
        impact = []
        limitations = []
        evidence = []

    monkeypatch.setattr(act_agent, "chat_structured", _boom)
    created, skipped, err = act_agent.generate_actions(MagicMock(), _FakeInsight())
    assert created == []
    assert skipped == []
    assert err is not None
    assert err.startswith("LLMStructureError")
    assert len(err) <= 500


def test_run_progress_schema_has_llm_budget() -> None:
    from app.schemas.agent import RunProgressOut

    out = RunProgressOut.model_validate(
        {
            "iteration": 1,
            "max_iterations": 8,
            "last_tool": "aggregate_feedback",
            "llm_calls_used": 3,
            "llm_budget": get_settings().UNDERSTAND_LLM_BUDGET_PER_RUN,
            "evidence_count": 1,
        }
    )
    assert out.llm_budget >= 1


# ---------------------------------------------------------------- integration


@pytest.fixture()
def _trace_run():
    """1 AnalysisRun (running) + 2 LlmCallLog (ok/error) — dọn dẹp sau test."""
    from app.models.llm_call_log import LlmCallLog

    with SessionLocal() as db:
        run = AnalysisRun(
            pipeline_version="hax-test",
            llm_model="test-model",
            prompt_version="hax-test",
            embedding_model="test-embed",
            status=RunStatus.running,
        )
        db.add(run)
        db.flush()
        db.add(
            LlmCallLog(
                analysis_run_id=run.id,
                call_type=LlmCallType.plan,
                prompt_version="plan-v1",
                model="test-model",
                latency_ms=120,
                prompt_tokens=10,
                completion_tokens=4,
            )
        )
        db.add(
            LlmCallLog(
                analysis_run_id=run.id,
                call_type=LlmCallType.synthesize,
                prompt_version="syn-v1",
                model="test-model",
                latency_ms=999,
                error="x" * 500,
            )
        )
        db.commit()
        yield run
        db.query(LlmCallLog).filter(LlmCallLog.analysis_run_id == run.id).delete(
            synchronize_session=False
        )
        db.delete(run)
        db.commit()


def _login(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={
            "username": SEED_EMAILS[UserRole.pm],
            "password": TEST_PASSWORDS[UserRole.pm],
        },
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.integration
def test_trace_metadata_only(client, _trace_run) -> None:
    auth = _login(client)
    resp = client.get(f"/api/agent/runs/{_trace_run.id}/trace", headers=auth)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["run_id"] == str(_trace_run.id)
    items = body["items"]
    assert len(items) == 2
    # Metadata-only: KHÔNG prompt/response
    assert all(
        set(item.keys())
        == {
            "call_type",
            "status",
            "latency_ms",
            "prompt_tokens",
            "completion_tokens",
            "model",
            "prompt_version",
            "error",
            "created_at",
        }
        for item in items
    )
    by_status = {item["status"]: item for item in items}
    assert by_status["ok"]["call_type"] == "plan"
    assert by_status["ok"]["error"] is None
    assert by_status["ok"]["completion_tokens"] == 4
    assert by_status["error"]["call_type"] == "synthesize"
    assert len(by_status["error"]["error"]) == 200  # truncate error[:200]


@pytest.mark.integration
def test_trace_404_unknown_run(client) -> None:
    import uuid as _uuid

    auth = _login(client)
    resp = client.get(f"/api/agent/runs/{_uuid.uuid4()}/trace", headers=auth)
    assert resp.status_code == 404


@pytest.mark.integration
def test_trace_requires_auth(client) -> None:
    import uuid as _uuid

    resp = client.get(f"/api/agent/runs/{_uuid.uuid4()}/trace")
    assert resp.status_code == 401


@pytest.mark.integration
def test_status_progress_has_llm_budget(client, _trace_run) -> None:
    auth = _login(client)
    resp = client.get(f"/api/agent/runs/{_trace_run.id}", headers=auth)
    assert resp.status_code == 200, resp.text
    progress = resp.json()["progress"]
    assert progress is not None
    assert progress["llm_budget"] == get_settings().UNDERSTAND_LLM_BUDGET_PER_RUN
