"""HTTP wizard behavior: no paid work/decisions without owner input."""
import json
import uuid
from types import SimpleNamespace

import httpx
import pytest


def test_http_timeout_does_not_retry_write():
    from app.services.terminal_http import TerminalClient, TerminalError

    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("private payload", request=request)
    client = TerminalClient("http://test", transport=httpx.MockTransport(handler))
    with pytest.raises(TerminalError) as exc:
        client.request("POST", "/api/agent/runs", json={"question": "private"})
    assert len(calls) == 1
    assert "private" not in str(exc.value)
    assert exc.value.uncertain


def test_resume_file_only_contains_identifiers(tmp_path):
    from app.services.terminal_flow import FlowWizard
    path = tmp_path / "session.json"
    wizard = FlowWizard(None, state_path=path)
    wizard.state = {"product_id": str(uuid.uuid4()), "question": "private", "token": "secret"}
    wizard.save()
    assert set(json.loads(path.read_text())) == {"product_id"}


def test_mapping_ambiguous_requires_explicit_resolution(tmp_path):
    from app.services.terminal_flow import FlowWizard
    inputs = iter(["approve", "remap", "feedback_text"])
    wizard = FlowWizard(None, input_fn=lambda _: next(inputs), state_path=tmp_path / "s.json")
    result = wizard.mapping_decisions({"mappings": [{"source_field": "message", "decision": "AMBIGUOUS", "confidence": .3, "reason": "unclear"}]})
    assert result == [{"source_field": "message", "action": "remap", "target_key": "feedback_text"}]


def test_understand_sanitizes_before_checkpoint(monkeypatch):
    from understand_agent import runner
    from app.services import presidio_service
    monkeypatch.setattr(presidio_service, "sanitize", lambda text: SimpleNamespace(sanitized_text=text.replace("test@example.com", "<EMAIL>")))
    monkeypatch.setattr(runner, "ensure_checkpointer_ready", lambda: True)
    seen = []
    monkeypatch.setattr(runner, "_run_graph", lambda payload, *_: seen.append(payload) or {})
    runner.submit_or_start(uuid.uuid4(), uuid.uuid4(), {"question": "ask test@example.com"})
    assert seen[0]["question"] == "ask <EMAIL>"


def test_impact_scope_limits_candidate_query():
    from app.services.impact_service import run_impact_checks
    queries = []
    db = SimpleNamespace(scalars=lambda stmt: queries.append(stmt) or SimpleNamespace(all=lambda: []))
    product_id = uuid.uuid4()
    assert run_impact_checks(db, product_id=product_id) == []
    compiled = queries[0].compile()
    assert product_id in compiled.params.values()
    assert "insights.product_id" in str(compiled)


def test_feedback_embedding_status_does_not_expose_vector():
    from app.models.feedback import Feedback
    feedback = Feedback(embedding=None)
    assert feedback.has_embedding is False
    feedback.embedding = [0.] * 1536
    assert feedback.has_embedding is True


def test_action_human_text_sanitized_before_persistence(monkeypatch):
    from app.api.routes import actions
    from app.schemas.action import HumanActionIn
    from app.services import presidio_service
    monkeypatch.setattr(presidio_service, "sanitize", lambda text: SimpleNamespace(sanitized_text=text.replace("test@example.com", "<EMAIL>")))
    monkeypatch.setattr(actions, "_load_insight", lambda *_: object())
    saved = []
    class StopAfterWrite(Exception): pass
    def commit(): raise StopAfterWrite()
    db = SimpleNamespace(add=saved.append, commit=commit)
    with pytest.raises(StopAfterWrite):
        actions.add_human_action(uuid.uuid4(), HumanActionIn(function="SUPPORT", recommendation="Contact test@example.com", impact=5, effort=3, urgency=5), db)
    assert saved[0].recommendation == "Contact <EMAIL>"


def test_impact_endpoint_requires_auth_and_product():
    from fastapi.testclient import TestClient
    from app.main import app
    response = TestClient(app).post("/api/impact-checks/run", json={"product_id": str(uuid.uuid4())})
    assert response.status_code == 401


def test_full_wizard_uses_http_gates_and_persists_ids(tmp_path):
    from app.services.terminal_http import TerminalClient
    from app.services.terminal_flow import FlowWizard
    pid, iid, rid, aid, insight, action = [str(uuid.uuid4()) for _ in range(6)]
    csv = tmp_path / "sample.csv"
    csv.write_text("message\nỨng dụng chậm\nThe app is slow\n", encoding="utf-8")
    records = []
    state = {"import": "profile_ready", "agent": "running", "generated": False}
    def handler(req):
        path = req.url.path
        records.append((req.method, path, req.content))
        body = json.loads(req.content) if req.headers.get("content-type") == "application/json" else {}
        data = {}
        if path.endswith("/token"): data = {"access_token": "test-secret"}
        elif path.endswith("/me"): data = {"role": "pm"}
        elif path == "/api/products": data = {"items": [{"id": pid, "name": "Test"}]}
        elif path == "/api/imports" and req.method == "POST": data = {"id": iid}
        elif path.endswith("/preview") and "/imports/" in path: data = {"source_row_count": 2, "column_profiles": []}
        elif path.endswith("/mapping/proposal"): state["import"] = "mapping_review"
        elif path.endswith("/mapping/decision"):
            assert body == {"decisions": [{"source_field": "message", "action": "approve"}]}
            state["import"] = "imported"
        elif path.endswith("/mapping"): data = {"mappings": [{"source_field": "message", "decision": "MAP", "target": "feedback_text", "confidence": .9, "reason": "text"}]}
        elif path == f"/api/imports/{iid}": data = {"id": iid, "product_id": pid, "status": state["import"], "report": {"imported": 2, "failed": 0}}
        elif path.endswith("/schema"): data = {"core_fields": []}
        elif path == "/api/analysis/runs/preview": data = {"selected_count": 2, "remaining_count": 0}
        elif path == "/api/analysis/runs" and req.method == "POST":
            assert body["import_id"] == iid and body["confirmed_item_count"] == 2
            data = {"run_id": rid}
        elif path == f"/api/analysis/runs/{rid}": data = {"status": "completed", "processed_count": 2, "total_count": 2, "import_id": iid}
        elif path.endswith("/results"): data = {"items": [], "total": 0}
        elif path == "/api/agent/runs": data = {"run_id": aid}
        elif path.endswith("/decision"):
            assert body["action"] == "approve"
            state["agent"] = "completed"
            data = {"final_status": "approved"}
        elif path == f"/api/agent/runs/{aid}": data = {"status": state["agent"], "pending_approval": {"insight_id": insight, "insight": {"title": "Slow app", "finding": "Slow feedback", "finding_confidence": .8}, "evidence": []} if state["agent"] == "running" else None}
        elif path == "/api/insights": data = {"items": [{"id": insight, "run_id": aid, "status": "approved"}]}
        elif path.endswith("/actions/generate"):
            state["generated"] = True
            data = {"actions_created": 1, "functions_skipped": []}
        elif path.endswith("/actions"): data = {"items": [{"id": action, "status": "proposed", "impact": 7, "effort": 3, "urgency": 8}] if state["generated"] else [], "matrix": {"quick_wins": [action]}}
        elif path == f"/api/actions/{action}":
            assert body["status"] == "accepted"
            data = {"id": action, "status": "accepted"}
        elif path == "/api/impact-checks/run":
            assert body == {"product_id": pid}
            data = {"window_days": 7, "results": []}
        return httpx.Response(200, json=data)
    inputs = iter(["pm@example.test", "1", str(csv), "y", "approve", "y", "batch", "y", "", "n", "Why slow?", "y", "approve", "", "y", "accept", "n", "30", "y"])
    client = TerminalClient("http://test", transport=httpx.MockTransport(handler))
    wizard = FlowWizard(client, input_fn=lambda _: next(inputs), password_fn=lambda _: "pw", output_fn=lambda _: None, state_path=tmp_path / "session.json", sleep_fn=lambda _: None)
    wizard.run()
    assert wizard.state["insight_id"] == insight
    assert f"/api/actions/{action}" in [path for _, path, _ in records]
    assert "test-secret" not in (tmp_path / "session.json").read_text()
    assert len([1 for m, p, _ in records if m == "POST" and p == "/api/imports"]) == 1


@pytest.mark.parametrize("status", [401, 409, 422, 500])
def test_http_error_never_replays_or_prints_input(status):
    from app.services.terminal_http import TerminalClient, TerminalError
    requests = []
    def handler(req):
        requests.append(req)
        return httpx.Response(status, json={"detail": [{"input": "private-original"}]})
    client = TerminalClient("http://test", transport=httpx.MockTransport(handler))
    with pytest.raises(TerminalError) as exc:
        client.request("PATCH", "/api/actions/example", json={"recommendation": "private-original"})
    assert len(requests) == 1
    assert "private-original" not in str(exc.value)
    assert exc.value.status == status


def test_upload_declined_mapping_never_calls_ai(tmp_path):
    from app.services.terminal_flow import FlowWizard, PauseFlow
    from app.services.terminal_http import TerminalClient
    pid, iid = str(uuid.uuid4()), str(uuid.uuid4())
    csv = tmp_path / "feedback.csv"
    csv.write_text("message\nThe app is slow\n")
    writes = []
    def handler(req):
        if req.method == "POST":
            writes.append(req.url.path)
            return httpx.Response(201, json={"id": iid})
        return httpx.Response(200, json={"id": iid, "product_id": pid, "status": "profile_ready"})
    inputs = iter([str(csv), "n"])
    wizard = FlowWizard(TerminalClient("http://test", transport=httpx.MockTransport(handler)), input_fn=lambda _: next(inputs), state_path=tmp_path / "s.json")
    wizard.state = {"product_id": pid}
    with pytest.raises(PauseFlow): wizard.listen()
    assert writes == ["/api/imports"]
    assert wizard.state["import_id"] == iid


def test_investigate_more_then_reject_reuses_run(tmp_path):
    from app.services.terminal_flow import FlowWizard
    from app.services.terminal_http import TerminalClient
    pid, rid, iid = [str(uuid.uuid4()) for _ in range(3)]
    writes = []
    def handler(req):
        if req.method == "POST":
            writes.append((req.url.path, json.loads(req.content)["action"]))
            return httpx.Response(200, json={"final_status": "investigating" if len(writes) == 1 else "rejected"})
        if req.url.path == "/api/insights":
            return httpx.Response(200, json={"items": [{"id": iid, "run_id": rid, "status": "pending"}]})
        return httpx.Response(200, json={"status": "running", "pending_approval": {"insight_id": iid, "insight": {}, "evidence": []}})
    inputs = iter(["investigate_more", "more evidence", "reject", "insufficient", "n"])
    wizard = FlowWizard(TerminalClient("http://test", transport=httpx.MockTransport(handler)), input_fn=lambda _: next(inputs), state_path=tmp_path / "s.json")
    wizard.state = {"product_id": pid, "agent_run_id": rid}
    wizard.understand()
    assert [action for _, action in writes] == ["investigate_more", "reject"]
    assert all(path == f"/api/agent/runs/{rid}/decision" for path, _ in writes)
    assert "insight_id" not in wizard.state


def test_no_act_for_rejected_insight(tmp_path):
    from app.services.terminal_flow import FlowWizard
    from app.services.terminal_http import TerminalClient
    pid, iid = str(uuid.uuid4()), str(uuid.uuid4())
    requests = []
    def handler(req):
        requests.append(req.method)
        return httpx.Response(200, json={"items": [{"id": iid, "status": "rejected"}]})
    wizard = FlowWizard(TerminalClient("http://test", transport=httpx.MockTransport(handler)), state_path=tmp_path / "s.json")
    wizard.state = {"product_id": pid, "insight_id": iid}
    wizard.actions()
    assert requests == ["GET"]


def test_analysis_count_change_requires_new_preview(tmp_path):
    from app.services.terminal_flow import FlowWizard
    from app.services.terminal_http import TerminalClient, TerminalError
    requests = []
    def handler(req):
        requests.append(req.url.path)
        if req.url.path.endswith("preview"):
            return httpx.Response(200, json={"selected_count": 5})
        return httpx.Response(409, json={"detail": {"code": "selection_changed"}})
    inputs = iter(["batch", "y"])
    wizard = FlowWizard(TerminalClient("http://test", transport=httpx.MockTransport(handler)), input_fn=lambda _: next(inputs), state_path=tmp_path / "s.json")
    wizard.state = {"import_id": str(uuid.uuid4())}
    with pytest.raises(TerminalError): wizard.analysis()
    assert requests == ["/api/analysis/runs/preview", "/api/analysis/runs"]
    assert "analysis_run_id" not in wizard.state


def test_pause_wait_does_not_cancel_job(tmp_path):
    from app.services.terminal_flow import FlowWizard, PauseFlow
    from app.services.terminal_http import TerminalClient
    requests = []
    def handler(req):
        requests.append(req.method)
        return httpx.Response(200, json={"status": "running"})
    def stop(_): raise KeyboardInterrupt()
    wizard = FlowWizard(TerminalClient("http://test", transport=httpx.MockTransport(handler)), state_path=tmp_path / "s.json", sleep_fn=stop)
    with pytest.raises(PauseFlow): wizard.wait("/api/analysis/runs/example")
    assert requests == ["GET"]


def test_resume_analysis_rejects_other_import(tmp_path):
    from app.services.terminal_flow import FlowWizard
    from app.services.terminal_http import TerminalClient, TerminalError
    wizard = FlowWizard(TerminalClient("http://test", transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"status": "completed", "import_id": str(uuid.uuid4())}))), input_fn=lambda _: pytest.fail("must reject before input"), state_path=tmp_path / "s.json")
    wizard.state = {"import_id": str(uuid.uuid4()), "analysis_run_id": str(uuid.uuid4())}
    with pytest.raises(TerminalError): wizard.analysis()


def test_import_date_error_does_not_echo_raw_column(monkeypatch):
    from app.services import import_service
    from app.models.import_ import Import
    monkeypatch.setattr(import_service.schema_registry, "get_active_schema", lambda *_: None)
    monkeypatch.setattr(import_service, "load_raw_import", lambda _: b"message,date\nInvalid date,test@example.com\n")
    row = Import(id=uuid.uuid4(), product_id=uuid.uuid4(), storage_path="synthetic")
    db = SimpleNamespace(commit=lambda: None)
    result = import_service.execute_import(db, row, {"message": "feedback_text", "date": "occurred_at"}, {})
    assert result["failed"] == 1
    assert "test@example.com" not in str(result)


def test_gate_three_edit_sends_human_scores_and_empty_act_is_valid(tmp_path):
    from app.services.terminal_flow import FlowWizard
    from app.services.terminal_http import TerminalClient
    pid, iid, aid = [str(uuid.uuid4()) for _ in range(3)]
    patches = []
    def handler(req):
        if req.url.path == "/api/insights":
            return httpx.Response(200, json={"items": [{"id": iid, "status": "approved"}]})
        if req.method == "PATCH":
            patches.append(json.loads(req.content))
            return httpx.Response(200, json={"id": aid, "impact": 8, "human_impact": 4})
        return httpx.Response(200, json={"items": [{"id": aid, "impact": 8}], "matrix": {}})
    inputs = iter(["edit", "", "", "0", "4", "", "", "narrow scope", "n"])
    wizard = FlowWizard(TerminalClient("http://test", transport=httpx.MockTransport(handler)), input_fn=lambda _: next(inputs), state_path=tmp_path / "s.json")
    wizard.state = {"product_id": pid, "insight_id": iid}
    wizard.actions()
    assert patches == [{"impact": 4, "override_reason": "narrow scope"}]


def test_act_zero_actions_does_not_force_a_human_decision(tmp_path):
    from app.services.terminal_flow import FlowWizard
    from app.services.terminal_http import TerminalClient
    pid, iid = str(uuid.uuid4()), str(uuid.uuid4())
    writes = []
    def handler(req):
        if req.url.path == "/api/insights":
            return httpx.Response(200, json={"items": [{"id": iid, "status": "approved"}]})
        if req.method == "POST":
            writes.append(req.url.path)
            return httpx.Response(200, json={"actions_created": 0, "functions_skipped": ["LEGAL"]})
        return httpx.Response(200, json={"items": [], "matrix": {}})
    inputs = iter(["y", "n"])
    wizard = FlowWizard(TerminalClient("http://test", transport=httpx.MockTransport(handler)), input_fn=lambda _: next(inputs), state_path=tmp_path / "s.json")
    wizard.state = {"product_id": pid, "insight_id": iid}
    wizard.actions()
    assert writes == [f"/api/insights/{iid}/actions/generate"]
