"""Integration tests Phase 18 Task 5 — tool `retrieve_similar_insights`.

⚠️ Marker `integration` — DB Supabase thật cho insights/insight_reviews;
embed_one MOCK (vector giả viết tay) — KHÔNG đốt embed API.

Kịch bản plan Step 5.3:
- Seed 2 insight với vector cố định trực giao (A=[1,0,...], B=[0,1,...]);
  insight A có 1 dòng insight_reviews (phán quyết người), B không có;
- Query mock trả vector gần A → A rank 1 đúng thứ tự cosine;
- human_decision: A kèm action+reason từ review MỚI NHẤT, B = None.
"""

import uuid

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import ReviewAction, ReviewStatus
from app.models.insight import Insight
from app.models.insight_review import InsightReview
from app.models.user import User
from happynest_agent.tools import precedents as pr_mod

pytestmark = pytest.mark.integration

REF_TITLE_PREFIX = "[agtool-test]"


def _vec(first: float, second: float) -> list[float]:
    v = [0.0] * 1536
    v[0], v[1] = first, second
    return v


@pytest.fixture()
def seeded_insights(monkeypatch):
    state: dict = {}
    with SessionLocal() as db:
        old = db.scalars(
            select(Insight).where(Insight.title.like(f"{REF_TITLE_PREFIX}%"))
        ).all()
        for ins in old:
            db.delete(ins)
        db.commit()

        reviewer = db.scalars(select(User).limit(1)).first()
        if reviewer is None:
            pytest.skip("DB chưa có user seed — cần cho FK reviewer_id")

        ins_a = Insight(
            title=f"{REF_TITLE_PREFIX} A",
            summary="Cụm Google-login spike tuần này",
            suggested_action="Kiểm tra OAuth flow",
            evidence_ids=[],
            review_status=ReviewStatus.unreviewed,
        )
        ins_b = Insight(
            title=f"{REF_TITLE_PREFIX} B",
            summary="Email notification trễ hàng loạt",
            suggested_action="Rà soát mail queue",
            evidence_ids=[],
            review_status=ReviewStatus.unreviewed,
        )
        db.add_all([ins_a, ins_b])
        db.flush()
        # vector TRỰC GIAO viết tay — cosine(A, gần-A) > cosine(B, gần-A)
        ins_a.embedding = _vec(1.0, 0.0)
        ins_a.embedding_model = "test-fake"
        ins_a.embedding_dim = 1536
        ins_b.embedding = _vec(0.0, 1.0)
        ins_b.embedding_model = "test-fake"
        ins_b.embedding_dim = 1536

        review = InsightReview(
            insight_id=ins_a.id,
            original_value={"title": ins_a.title, "summary": ins_a.summary},
            reviewer_id=reviewer.id,
            action=ReviewAction.approve,
            reason="đồng ý, đã tạo ticket",
        )
        db.add(review)
        db.commit()
        state.update(a_id=ins_a.id, b_id=ins_b.id, review_id=review.id)
    yield state

    with SessionLocal() as db:
        db.query(InsightReview).filter(
            InsightReview.insight_id.in_(
                [i for i in [state.get("a_id"), state.get("b_id")] if i]
            )
        ).delete(synchronize_session=False)
        db.query(Insight).filter(
            Insight.title.like(f"{REF_TITLE_PREFIX}%")
        ).delete(synchronize_session=False)
        db.commit()


def test_precedent_ranking_and_human_decision(seeded_insights, monkeypatch):
    # query vector lệch nhẹ về phía A: [0.9, 0.1, 0, ...]
    monkeypatch.setattr(pr_mod, "embed_one", lambda text: _vec(0.9, 0.1))

    with SessionLocal() as db:
        out = pr_mod.execute(
            db,
            pr_mod.PrecedentsIn(run_id=uuid.uuid4(), query_text="mô tả cụm bất kỳ", top_k=2),
        )

        assert len(out.matches) == 2
        first, second = out.matches
        assert first.insight_id == seeded_insights["a_id"], "gần-A phải rank 1"
        assert first.similarity > second.similarity
        # A có phán quyết người; B không có
        assert first.human_decision is not None
        assert first.human_decision.action == "approve"
        assert "đồng ý" in first.human_decision.reason
        assert second.human_decision is None


def test_precedent_summary_truncated_to_300(seeded_insights, monkeypatch):
    monkeypatch.setattr(pr_mod, "embed_one", lambda text: _vec(0.9, 0.1))
    with SessionLocal() as db:
        ins = db.get(Insight, seeded_insights["b_id"])
        original = ins.summary
        ins.summary = "x" * 500
        db.commit()

        out = pr_mod.execute(
            db,
            pr_mod.PrecedentsIn(run_id=uuid.uuid4(), query_text="q", top_k=2),
        )
        for m in out.matches:
            assert len(m.summary) <= 300

        ins.summary = original  # khôi phục
        db.commit()
