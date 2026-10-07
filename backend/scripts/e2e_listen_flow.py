"""E2E Listen flow (spec Listen 2026-10-07) — generate → apply → enrich →
uncategorized → recommend → apply → re-enrich → insight-ready dataset.

⚠️ Gọi LLM THẬT (OpenRouter) — chạy THỦ CÔNG khi muốn demo, KHÔNG chạy trong
pytest (quy tắc: test tự động mock LLM). Idempotent: product tồn tại + đã có
dataset → chỉ in tổng kết; `--fresh` để xoá data product rồi chạy lại.

Cách chạy (từ backend/):
    uv run python scripts/e2e_listen_flow.py                 # demo product mặc định
    uv run python scripts/e2e_listen_flow.py --fresh         # chạy lại từ đầu
    uv run python scripts/e2e_listen_flow.py --product ten   # product khác

Check trace sau khi chạy:
    SELECT call_type, model, COUNT(*) FROM llm_call_logs GROUP BY 1, 2 ORDER BY 2;
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta

utf8 = sys.stdout.reconfigure(encoding="utf-8")  # Windows console

PRODUCT_NAME = "listen-flow-demo"
SAMPLE_FEEDBACK = [
    # (text VI/EN nhân tạo, KHÔNG PII thật) — một nửa NẰM NGOÀI taxonomy seed
    # để tạo uncategorized cho vòng recommend.
    "Update xong thanh toan cu quay mai roi bao loi",
    "The payment keeps failing with my card since yesterday",
    "dang nhap bang google ko duoc nua, bao loi 500",
    "OTP khong gui ve dien thoai, thu 5 lan roi",
    "Search ra ket qua khong lien quan, filter lag lau",
    "App mo rat lau, quay qua 1 phut moi vao duoc",
    "Bot bia mot nguon tin khong ton tai, so lieu sai het",
    "Bao cao xuat ra thieu cot, doc khong hieu gi",
    "Font chu hien thi loi o man hinh nho, chu bi hoa",
    "To mau phan bieu do sai, mau voi chu cung mau",
    "Support tra loi rat cham, 3 ngay chua thay phan hoi",
    "Cam on doi ngu, tinh nang moi rat huu ich lam",
]


def _ensure_product(product_name: str):
    from app.models.product import Product

    with SessionLocal() as db:
        product = db.query(Product).filter(Product.name == product_name).first()
        if product is None:
            product = Product(
                name=product_name,
                description="Demo product cho E2E Listen flow (spec 2026-10-07).",
            )
            db.add(product)
            db.commit()
            db.refresh(product)
        return product.id


def _wipe(product_id) -> None:
    from app.models.analysis_run import AnalysisRun
    from app.models.feedback import Feedback
    from app.models.taxonomy import Taxonomy

    with SessionLocal() as db:
        db.query(Feedback).filter(Feedback.product_id == product_id).delete(
            synchronize_session=False
        )
        db.query(Taxonomy).filter(Taxonomy.product_id == product_id).delete(
            synchronize_session=False
        )
        runs = db.query(AnalysisRun).filter(AnalysisRun.import_id.is_(None)).all()
        for run in runs:
            db.delete(run)
        db.commit()


def _seed(product_id, n: int) -> None:
    from app.models.feedback import Feedback

    now = datetime.now(UTC)
    with SessionLocal() as db:
        for i, text in enumerate(SAMPLE_FEEDBACK[:n]):
            db.add(
                Feedback(
                    product_id=product_id,
                    source="e2e-listen-flow",
                    source_record_id=f"seed-{i:02d}",
                    occurred_at=now - timedelta(hours=n - i),
                    raw_content=text,
                    feedback_text=text,  # nhân tạo KHÔNG PII — coi như đã sanitize
                )
            )
        db.commit()


def _run_enrichment(product_id, import_id=None) -> None:
    from app.core.config import get_settings
    from app.jobs.analysis_runner import PIPELINE_VERSION, run_analysis
    from app.models.analysis_run import AnalysisRun
    from app.models.enums import RunStatus
    from app.schemas.analysis import AnalysisScopeIn
    from app.services.analysis_service import select_eligible_feedback
    from app.services.enricher import PROMPT_VERSION

    with SessionLocal() as db:
        scope = AnalysisScopeIn(mode="batch", import_id=import_id)
        rows, _ = select_eligible_feedback(db, scope)
        if not rows:
            print("    (không còn row nào để enrich)")
            return
        run = AnalysisRun(
            pipeline_version=PIPELINE_VERSION,
            llm_model=get_settings().llm_model_for("enrich"),
            prompt_version=PROMPT_VERSION,
            embedding_model=get_settings().EMBEDDING_MODEL,
            import_id=import_id,
            mode="batch",
            chunk_size=get_settings().ANALYSIS_BATCH_SIZE,
            total_count=len(rows),
        )
        db.add(run)
        db.flush()
        for row in rows:
            row.analysis_run_id = run.id
        db.commit()
        run_id = run.id
    print(f"    run {run_id} — enrich {len(rows)} row (LLM thật, chờ...)")
    run_analysis(run_id)
    with SessionLocal() as db:
        run = db.get(AnalysisRun, run_id)
        print(
            f"    status={run.status.value} processed={run.processed_count}/{run.total_count}"
            + (f" failed={run.failed_count}" if run.failed_count else "")
        )
        if run.status != RunStatus.completed:
            print(f"    ERROR: {run.error}")
            raise SystemExit(1)


def _summary(product_id) -> None:
    from sqlalchemy import func, select

    from app.models.feedback import Feedback

    with SessionLocal() as db:
        total = db.scalar(
            select(func.count()).select_from(Feedback).where(Feedback.product_id == product_id)
        )
        rows = db.scalars(
            select(Feedback.ai_analysis).where(Feedback.product_id == product_id)
        ).all()
    counts: dict[str, int] = {}
    uncategorized = 0
    emotions: dict[str, int] = {}
    for analysis in rows:
        if not analysis:
            continue
        if analysis.get("uncategorized"):
            uncategorized += 1
        for topic in analysis.get("topics") or []:
            counts[topic] = counts.get(topic, 0) + 1
        for emo in analysis.get("emotions") or []:
            emotions[emo] = emotions.get(emo, 0) + 1
    print("\n=== INSIGHT-READY DATASET (spec §7) ===")
    print(f"rows enriched: {sum(1 for r in rows if r)} / {total}")
    print(f"uncategorized: {uncategorized}")
    print("top topics:", dict(sorted(counts.items(), key=lambda kv: -kv[1])))
    print("emotions:", dict(sorted(emotions.items(), key=lambda kv: -kv[1])))


def main() -> int:
    args = sys.argv[1:]
    fresh = "--fresh" in args
    product_name = PRODUCT_NAME
    if "--product" in args:
        product_name = args[args.index("--product") + 1]

    from app.core.config import get_settings
    from app.models.feedback import Feedback
    from app.models.product import Product
    from app.schemas.taxonomy import ProposedTopic, TaxonomyProposalOut
    from app.services import analysis_service, taxonomy_service

    settings = get_settings()
    if not settings.LLM_API_KEY:
        print("LLM_* chưa cấu hình trong backend/.env — không chạy được flow thật.")
        return 2

    product_id = _ensure_product(product_name)
    with SessionLocal() as db:
        existing = (
            db.query(Feedback)
            .filter(Feedback.product_id == product_id, Feedback.ai_analysis.is_not(None))
            .count()
        )
    if existing and not fresh:
        print(f"Product '{product_name}' đã có {existing} row enriched — in tổng kết.")
        print("(chạy lại với --fresh để làm lại từ đầu)")
        _summary(product_id)
        return 0
    if fresh:
        print(f"[0] --fresh: wipe feedback + taxonomy của '{product_name}'")
        _wipe(product_id)

    print(f"[1] Seed {len(SAMPLE_FEEDBACK)} feedback VI/EN nhân tạo (không PII thật)")
    _seed(product_id, len(SAMPLE_FEEDBACK))

    print("[2] GPT generate proposal từ sample + context (LLM thật)")
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        proposal, sample_count = taxonomy_service.generate_proposal(
            db, product, sample_size=12,
            context={"product_type": "AI chatbot cho doanh nghiệp", "use_case": "hỗ trợ khách hàng"},
        )
        print(f"    samples dùng: {sample_count}; đề xuất {len(proposal.topics)} topic:")
        for t in proposal.topics:
            print(f"      - {t.name}" + (f" (con của {t.parent})" if t.parent else ""))
        print("[3] HUMAN GATE — demo script auto-apply (thực tế qua POST /api/taxonomies/apply)")
        result = taxonomy_service.apply_proposal(db, product, proposal)
        print(
            f"    applied: created={len(result['created'])} skipped={result['skipped']}"
            f" → taxonomy_version={result['taxonomy_version']}"
        )

    print("[4] Enrich batch (engine=llm, model=" + settings.llm_model_for("enrich") + ")")
    _run_enrichment(product_id)
    _summary(product_id)

    print("[5] GPT recommend topics từ pool uncategorized (LLM thật)")
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        rec, pool_count = taxonomy_service.recommend_topics(db, product)
        print(f"    pool={pool_count}; đề xuất {len(rec.recommendations)}:")
        for r in rec.recommendations:
            print(f"      - {r.name} (evidence={r.evidence_count})")
        if rec.recommendations:
            print("[6] HUMAN GATE — demo auto-apply recommendation → Taxonomy v2")
            applied = taxonomy_service.apply_proposal(
                db, product,
                TaxonomyProposalOut(
                    topics=[ProposedTopic(name=r.name, parent=r.parent) for r in rec.recommendations]
                ),
            )
            print(
                f"    applied: created={len(applied['created'])} skipped={applied['skipped']}"
                f" → taxonomy_version={applied['taxonomy_version']}"
            )

    released = analysis_service.reset_uncategorized(SessionLocal(), product_id)
    print(f"[7] Re-enrich loop: released {released} row uncategorized")
    if released:
        _run_enrichment(product_id)
    _summary(product_id)

    print("\n=== WHERE TO CHECK ===")
    print("SQL: SELECT call_type, model, COUNT(*) FROM llm_call_logs GROUP BY 1,2;")
    print("Langfuse: filter generation name enrich:EnrichmentOut / taxonomy_generate:TaxonomyProposalOut")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
