"""Real API + PostgreSQL + LangGraph; only provider calls are mocked.

All inserted rows belong to a unique synthetic product/user and are removed.
No real feedback is passed to a provider, and no existing user is reseeded.
"""
import uuid
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.action import Action
from app.models.analysis_run import AnalysisRun
from app.models.decision_log import DecisionLog
from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.models.insight import Insight
from app.models.insight_review import InsightReview
from app.models.product import Product
from app.models.product_schema import ProductSchema
from app.models.taxonomy import Taxonomy
from app.models.user import User
from app.schemas.import_ import MappingProposalOut
from app.services import act_agent, import_service, llm_client
from app.services.terminal_flow import FlowWizard
from app.services.terminal_http import TerminalClient

pytestmark = pytest.mark.integration


def test_csv_three_gates_real_persistence_and_scoped_impact(tmp_path, monkeypatch):
    from app.jobs import analysis_runner
    from understand_agent import nodes
    from understand_agent.nodes import PlannerOut, EvaluateOut, InsightDraft

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected live provider call")
    monkeypatch.setattr(llm_client, "chat_structured", forbidden)
    proposal = MappingProposalOut.model_validate({"mappings": [
        {"source_field": source, "decision": "MAP", "target": target,
         "confidence": .95, "reason": "synthetic mapping", "needs_human_review": False}
        for source, target in [("message", "feedback_text"), ("date", "occurred_at")]
    ]})
    monkeypatch.setattr(import_service, "build_mapping_proposal", lambda *a, **k: proposal)
    enrichment = {
        "topics": ["performance"],
        "topic_scores": [{"id": "performance", "probability": 0.94}],
        "topic_confidence": 0.94,
        "uncategorized": False,
        "sentiment": "negative",
        "emotions": ["frustration"],
        "emotion_scores": [{"label": "frustration", "probability": 0.8}],
        "intent": "bug_report",
        "severity": "high",
        "safety_issue": False,
        "ai_issue": None,
        "confidence": 0.9,
        "rationale": "Synthetic slow app",
        "taxonomy_version": 1,
        "analysis_version": "enrich-v3",
    }

    monkeypatch.setattr(
        analysis_runner,
        "enrich_feedback",
        lambda text, labels, **kwargs: dict(enrichment),
    )
    monkeypatch.setattr(analysis_runner, "embed_one", lambda text: [1.] + [0.] * 1535)
    calls = {"planner": 0}
    def agent_llm(system, user, schema, **kwargs):
        assert "test@example.com" not in user
        if schema is PlannerOut:
            calls["planner"] += 1
            if calls["planner"] == 1:
                return PlannerOut(action="tool", tool="aggregate_feedback", params={"group_by": ["severity"]}, objective="Measure synthetic feedback")
            return PlannerOut(action="synthesize", objective="Summarize measured evidence")
        if schema is EvaluateOut:
            return EvaluateOut(sufficient_evidence=True)
        if schema is InsightDraft:
            evidence_ids = [e["evidence_id"] for e in json.loads(user)["evidence"]]
            return InsightDraft(title="Synthetic latency", finding="Two reports mention latency", finding_confidence=.9, affected_context={}, impact=["slow workflow"], limitations=["Synthetic sample"], evidence_ids=evidence_ids)
        raise AssertionError(schema)
    monkeypatch.setattr(nodes, "chat_structured", agent_llm)
    from tests.act_fixtures import support_draft
    # ea6535c: ACT proposal phải mang decision_support đủ điều kiện grounding,
    # nếu không generate_actions trả ACTGroundingError → 0 action.
    monkeypatch.setattr(act_agent, "chat_structured", lambda *a, **k: act_agent.ActProposalOut.model_validate({"functions": [{"function": "ENGINEERING", "relevance": .9, "recommendation": "Investigate latency", "rationale": "Synthetic evidence", "impact": 8, "effort": 3, "urgency": 8, "confidence": .9, "decision_support": support_draft()}]}))

    suffix = uuid.uuid4().hex
    email = f"terminal-{suffix}@example.test"
    csv = tmp_path / "mixed.csv"
    # Third record deliberately fails date validation; error must not echo it.
    csv.write_text("message,date\nỨng dụng rất chậm,2026-09-01T00:00:00Z\nThe app is slow,2026-09-02T00:00:00Z\nInvalid date,test@example.com\n", encoding="utf-8")
    with SessionLocal() as db:
        user = User(email=email, password_hash=hash_password("synthetic-test-password"))
        db.add(user)
        db.commit()
        db.refresh(user)
        uid = user.id
        other_product = Product(name=f"terminal-other-{suffix}", owner_id=uid)
        db.add(other_product)
        db.commit()
        db.refresh(other_product)
        other_pid = other_product.id
    client = TerminalClient("http://testserver")
    client.http.close()
    client.http = TestClient(app)
    inputs = iter([email, "new", f"terminal-test-{suffix}", str(csv), "y", "approve", "approve", "y", "batch", "y", "", "n", "Why slow? test@example.com", "y", "edit", "Latency test@example.com", "", "Synthetic review test@example.com", "y", "edit", "", "", "4", "", "", "Scope reduced test@example.com", "n", "30", "y"])
    outputs = []
    wizard = FlowWizard(client, input_fn=lambda _: next(inputs), password_fn=lambda _: "synthetic-test-password", output_fn=outputs.append, state_path=tmp_path / "session.json")
    try:
        wizard.run()
        pid = uuid.UUID(wizard.state["product_id"])
        iid = uuid.UUID(wizard.state["import_id"])
        sid = uuid.UUID(wizard.state["insight_id"])
        with SessionLocal() as db:
            imported = db.get(Import, iid)
            assert imported.report["imported"] == 2
            assert imported.report["failed"] == 1
            assert "test@example.com" not in str(imported.report)
            feedback = db.scalars(select(Feedback).where(Feedback.product_id == pid)).all()
            assert len(feedback) == 2
            assert all(f.ai_analysis and f.has_embedding for f in feedback)
            insight = db.get(Insight, sid)
            assert insight.status == "edited" and insight.evidence
            assert "test@example.com" not in insight.title
            run = db.get(AnalysisRun, uuid.UUID(wizard.state["agent_run_id"]))
            assert run.status.value == "completed"
            action = db.scalars(select(Action).where(Action.insight_id == sid)).one()
            assert action.impact == 8 and action.human_impact == 4
            assert action.status == "edited"
            logs = db.scalars(select(DecisionLog).where(DecisionLog.product_id == pid)).all()
            assert {r.subject_type.value for r in logs} == {"schema_mapping", "insight", "action"}
            assert all(r.reviewer_id == uid for r in logs)
            assert "test@example.com" not in str([(r.reason, r.human_value) for r in logs])
            # Mature only this test action to exercise the measurement branch.
            action.created_at = datetime.now(timezone.utc) - timedelta(days=10)
            db.commit()
        assert client.request("POST", "/api/impact-checks/run", json={"product_id": str(other_pid)})["results"] == []
        measured = client.request("POST", "/api/impact-checks/run", json={"product_id": str(pid)})
        assert len(measured["results"]) == 1
        assert client.request("POST", "/api/impact-checks/run", json={"product_id": str(pid)})["results"] == []
        assert "test@example.com" not in "\n".join(outputs)
    finally:
        client.close()
        pid = uuid.UUID(wizard.state["product_id"]) if wizard.state.get("product_id") else None
        with SessionLocal() as db:
            if pid:
                imports = db.scalars(select(Import).where(Import.product_id == pid)).all()
                paths = [Path(i.storage_path) for i in imports if i.storage_path]
                insight_ids = select(Insight.id).where(Insight.product_id == pid)
                run_ids = [uuid.UUID(wizard.state[k]) for k in ("analysis_run_id", "agent_run_id") if wizard.state.get(k)]
                db.query(DecisionLog).filter(DecisionLog.product_id == pid).delete(synchronize_session=False)
                db.query(InsightReview).filter(InsightReview.insight_id.in_(insight_ids)).delete(synchronize_session=False)
                db.query(Action).filter(Action.insight_id.in_(insight_ids)).delete(synchronize_session=False)
                for model in (Insight, Evidence, Feedback, Taxonomy, ProductSchema):
                    db.query(model).filter(model.product_id == pid).delete(synchronize_session=False)
                if run_ids:
                    db.query(AnalysisRun).filter(AnalysisRun.id.in_(run_ids)).delete(synchronize_session=False)
                    for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                        for rid in run_ids:
                            db.execute(text(f"DELETE FROM {table} WHERE thread_id = :tid"), {"tid": f"understand-{rid}"})
                db.query(Import).filter(Import.product_id == pid).delete(synchronize_session=False)
                db.query(Product).filter(Product.id == pid).delete(synchronize_session=False)
                for path in paths:
                    storage = Path(import_service.get_settings().IMPORT_STORAGE_DIR).resolve()
                    if path.resolve().is_relative_to(storage):
                        path.unlink(missing_ok=True)
            # Isolation 2026-10-22: products.owner_id → user — xoá product
            # (kể cả terminal-other) TRƯỚC khi xoá user.
            db.query(Product).filter(Product.owner_id == uid).delete(synchronize_session=False)
            db.query(User).filter(User.id == uid).delete(synchronize_session=False)
            db.commit()
