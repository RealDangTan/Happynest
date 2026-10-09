"""Resolve evidence and validate grounding before any ACT portfolio mutation."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.insight import Insight
from app.schemas.action_support import (
    ActionDecisionSupport, ActionEvidence, DecisionSupportDraft, PracticeReference,
)
from app.services.act_practices import LIBRARY_VERSION, PRACTICES_BY_ID, reference_metadata


def load_act_evidence(db: Session, insight: Insight) -> list[ActionEvidence]:
    wanted: list[uuid.UUID] = []
    for raw in insight.evidence or []:
        try:
            evidence_id = uuid.UUID(str(raw))
        except (ValueError, TypeError, AttributeError):
            continue
        if evidence_id not in wanted:
            wanted.append(evidence_id)
    wanted = wanted[:10]
    if not wanted:
        return []
    rows = db.scalars(select(Evidence).where(
        Evidence.id.in_(wanted), Evidence.product_id == insight.product_id,
    )).all()
    by_id = {row.id: row for row in rows if row.product_id == insight.product_id and row.id in wanted}
    return [ActionEvidence(
        evidence_id=evidence_id, statement=by_id[evidence_id].statement[:1500],
        source_tool=by_id[evidence_id].source_tool,
    ) for evidence_id in wanted if evidence_id in by_id]


def build_decision_support(
    draft: DecisionSupportDraft, evidence: list[ActionEvidence], *,
    recommendation: str, rationale: str,
) -> ActionDecisionSupport:
    by_id = {item.evidence_id: item for item in evidence}
    if any(evidence_id not in by_id for evidence_id in draft.evidence_ids):
        raise ValueError("ACT cited evidence outside the reviewed insight and product")
    if draft.kind != "investigate" and not draft.evidence_ids:
        raise ValueError("ACT requires referenced evidence for mitigation or improvement")
    if any(ref.card_id not in PRACTICES_BY_ID for ref in draft.references):
        raise ValueError("ACT cited a practice outside the curated library")
    references = [PracticeReference(
        **reference_metadata(ref.card_id), application=ref.application,
    ) for ref in draft.references]
    return ActionDecisionSupport(
        library_version=LIBRARY_VERSION,
        basis_recommendation=recommendation, basis_rationale=rationale,
        kind=draft.kind,
        evidence=[by_id[evidence_id] for evidence_id in dict.fromkeys(draft.evidence_ids)],
        perspectives=draft.perspectives, references=references, source_gap=draft.source_gap,
        alternative=draft.alternative, tradeoff=draft.tradeoff,
        assumptions=draft.assumptions, success_criteria=draft.success_criteria,
        estimate_basis=draft.estimate_basis,
    )
