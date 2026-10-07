"""E2E full flow cho product test "happytest" — LISTEN → UNDERSTAND → ACT.

Chạy: uv run python scripts/e2e_happytest.py   (từ backend/, cần LLM thật)

Tạo product "happytest" (nếu chưa có) + CSV 50 feedback synthetic → Gate #1
approve-all → analysis (classify+embed) → clusters → UNDERSTAND (Gate #2
approve) → ACT generate + Gate #3 override → in checklist chỗ check UI/trace.
"""

import csv
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.analysis_run import AnalysisRun  # noqa: E402
from app.models.enums import RunStatus  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.services import act_agent, import_service  # noqa: E402

PRODUCT_NAME = "happytest"
CSV_PATH = Path("storage/e2e/happytest.csv")

FEEDBACK_TEMPLATES = [
    # (vi/en mixed, weight tăng dần theo tuần cuối = spike bug)
    ("App bị crash ngay khi tôi mở tính năng phân tích, đang dùng thì thoát hẳn", "bug"),
    ("The AI summary feature stopped working since yesterday, always times out", "bug"),
    ("Khi upload file lớn thì loading quay mãi không xong, phải reload lại trang", "bug"),
    ("Chatbot trả lời sai hoàn toàn câu hỏi về dữ liệu tháng trước", "accuracy"),
    ("The assistant keeps misunderstanding Vietnamese questions with mixed English", "accuracy"),
    ("Kết quả phân tích không khớp với số liệu thực tế trong dashboard", "accuracy"),
    ("Report generate bị thiếu mất vài feedback mới nhất", "accuracy"),
    ("AI hay bịa số liệu, không có nguồn dẫn chứng rõ ràng", "accuracy"),
    ("Giao diện mới xinh hơn nhưng khó tìm nút export", "ux"),
    ("The dark mode contrast is too low, hard to read the charts", "ux"),
    ("Nút xác nhận mapping nằm quá gần nút hủy, tôi bấm nhầm 2 lần", "ux"),
    ("Trên mobile không kéo được biểu đồ sang ngang", "ux"),
    ("Tôi không hiểu ô 'schema mapping' nghĩa là gì, cần tooltip giải thích", "ux"),
    ("The onboarding flow is confusing, I gave up at step 3", "ux"),
    ("Phản hồi từ support team rất nhanh, giải quyết trong 2 giờ", "support"),
    ("Đội hỗ trợ trả lời bằng template, không đọc kỹ vấn đề của tôi", "support"),
    ("Hỗ trợ tiếng Việt tốt, kỹ thuật nắm vững", "support"),
    ("Ticket của tôi bị đóng mà chưa được giải quyết", "support"),
    ("Giá gói pro tăng 40% mà không có tính năng mới đáng kể", "pricing"),
    ("The free tier limit of 100 feedbacks per month is too restrictive", "pricing"),
    ("Tôi muốn thanh toán theo năm để được giảm giá", "pricing"),
    ("Bảng giá khó hiểu, không rõ sự khác biệt giữa các gói", "pricing"),
    ("Tính năng phân tích cảm xúc hoạt động rất chính xác", "praise"),
    ("The multi-language support is impressive, works well with Vietnamese", "praise"),
    ("Dashboard tổng quan trực quan, sếp tôi rất thích", "praise"),
    ("Auto-clustering giúp tôi tiết kiệm nhiều thời gian đọc feedback", "praise"),
    ("Xuất báo cáo PDF nhanh và đẹp", "praise"),
    ("App hơi chậm khi quá 500 feedback, phân cụm mất vài phút", "performance"),
    ("The embedding search takes 5+ seconds per query", "performance"),
    ("Trang insights load rất lâu vào giờ cao điểm", "performance"),
    ("Đồng bộ dữ liệu giữa các thiết bị bị trễ 10 phút", "performance"),
    ("Tôi bị lộ email trong phần preview feedback, lo ngại quyền riêng tư", "privacy"),
    ("The tool logged my customer names in the activity trace", "privacy"),
    ("Không có tùy chọn xóa dữ liệu vĩnh viễn", "privacy"),
    ("Cần thêm tính năng gán feedback cho thành viên team", "feature"),
    ("Would love a Slack integration for real-time alerts", "feature"),
    ("Thêm API để tích hợp với hệ thống CRM của chúng tôi", "feature"),
    ("Nên có bản đồ nhiệt (heatmap) cho tần suất vấn đề", "feature"),
    ("Tôi muốn lọc feedback theo khoảng thời gian tùy chọn", "feature"),
    ("App không đăng nhập được bằng Google SSO", "bug"),
    ("When I export to CSV the Vietnamese diacritics are broken", "bug"),
    ("Thông báo email gửi trùng 3 lần cùng một sự kiện", "bug"),
    ("AI classifier gán sai sentiment cho câu hỏi phủ định", "accuracy"),
    ("Đồ thị xu hướng không hiển thị khi chọn mốc thời gian >90 ngày", "bug"),
    ("Chế độ tối bị lỗi màu ở phần matrix ưu tiên", "ux"),
    ("Support trả lời giờ hành chính thôi, cuối tuần không có ai", "support"),
    ("Gói free giới hạn 1 product là hơi ít", "pricing"),
    ("Tính năng phát hiện vấn đề mới (emerging) rất hữu ích", "praise"),
    ("Latency của chatbot tăng vọt giữa trưa, phải chờ 30 giây", "performance"),
    ("Cần cảnh báo khi phát hiện spike feedback tiêu cực", "feature"),
]


def generate_csv() -> Path:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CSV_PATH.is_file() and CSV_PATH.stat().st_size > 0:
        print(f"[csv] dùng lại {CSV_PATH}")
        return CSV_PATH
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    rows = []
    for i, (text, _cat) in enumerate(FEEDBACK_TEMPLATES):
        # spike: 60% row rơi vào 7 ngày cuối (để trend/spike có tín hiệu)
        days_ago = rng.uniform(0, 7) if rng.random() < 0.6 else rng.uniform(7, 30)
        created = now - timedelta(days=days_ago)
        source = rng.choice(["Support", "App Review", "Survey", "Social", "Email"])
        rating = rng.choice([1, 2, 2, 3, 3, 3, 4, 4, 5])
        rows.append({
            "feedback_text": text,
            "source": source,
            "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
            "rating": rating,
            "customer_ref": f"user-{i:03d}",
        })
    # lặp để đủ 50 row (template 50 dòng là đủ; nếu thiếu shuffle thêm bản dịch biến thể)
    base = list(rows)
    while len(rows) < 50:
        t = rng.choice(base)
        rows.append({**t, "created_at": (now - timedelta(days=rng.uniform(0, 30))).strftime("%Y-%m-%d %H:%M:%S")})
    rows = rows[:50]
    rng.shuffle(rows)
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[csv] đã tạo {CSV_PATH} với {len(rows)} row")
    return CSV_PATH


def get_or_create_product() -> Product:
    with SessionLocal() as db:
        product = db.query(Product).filter_by(name=PRODUCT_NAME).first()
        if product is not None:
            print(f"[1] Product đã tồn tại: {product.name} ({product.id})")
            return product
        product = Product(name=PRODUCT_NAME)
        db.add(product)
        db.commit()
        db.refresh(product)
        print(f"[1] Đã tạo product: {product.name} ({product.id})")
        return product


def main() -> int:
    get_settings()
    product = get_or_create_product()
    csv_path = generate_csv()

    with SessionLocal() as db:
        from app.models.feedback import Feedback
        from app.models.import_ import Import

        # Tái dùng import gần nhất của product nếu còn row chưa claim (idempotent re-run)
        reusable = None
        for imp in (
            db.query(Import)
            .filter(Import.product_id == product.id)
            .order_by(Import.created_at.desc())
            .limit(3)
            .all()
        ):
            pending = int(
                db.query(Feedback)
                .filter(
                    Feedback.import_id == imp.id,
                    Feedback.ai_analysis.is_(None),
                    Feedback.analysis_run_id.is_(None),
                )
                .count()
            )
            if pending > 0:
                reusable = (imp, pending)
                break

        if reusable is not None:
            import_row, pending = reusable
            print(f"[2] Tái dùng import {import_row.id} — {pending} row chưa claim (bỏ qua upload)")
            report = {"imported": pending, "failed": 0, "schema_version": None}
        else:
            raw = csv_path.read_bytes()
            print("[2] Upload CSV → profiler → LLM mapper...")
            import_row = import_service.start_import(db, product.id, raw)
            proposal = import_service.get_proposal(import_row)
            for m in proposal.mappings:
                print(f"    {m.source_field}: {m.decision}"
                      + (f" → {m.target or m.candidate.key}" if m.decision in ("MAP", "PROMOTE") else ""))
            from app.schemas.import_ import MappingDecisionItem

            decisions = [
                {"source_field": m.source_field, "action": "approve"} for m in proposal.mappings
            ]
            report = import_service.apply_mapping_decision(
                db, import_row,
                [MappingDecisionItem.model_validate(d) for d in decisions],
            )
            print(f"[3] Gate #1 approved → imported={report['imported']} "
                  f"failed={report['failed']} schema v{report['schema_version']}")

        from app.jobs.analysis_runner import PIPELINE_VERSION, run_analysis
        from app.schemas.analysis import AnalysisScopeIn
        from app.services.analysis_service import select_eligible_feedback
        from app.services.enricher import PROMPT_VERSION

        scope = AnalysisScopeIn(mode="batch", import_id=import_row.id)
        rows, _eligible = select_eligible_feedback(db, scope)
        run = AnalysisRun(
            pipeline_version=PIPELINE_VERSION,
            llm_model=get_settings().llm_model_for("enrich"),
            prompt_version=PROMPT_VERSION,
            embedding_model=get_settings().EMBEDDING_MODEL,
            import_id=import_row.id,
            mode="batch",
            chunk_size=get_settings().ANALYSIS_BATCH_SIZE,
            total_count=len(rows),
        )
        db.add(run)
        db.flush()
        for row in rows:
            row.analysis_run_id = run.id
        db.commit()
        db.refresh(run)
        print(f"[4] Analysis run {run.id} — claim {len(rows)} row, classify + embed (LLM thật, chờ...)")
        run_analysis(run.id)
        db.refresh(run)
        print(f"    status={run.status.value} processed={run.processed_count}/{run.total_count}")
        if run.status != RunStatus.completed:
            print(f"    ERROR: analysis không hoàn tất — {run.error}")
            return 1

        from app.services.clustering import run_clustering

        stats = run_clustering(db)
        print(f"[5] Clusters: {stats.clusters_upserted} cụm, {stats.assigned_count} members")

        from understand_agent import runner as u_runner

        question = "Điều gì đang là vấn đề lớn nhất của sản phẩm tuần này?"
        u_run = AnalysisRun(
            pipeline_version="understand-v1",
            llm_model=get_settings().LLM_MODEL,
            prompt_version="understand-v1",
            embedding_model=get_settings().EMBEDDING_MODEL,
            total_count=1,
        )
        db.add(u_run)
        db.commit()
        db.refresh(u_run)
        print(f"[6] UNDERSTAND run {u_run.id}: {question!r} (graph tới Gate #2, chờ...)")
        values = u_runner.submit_or_start(u_run.id, product.id, {"question": question})
        draft = values.get("draft_insight") or {}
        print(f"    Gate #2 interrupt — insight: {draft.get('title')}")
        print(f"    finding: {(draft.get('finding') or '')[:200]}")
        print(f"    evidence_ids: {draft.get('evidence_ids')}")
        created_ids = values.get("insights_created") or []
        if not created_ids:
            print("    ERROR: không có insights_created")
            return 1
        insight_id = uuid.UUID(created_ids[-1])

        from app.models.user import User

        pm = db.query(User).filter_by(role="pm").first()
        values = u_runner.resume_with_decision(u_run.id, {"action": "approve", "reviewer_id": str(pm.id)})
        print(f"[7] Gate #2 approved → final_status={values.get('final_status')}")

        from app.models.insight import Insight

        insight = db.get(Insight, insight_id)
        created, skipped, _gen_err = act_agent.generate_actions(db, insight)
        print(f"[8] ACT: {len(created)} actions, skipped: {', '.join(skipped) or '—'}")
        for a in created[:6]:
            print(f"    [{a.function.value}] impact={a.impact} effort={a.effort} "
                  f"priority={a.priority_score} :: {a.recommendation[:60]}")
        if created:
            a = created[0]
            a.human_impact = max(1, a.impact - 2)
            a.human_effort = a.effort
            a.override_reason = "E2E happytest override"
            act_agent.recompute_priority(a)
            db.commit()
            print(f"    Gate #3 override action {a.id} → priority mới={a.priority_score}")

    print("\n=== E2E HOÀN TẤT — CHỖ CHECK ===")
    print(f"product_id : {product.id} (happytest)")
    print(f"import_id  : {import_row.id}")
    print(f"analysis   : {run.id} (LISTEN classify+embed)")
    print(f"understand : {u_run.id} (chat history + /reports?run={u_run.id})")
    print(f"insight_id : {insight_id}")
    print("UI         : /dashboard → product switcher chọn happytest → /feedbacks,")
    print("             /insights (insight approved), /reports?run=..., /matrix (actions)")
    print("Langfuse   : cloud.langfuse.com → Traces → lọc giờ vừa chạy")
    print("SQL        : SELECT call_type, latency_ms, error, created_at FROM llm_call_logs")
    print(f"             WHERE analysis_run_id IN ('{run.id}', '{u_run.id}') ORDER BY created_at;")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
