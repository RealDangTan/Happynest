"""ACT source integrity, evidence scoping and non-destructive generation."""

import json
import uuid
from types import SimpleNamespace

import pytest

from app.models.action import Action
from app.models.enums import BusinessFunction
from app.models.evidence import Evidence
from app.services import act_agent
from tests.act_fixtures import proposal_payload, support_draft


def insight_with(evidence_ids=None):
    return SimpleNamespace(
        id=uuid.uuid4(), product_id=uuid.uuid4(), title="Khó sửa lỗi AI",
        finding="Người dùng phản ánh khó chỉnh câu trả lời sai.",
        finding_confidence=0.8, hypothesis={"statement": "UX có thể là nguyên nhân", "confidence": 0.4},
        affected_context={}, impact=["task_failure"], limitations=["Mẫu nhỏ"],
        evidence=evidence_ids or [], status="approved",
    )


class MemorySession:
    """Database boundary double; real service, schemas and ORM actions are exercised."""

    def __init__(self, actions=(), evidence=()):
        self.actions = list(actions)
        self.evidence = list(evidence)

    def scalars(self, query):
        entity = query.column_descriptions[0]["entity"]
        rows = self.evidence if entity is Evidence else self.actions
        return SimpleNamespace(all=lambda: list(rows))

    def delete(self, action):
        self.actions.remove(action)

    def add(self, action):
        action.id = action.id or uuid.uuid4()
        self.actions.append(action)

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, action):
        pass


def existing_action(insight, status="proposed"):
    return Action(
        id=uuid.uuid4(), insight_id=insight.id, function=BusinessFunction.ENGINEERING,
        recommendation="Original", rationale="Reviewed", impact=7, effort=4,
        urgency=6, confidence=0.65, priority_score=6.3, status=status,
    )


def test_catalog_supplies_traceable_rules_without_model_controlled_urls():
    from app.services.act_practices import PRACTICES, catalog_for_prompt

    assert len(PRACTICES) == 18
    assert len({card.id for card in PRACTICES}) == 18
    assert len({card.lens for card in PRACTICES}) == 7
    assert all(card.url.startswith("https://") and card.section and card.limitations for card in PRACTICES)
    prompt_cards = catalog_for_prompt()
    assert {c["card_id"] for c in prompt_cards} == {c.id for c in PRACTICES}
    assert all("url" not in card for card in prompt_cards)


def test_act_schema_meets_strict_provider_object_requirements():
    from app.services.llm_client import _schema_for

    def check(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)

    check(_schema_for(act_agent.ActProposalOut))


def test_evidence_loader_excludes_other_products_and_unreferenced_evidence():
    from app.services.act_grounding import load_act_evidence

    wanted, foreign, unrelated = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    insight = insight_with([str(wanted), str(foreign), "invalid-id"])
    rows = [
        SimpleNamespace(id=wanted, product_id=insight.product_id, statement="Safe fact", source_tool="aggregate_feedback"),
        SimpleNamespace(id=foreign, product_id=uuid.uuid4(), statement="Other product", source_tool="aggregate_feedback"),
        SimpleNamespace(id=unrelated, product_id=insight.product_id, statement="Unrelated", source_tool="aggregate_feedback"),
    ]
    evidence = load_act_evidence(MemorySession(evidence=rows), insight)
    assert [str(e.evidence_id) for e in evidence] == [str(wanted)]
    assert evidence[0].statement == "Safe fact"


def test_support_hydrates_sources_from_catalog_and_preserves_original_text():
    from app.schemas.action_support import DecisionSupportDraft
    from app.services.act_grounding import build_decision_support

    support = build_decision_support(
        DecisionSupportDraft.model_validate(support_draft()), [],
        recommendation="Original action", rationale="Original rationale",
    )
    assert support.basis_recommendation == "Original action"
    assert support.basis_rationale == "Original rationale"
    correction = support.references[0]
    assert correction.url == "https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/"
    assert correction.section == "G9 — Support efficient correction"
    assert correction.application == "Thử cơ chế chỉnh sửa câu trả lời."


@pytest.mark.parametrize("mutation", ["unknown_source", "unknown_evidence", "no_evidence", "missing_brief", "duplicate_lens", "missing_source_gap"])
def test_invalid_proposal_preserves_existing_portfolio(monkeypatch, mutation):
    insight = insight_with()
    original = existing_action(insight)
    db = MemorySession([original])
    payload = proposal_payload()
    brief = payload["functions"][0]["decision_support"]
    if mutation == "unknown_source":
        brief["references"][0]["card_id"] = "invented-source"
    elif mutation == "unknown_evidence":
        brief["evidence_ids"] = [str(uuid.uuid4())]
    elif mutation == "no_evidence":
        brief["kind"] = "improve"
    elif mutation == "missing_brief":
        del payload["functions"][0]["decision_support"]
    elif mutation == "duplicate_lens":
        brief["perspectives"][1]["lens"] = "ux"
    else:
        brief["references"] = []

    def generated(*args, **kwargs):
        return act_agent.ActProposalOut.model_validate(payload)

    monkeypatch.setattr(act_agent, "chat_structured", generated)
    created, _, error = act_agent.generate_actions(db, insight)
    assert created == []
    assert error is not None
    assert db.actions == [original]


@pytest.mark.parametrize("status", ["edited", "accepted", "rejected"])
def test_regeneration_preserves_human_decisions(monkeypatch, status):
    insight = insight_with()
    original = existing_action(insight, status)
    db = MemorySession([original])
    monkeypatch.setattr(act_agent, "chat_structured", lambda *a, **kw: act_agent.ActProposalOut.model_validate(proposal_payload()))
    created, _, error = act_agent.generate_actions(db, insight)
    assert error is None
    assert created == []
    assert db.actions == [original]


def test_generate_includes_safe_evidence_and_persists_grounding(monkeypatch):
    evidence_id = uuid.uuid4()
    insight = insight_with([str(evidence_id)])
    row = SimpleNamespace(id=evidence_id, product_id=insight.product_id, statement="Users cannot correct answers", source_tool="aggregate_feedback")
    db = MemorySession(evidence=[row])

    def generated(system, user, schema, **kwargs):
        payload = json.loads(user)
        assert payload["insight"]["evidence"][0]["statement"] == "Users cannot correct answers"
        assert len(payload["best_practices"]) == 18
        assert kwargs["prompt_version"] == "act-v2"
        return schema.model_validate(proposal_payload([str(evidence_id)], "improve"))

    monkeypatch.setattr(act_agent, "chat_structured", generated)
    created, _, error = act_agent.generate_actions(db, insight)
    assert error is None
    assert len(created) == 1
    stored = created[0].decision_support
    assert stored["evidence"][0]["evidence_id"] == str(evidence_id)
    assert stored["kind"] == "improve"
    assert stored["references"][0]["url"].startswith("https://www.microsoft.com/")


def test_unmatched_sources_are_explicit_in_saved_support():
    from app.schemas.action_support import DecisionSupportDraft
    from app.services.act_grounding import build_decision_support

    draft = support_draft()
    draft.update(references=[], source_gap="Chưa có nguyên tắc phù hợp trong thư viện.")
    support = build_decision_support(DecisionSupportDraft.model_validate(draft), [], recommendation="Investigate", rationale="Limited evidence")
    assert support.references == []
    assert support.source_gap == "Chưa có nguyên tắc phù hợp trong thư viện."
