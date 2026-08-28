"""Test service impact.run_impact_checks — Phase 20 Task 1.

DB-backed trên Supabase dev dùng chung: seed qua SessionLocal với marker
prefix ``impit-`` / ``[impit-``; teardown xoá đúng bộ vừa tạo theo thứ tự FK.
run_impact_checks COMMIT nội bộ nên rollback-thông-thường không đủ — dọn tay
như các suite integration hiện hành.

Thuần SQL — test cũng KHÔNG mock gì: assert zero LLM bằng chính hành vi
(không patch, không chờ, chạy tức thì).

Chạy:  uv run pytest tests/test_impact_service.py -q   (SKIP khi DB offline)
"""

from datetime import datetime, timedelta, timezone
from itertools import count

import pytest
from sqlalchemy import delete, select, text

from app.db.session import SessionLocal
from app.models.action_draft import ActionDraft
from app.models.cluster import Cluster
from app.models.enums import DraftKind, ReviewStatus
from app.models.feedback import Feedback
from app.models.impact_check import ImpactCheck
from app.models.insight import Insight
from app.services.impact import run_impact_checks

_REF_PREFIX = "impit-"
_TITLE_PREFIX = "[impit-"
_plant_seq = count()  # tên cụm plant duy nhất mỗi lần gọi — lookup .one() không trùng


def _count_stray() -> int:
    with SessionLocal() as db:
        fb = int(
            db.execute(
                text("SELECT count(*) FROM feedbacks WHERE external_ref LIKE :p"),
                {"p": _REF_PREFIX + "%"},
            ).scalar_one()
        )
        ins = int(
            db.execute(
                text("SELECT count(*) FROM insights WHERE title LIKE :p"),
                {"p": _TITLE_PREFIX + "%"},
            ).scalar_one()
        )
        return fb + ins


@pytest.fixture()
def imp_env():
    """GUARD skip khi DB còn row lạ cùng marker; teardown dọn FK-order."""
    if _count_stray():
        pytest.skip("DB dùng chung còn row impit-* chưa dọn — bỏ chạy.")
    yield
    with SessionLocal() as db:
        ins_ids = db.scalars(
            select(Insight.id).where(Insight.title.like(_TITLE_PREFIX + "%"))
        ).all()
        if ins_ids:
            db.execute(
                delete(ImpactCheck).where(ImpactCheck.insight_id.in_(ins_ids))
            )
            db.execute(
                delete(ActionDraft).where(ActionDraft.insight_id.in_(ins_ids))
            )
        db.execute(delete(Insight).where(Insight.title.like(_TITLE_PREFIX + "%")))
        db.execute(
            delete(Feedback).where(Feedback.external_ref.like(_REF_PREFIX + "%"))
        )
        db.execute(delete(Cluster).where(Cluster.name.like(_TITLE_PREFIX + "%")))
        db.commit()
        assert _count_stray() == 0


def _plant(db, *, review_status=ReviewStatus.approved, age_days=30,
           ticket=True, slack=False):
    """Cụm + insight + draft đủ điều kiện chuẩn — giờ tuyệt đối từ bây giờ."""
    from app.models.enums import DraftStatus

    now = datetime.now(timezone.utc)
    cname = f"{_TITLE_PREFIX}Wifi rớt liên tục #{next(_plant_seq)}"
    db.add(
        Cluster(
            name=cname,
            summary="than wifi.",
            feedback_count=0,
            first_seen=now - timedelta(days=40),
            last_seen=now,
            current_count=0,
            previous_count=0,
            growth_ratio=None,
            is_emerging=False,
            is_spike=False,
            suggested_priority=0.5,
        )
    ) or None
    # add trả về state — lấy lại qua flush
    db.flush()
    cid_obj = db.scalars(select(Cluster.id).where(Cluster.name == cname)).one()

    ins = Insight(
        cluster_id=cid_obj,
        title=_TITLE_PREFIX + "Fix wifi trước giờ cao điểm",
        summary="wifi rớt nhiều.",
        suggested_action="Nâng băng thông.",
        evidence_ids=[],
        review_status=review_status,
        created_at=now - timedelta(days=age_days),
    )
    db.add(ins)
    db.flush()

    if ticket:
        db.add(
            ActionDraft(
                insight_id=ins.id,
                kind=DraftKind.draft_ticket,
                body="ticket",
                status=DraftStatus.draft,
                created_at=now - timedelta(days=10),
            )
        )
    if slack:
        db.add(
            ActionDraft(
                insight_id=ins.id,
                kind=DraftKind.slack_message,
                body="slack",
                status=DraftStatus.draft,
                created_at=now - timedelta(days=10),
            )
        )

    def _fb(offset_days: int) -> Feedback:
        return Feedback(
            external_ref=f"{_REF_PREFIX}{ins.id.hex[:6]}-{offset_days}",
            source="unit-test",
            created_at=(now - timedelta(days=10)) + timedelta(days=offset_days),
            raw_content="raw unit test (không bao giờ ra khỏi biên sanitize)",
            sanitized_content="wifi rớt.",
            cluster_id=cid_obj,
        )

    return {"cid": cid_obj, "ins": ins, "now": now, "fb": _fb}


def test_measures_delta_around_ticket_milestone(imp_env) -> None:
    with SessionLocal() as db:
        p = _plant(db)
        # 2 member TRƯỚC mốc (trong [t-7d, t)), 1 SAU (trong [t, t+7d)),
        # 1 ngoài cả hai cửa sổ (+20d) — không được tính
        db.add_all([p["fb"](-5), p["fb"](-3), p["fb"](+2), p["fb"](+20)])
        db.commit()

        out = run_impact_checks(db)

    assert out["checks_inserted"] == 1
    item = out["items"][0]
    assert item["before"] == 2
    assert item["after"] == 1
    assert item["delta_ratio"] == -0.5  # (1-2)/max(2,1)

    with SessionLocal() as db2:
        row = db2.scalars(
            select(ImpactCheck).where(
                ImpactCheck.insight_id == p["ins"].id
            )
        ).one()
        assert row.window_days == 7
        assert row.before_count == 2 and row.after_count == 1
        assert row.delta_ratio == pytest.approx(-0.5)
        expected_checked_at = (p["now"] - timedelta(days=10)) + timedelta(days=7)
        assert abs((row.checked_at - expected_checked_at).total_seconds()) < 60
        assert row.cluster_name.startswith(_TITLE_PREFIX)
        assert str(row.cluster_id) == str(p["cid"])


def test_skips_young_non_ticket_and_unapproved(imp_env) -> None:
    """Bộ lọc: thiếu draft_ticket · chưa đủ tuổi window · chưa duyệt → bỏ."""
    with SessionLocal() as db:
        young = _plant(db, age_days=2)          # created_at mới hơn cutoff 7d
        no_ticket = _plant(db, ticket=False, slack=True)  # chỉ slack → bỏ
        rejected = _plant(db, review_status=ReviewStatus.rejected)  # chưa duyệt

        ok = _plant(db)  # control — chứng minh bộ lọc không nuốt sạch
        db.add_all([ok["fb"](0)])
        db.commit()

        out = run_impact_checks(db)

    measured = {i["insight_id"] for i in out["items"]}
    assert str(ok["ins"].id) in measured
    assert len(measured) == 1
    for skipped in (young, no_ticket, rejected):
        assert str(skipped["ins"].id) not in measured


def test_rerun_is_idempotent(imp_env) -> None:
    """Rerun không nhân bản phép đo — already-measured bị loại."""
    with SessionLocal() as db:
        p = _plant(db)
        db.add(p["fb"](-1))
        db.commit()

        first = run_impact_checks(db)
        second = run_impact_checks(db)

    assert first["checks_inserted"] == 1
    assert second["checks_inserted"] == 0
    with SessionLocal() as db2:
        n = len(
            db2.scalars(
                select(ImpactCheck.id).where(ImpactCheck.insight_id == p["ins"].id)
            ).all()
        )
    assert n == 1
