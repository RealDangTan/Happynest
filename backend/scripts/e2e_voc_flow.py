"""E2E acceptance flow VoC OS — plan 27 Task 5.

Demo CSV đi qua TOÀN BỘ LISTEN → UNDERSTAND → ACT (cần LLM THẬT + key còn
tín dụng — KHÔNG mock). Chạy: uv run python scripts/e2e_voc_flow.py

Các bước: tạo product demo → upload CSV → (in mapping proposal) → Gate #1
approve-all → analysis run (chờ xong) → clusters → understand run (question)
→ (in insight + evidence) → Gate #2 approve → actions generate → Gate #3
override action đầu tiên → GET /api/reports/kpis.
"""

import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.enums import RunStatus  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.services import act_agent, import_service  # noqa: E402


def main() -> int:
    demo_csv = Path("demo_dataset.csv")
    if not demo_csv.is_file():
        print(f"Không thấy {demo_csv} — đặt file demo vào backend/ trước.")
        return 2

    with SessionLocal() as db:
        # 1. Product demo (product đầu tiên)
        product = db.query(Product).order_by(Product.created_at).first()
        if product is None:
            print("Chưa có product — tạo POST /api/products trước.")
            return 2
        print(f"[1] Product: {product.name} ({product.id})")

        # 2-4. LISTEN: upload → profile → LLM map → Gate #1
        raw = demo_csv.read_bytes()
        print("[2] Upload CSV → profiler → LLM mapper...")
        import_row = import_service.start_import(db, product.id, raw)
        proposal = import_service.get_proposal(import_row)
        for m in proposal.mappings:
            print(f"    {m.source_field}: {m.decision}"
                  + (f" → {m.target or m.candidate.key}" if m.decision in ("MAP", "PROMOTE") else ""))
        decisions = [
            {"source_field": m.source_field, "action": "approve"}
            for m in proposal.mappings
        ]
        from app.schemas.import_ import MappingDecisionItem

        report = import_service.apply_mapping_decision(
            db,
            import_row,
            [MappingDecisionItem.model_validate(d) for d in decisions],
        )
        print(f"[3] Gate #1 approved → imported={report['imported']} "
              f"failed={report['failed']} schema v{report['schema_version']}")

        # 5. Analysis run (classify + embed — LLM thật)
        from app.jobs.analysis_runner import run_analysis
        from app.models.analysis_run import AnalysisRun
        from app.core.config import get_settings

        run = AnalysisRun(
            pipeline_version="v2",
            llm_model=get_settings().LLM_MODEL,
            prompt_version="v2",
            embedding_model=get_settings().EMBEDDING_MODEL,
            total_count=report["imported"],
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        print(f"[4] Analysis run {run.id} — classify + embed {report['imported']} row...")
        run_analysis(run.id)
        db.refresh(run)
        print(f"    status={run.status.value} processed={run.processed_count}")

        # 6. Clusters
        from app.services.clustering import run_clustering

        stats = run_clustering(db)
        print(f"[5] Clusters: {stats.clusters_upserted} cụm, "
              f"{stats.assigned_count} members")

        # 7-9. UNDERSTAND (chạy inline, không background — dễ theo dõi)
        from understand_agent import runner as u_runner

        question = "Điều gì đang là vấn đề lớn nhất của sản phẩm tuần này?"
        print(f"[6] UNDERSTAND run: {question!r}")
        values = u_runner.submit_or_start(run.id, product.id, {"question": question})
        draft = values.get("draft_insight") or {}
        print(f"    interrupt Gate #2 — insight: {draft.get('title')}")
        insight_id = uuid.UUID(values.get("insights_created", ["0"])[-1]) if values.get("insights_created") else None
        if insight_id is None:
            # id từ interrupt payload
            print("    (kiểm tra GET /api/agent/runs để lấy insight_id)")
            return 1

        # 10. Gate #2 approve (seed user pm)
        from app.models.user import User

        pm = db.query(User).filter_by(role="pm").first()
        values = u_runner.resume_with_decision(
            run.id, {"action": "approve", "reviewer_id": str(pm.id)}
        )
        print(f"[7] Gate #2 approved → final_status={values.get('final_status')}")

        # 11-13. ACT
        from app.models.insight import Insight

        insight = db.get(Insight, insight_id)
        created, skipped = act_agent.generate_actions(db, insight)
        print(f"[8] ACT: {len(created)} actions, skipped: {', '.join(skipped) or '—'}")
        if created:
            a = created[0]
            print(f"    sample: [{a.function.value}] {a.recommendation[:80]}... "
                  f"priority={a.priority_score}")
            a.human_impact = max(1, a.impact - 2)
            a.human_effort = a.effort
            a.override_reason = "E2E demo override"
            act_agent.recompute_priority(a)
            db.commit()
            print(f"    Gate #3 override → priority={a.priority_score}")

        # 14. KPIs
        from app.services.reports import build_kpis

        kpis = build_kpis(db, datetime.now(timezone.utc))
        print("[9] KPIs:")
        for key in (
            "time_to_listen_median_s", "time_to_insight_median_s",
            "time_to_action_median_s", "insights_total", "insight_evidence_grounding_pct",
            "actions_total", "pct_action_accepted", "matrix_displacement_avg",
        ):
            print(f"    {key} = {kpis[key]}")
    print("E2E flow HOÀN TẤT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
