"""Synthetic VI/EN ACT walkthrough. Explicit --live uses configured MODEL_ACT.

Run from backend: uv run python scripts/e2e_act_best_practices.py --live [--keep]
Only artificial fixtures are created; by default this script removes its own rows.
--keep retains a clearly labelled demo product for reviewing Matrix/Stakeholders.
"""

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.action import Action
from app.models.analysis_run import AnalysisRun
from app.models.enums import RunStatus
from app.models.evidence import Evidence
from app.models.insight import Insight
from app.models.product import Product
from app.schemas.action_support import ActionDecisionSupport
from app.services.act_agent import generate_actions


CASES = (
    ("Answer quality / citation", "Trong mẫu nhân tạo 24 phản hồi, 9 phản hồi nói citation không kiểm chứng được.",
     "Citation failure may be related to retrieval; root cause is unconfirmed."),
    ("Latency / độ trễ", "Trong dữ liệu nhân tạo, 8/20 phản hồi phàn nàn chờ AI lâu, chưa có telemetry p95.",
     "Model latency may contribute; network and UI waiting states are not ruled out."),
    ("Correction / sửa lỗi", "Trong mẫu nhân tạo, 6/20 phản hồi nói khó sửa câu trả lời AI dù đã phát hiện lỗi.",
     "Correction friction may increase task abandonment; causal impact is unconfirmed."),
    ("Missing evidence / thiếu bằng chứng", None,
     "Có ý kiến chi phí AI cao nhưng chưa thu thập dữ liệu chi phí hoặc phản hồi xác minh."),
)

EXPECTED_PRACTICES = (
    {"discovery-assumptions", "hax-explanation", "hax-capabilities", "nist-context"},
    {"discovery-assumptions", "sre-reliability", "rice-confidence", "hax-capabilities"},
    {"hax-correction"},
    {"finops-unit-value", "finops-trends", "discovery-assumptions"},
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Call configured LLM; consumes API credit")
    parser.add_argument("--keep", action="store_true", help="Retain the synthetic demo product")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live explicitly to run the real-LLM walkthrough.")

    product_id, run_id = uuid.uuid4(), uuid.uuid4()
    insight_ids: list[uuid.UUID] = []
    failed = False
    with SessionLocal() as db:
        try:
            db.add(Product(id=product_id, name=f"ACT best-practices demo {str(product_id)[:8]}",
                           description="Synthetic evaluation data only — no real user feedback."))
            db.add(AnalysisRun(id=run_id, pipeline_version="act-demo-v2", prompt_version="act-v2",
                               llm_model=get_settings().llm_model_for("act"), embedding_model="not-used",
                               status=RunStatus.completed))
            db.commit()
            print(f"Demo product: {product_id}", flush=True)
            for (title, statement, hypothesis), expected in zip(CASES, EXPECTED_PRACTICES, strict=True):
                insight = Insight(
                    id=uuid.uuid4(), product_id=product_id, run_id=run_id,
                    title=f"SYNTHETIC — {title}",
                    finding=statement or "Chưa có evidence xác minh vấn đề trong tình huống nhân tạo này.",
                    finding_confidence=0.8 if statement else 0.2,
                    hypothesis={"statement": hypothesis, "confidence": 0.35},
                    affected_context={"dataset": "synthetic-demo"}, impact=["Needs validation"],
                    limitations=["Artificial sample, not representative. No causal or ROI claims."],
                    evidence=[], status="approved",
                )
                if statement:
                    evidence = Evidence(id=uuid.uuid4(), run_id=run_id, product_id=product_id,
                                        type="aggregate", statement=statement, payload={"synthetic": True},
                                        source_tool="aggregate_feedback", coverage=1.0)
                    db.add(evidence)
                    insight.evidence = [str(evidence.id)]
                db.add(insight)
                insight_ids.append(insight.id)
                db.commit()
                actions, skipped, error = generate_actions(db, insight)
                if error or not actions:
                    print(f"FAIL {title}: {error or 'no actions'}", flush=True)
                    failed = True
                    continue
                briefs = [ActionDecisionSupport.model_validate(action.decision_support) for action in actions]
                if not statement:
                    assert all(brief.kind == "investigate" and not brief.evidence for brief in briefs)
                else:
                    assert all(brief.kind == "investigate" or brief.evidence for brief in briefs)
                cited = {reference.card_id for brief in briefs for reference in brief.references}
                if not cited.intersection(expected):
                    print(f"FAIL {title}: no applicable practice cited ({','.join(sorted(cited))})", flush=True)
                    failed = True
                    continue
                print(f"PASS {title}: actions={len(actions)}, skipped={len(skipped)}, report={insight.id}", flush=True)
                for action, brief in zip(actions, briefs, strict=True):
                    print(f"  {action.function.value}: {brief.kind}; "
                          f"lenses={','.join(p.lens for p in brief.perspectives)}; "
                          f"cards={','.join(r.card_id for r in brief.references)}", flush=True)
            return 1 if failed else 0
        finally:
            if not args.keep:
                db.rollback()
                if insight_ids:
                    db.execute(delete(Action).where(Action.insight_id.in_(insight_ids)))
                    db.execute(delete(Insight).where(Insight.id.in_(insight_ids)))
                db.execute(delete(Evidence).where(Evidence.run_id == run_id))
                db.execute(delete(AnalysisRun).where(AnalysisRun.id == run_id))
                db.execute(delete(Product).where(Product.id == product_id))
                db.commit()
                print("Removed this walkthrough's synthetic rows.", flush=True)
            else:
                print(f"Kept synthetic product {product_id} for UI review.", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
