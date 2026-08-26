"""Integration tests Phase 18 Task 3+4 — tools `get_cluster_metrics` /
`fetch_evidence_quotes` (test gộp theo plan Step 4.1).

⚠️ Marker `integration` — DB Supabase thật; KHÔNG chạm LLM (cả 2 tool thuần
SQL). Fixture prefix `agtool-` — dọn sạch sau, không đụng row lane khác.

Trọng tâm:
- Trend fields phải ĐỌC VERBATIM từ row clusters (growth_ratio đặt giá trị
  đặc biệt 7.77 — nếu tool tự tính lại sẽ lệch ngay);
- member_count/severity_dist/top_categories là số LIVE từ feedbacks;
- Evidence: ORDER BY confidence DESC NULLS LAST, snippet ≤200 từ
  sanitized_content, row chưa sanitize bị loại;
- **Canary PII**: raw_content chứa "RAW-CANARY-XYZ" — chuỗi này PHẢI vắng mặt
  trong toàn bộ output dump (khuôn cho mọi tool sau).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.cluster import Cluster
from app.models.enums import Severity
from app.models.feedback import Feedback
from happynest_agent.tools import evidence as ev_mod
from happynest_agent.tools import metrics as mt_mod

pytestmark = pytest.mark.integration

REF_PREFIX = "agtool-"
CANARY = "RAW-CANARY-XYZ"

N_MEMBERS = 6  # 6 row gắn cụm (01–06); evidence chỉ lấy 5 (06 chưa sanitize)


def _mk_cluster() -> Cluster:
    now = datetime.now(timezone.utc)
    # trend fields ĐẶT GIÁ TRỊ ĐẶC BIỆT — tool phải passthrough, không recomputed
    return Cluster(
        name="agtool cluster",
        summary="cụm giả lập cho test metrics/evidence",
        feedback_count=N_MEMBERS,
        first_seen=now - timedelta(days=40),
        last_seen=now - timedelta(hours=2),
        current_count=3,
        previous_count=2,
        growth_ratio=7.77,
        is_emerging=False,
        is_spike=True,
        suggested_priority=0.66,
    )


@pytest.fixture()
def seeded_cluster():
    """1 cluster + 6 feedbacks: 5 member + 1 canary member (sanitized sạch).

    confidences: 0.95, 0.90, NULL, 0.80, 0.70 → evidence order xác định;
    1 row ngoài cụm (không cluster_id) — không được lọt output.
    """
    state: dict = {"qrun_id": None}
    with SessionLocal() as db:
        # dọn rác lần trước (logs TRƯỚC — FK restrict)
        old_ids = db.scalars(
            select(Feedback.id).where(Feedback.external_ref.like(f"{REF_PREFIX}%"))
        ).all()
        if old_ids:
            from app.models.llm_call_log import LlmCallLog

            db.query(LlmCallLog).filter(
                LlmCallLog.feedback_id.in_(old_ids)
            ).delete(synchronize_session=False)
        db.query(Feedback).filter(
            Feedback.external_ref.like(f"{REF_PREFIX}%")
        ).delete(synchronize_session=False)
        db.query(Cluster).filter(Cluster.name == "agtool cluster").delete(
            synchronize_session=False
        )
        db.commit()

        # quarantine run: seed rows được CLAIM NGAY lúc tạo — runner thật đang
        # chạy trên DB dùng chung không được nhặt chúng (bài học 2026-08-26)
        from app.models.analysis_run import AnalysisRun
        from app.models.enums import RunStatus

        qrun = AnalysisRun(
            pipeline_version="test-quarantine",
            llm_model="none",
            prompt_version="none",
            embedding_model="none",
            status=RunStatus.failed,
            total_count=0,
        )
        db.add(qrun)
        db.flush()
        state["qrun_id"] = qrun.id

        cluster = _mk_cluster()
        db.add(cluster)
        db.flush()

        base = datetime.now(timezone.utc) - timedelta(days=10)
        specs = [
            # (ref, severity, confidence, categories, sanitized)
            ("01", Severity.high, 0.95, ["hiệu năng", "latency"], "App chậm rõ rệt khi tải báo cáo"),
            ("02", Severity.critical, None, ["hiệu năng"], "Đôi lúc treo hẳn màn hình chính"),
            ("03", Severity.medium, 0.80, ["pricing", "subscription"], "Giá gói premium tăng quá nhanh"),
            ("04", Severity.low, 0.70, ["hiệu năng", "battery"], "Pin tụt nhanh kể cả không dùng"),
            ("05", Severity.medium, 0.60, ["hiệu năng", "latency"], "Latency cao buổi tối"),
            ("06", Severity.low, 0.50, ["ui"], "Nút bấm khó nhìn trên màn hình nhỏ"),
        ]
        ids: list[uuid.UUID] = []
        for i, (ref, sev, conf, cats, san) in enumerate(specs):
            # CANARY chỉ nằm trong RAW (presidio phải gạt nó khỏi sanitized) —
            # đúng kịch bản plan Step 4.2
            raw = f"Latency cao buổi tối {CANARY}" if ref == "05" else f"raw {ref} (không PII)"
            fb = Feedback(
                source="test-agtool",
                external_ref=f"{REF_PREFIX}{ref}",
                raw_content=raw,
                sanitized_content=san if ref != "06" else None,  # 06: chưa sanitize
                created_at=base - timedelta(minutes=i),
                severity=sev,
                confidence=conf,
                categories=cats,
                cluster_id=cluster.id,
                analysis_run_id=state["qrun_id"],
            )
            db.add(fb)
            db.flush()
            ids.append(fb.id)

        outsider = Feedback(
            source="test-agtool",
            external_ref=f"{REF_PREFIX}out",
            raw_content="outsider",
            sanitized_content="ngoài cụm không được lọt",
            created_at=base,
            severity=Severity.critical,
            confidence=0.99,
            categories=["hiệu năng"],
            analysis_run_id=state["qrun_id"],
        )
        db.add(outsider)
        db.commit()
        state.update(cluster_id=cluster.id, ids=ids, outsider_id=outsider.id)
    yield state

    with SessionLocal() as db:
        db.query(Feedback).filter(
            Feedback.external_ref.like(f"{REF_PREFIX}%")
        ).delete(synchronize_session=False)
        db.query(Cluster).filter(Cluster.name == "agtool cluster").delete(
            synchronize_session=False
        )
        if state.get("qrun_id"):
            qrun = db.get(AnalysisRun, state["qrun_id"])
            if qrun is not None:
                db.delete(qrun)
        db.commit()


# ---------------------------------------------------------------------------
# get_cluster_metrics
# ---------------------------------------------------------------------------


def test_metrics_reads_stored_trend_verbatim(seeded_cluster):
    with SessionLocal() as db:
        out = mt_mod.execute(
            db, mt_mod.MetricsIn(run_id=uuid.uuid4(), cluster_id=seeded_cluster["cluster_id"])
        )

        assert out.name == "agtool cluster"
        # trend VERBATIM từ row clusters — growth 7.77 là dấu hiệu nhận diện
        assert out.growth_ratio == 7.77
        assert out.is_spike is True and out.is_emerging is False
        assert out.suggested_priority == pytest.approx(0.66)
        assert out.current_count == 3 and out.previous_count == 2
        # live query: đúng 5 member trong cụm (outsider không tính)
        assert out.member_count == N_MEMBERS
        assert out.severity_dist == {
            "critical": 1, "high": 1, "medium": 2, "low": 2,
        }
        # top_categories ≤5 giảm dần: hiệu năng 4 > latency 2 > còn lại 1
        top = [(c.category, c.count) for c in out.top_categories]
        assert len(top) <= 5
        assert top[0] == ("hiệu năng", 4)


def test_metrics_unknown_cluster_raises(seeded_cluster):
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="cluster not found"):
            mt_mod.execute(
                db, mt_mod.MetricsIn(run_id=uuid.uuid4(), cluster_id=uuid.uuid4())
            )


# ---------------------------------------------------------------------------
# fetch_evidence_quotes
# ---------------------------------------------------------------------------


def test_evidence_order_truncation_and_canary(seeded_cluster):
    with SessionLocal() as db:
        out = ev_mod.execute(
            db,
            ev_mod.EvidenceIn(run_id=uuid.uuid4(), cluster_id=seeded_cluster["cluster_id"]),
        )

        refs = {q.feedback_id: i for i, q in enumerate(out.quotes)}
        id_by_ref = {}
        for fid in seeded_cluster["ids"]:
            fb = db.get(Feedback, fid)
            id_by_ref[fb.external_ref] = fid

        # ORDER confidence DESC NULLS LAST: .95, .80, .70, .60 rồi NULL cuối;
        # row 06 (sanitized NULL) và outsider bị loại khỏi output
        in_output = {
            ext: fid for ext, fid in id_by_ref.items() if fid in refs
        }
        order_refs = [
            ext for ext, _ in sorted(in_output.items(), key=lambda kv: refs[kv[1]])
        ]
        assert order_refs == [
            f"{REF_PREFIX}01", f"{REF_PREFIX}03", f"{REF_PREFIX}04",
            f"{REF_PREFIX}05", f"{REF_PREFIX}02",
        ]
        # snippet cắt TỪ sanitized, ≤200 ký tự; 06 (sanitized NULL) bị loại
        assert all(len(q.snippet) <= 200 for q in out.quotes)
        assert len(out.quotes) == N_MEMBERS - 1
        assert seeded_cluster["outsider_id"] not in refs

        # CANARY PII: raw chứa RAW-CANARY-XYZ (member 05) — dump toàn bộ output
        dump = out.model_dump_json()
        assert CANARY not in dump, "canary lộ ra ngoài biên PII!"
