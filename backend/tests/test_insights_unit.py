"""Unit tests insight engine — Phase 15 Tasks 1–2 (plan 15).

Chiến lược DB theo conftest Phase 11: mọi INSERT đi qua fixture `db_session`
(ROLLBACK khi test xong) — không row `ins-it-` nào bám lại DB dev dùng chung.
LLM mock HOÀN TOÀN qua monkeypatch `chat_structured` — suite xanh offline,
không đốt tín dụng.

⚠️ `run_insights` COMMIT bên trong (replace-all DELETE toàn bộ `insights`).
Trên DB dev DÙNG CHUNG điều đó phá data thật → mọi test gọi `run_insights`
phải no-op `db_session.commit` (helper `_no_commit`) để fixture rollback dọn
sạch transaction; production code giữ nguyên hành vi commit.
"""

from datetime import datetime, timedelta, timezone
from json import loads
from uuid import uuid4

import pytest

from tests.conftest import _SKIP_MSG, db_reachable


# ------------------------------------------------------------------ Task 1 cap


class TestInsightMaxClustersSetting:
    """Step 1.2 — default + env override, đọc độc lập .env người dùng."""

    def _settings(self) -> type:
        from app.core.config import Settings

        return Settings(_env_file=None, DATABASE_URL="postgresql+psycopg://t:t@h/db")

    def test_default_is_10(self, monkeypatch) -> None:
        monkeypatch.delenv("INSIGHT_MAX_CLUSTERS", raising=False)
        assert self._settings().INSIGHT_MAX_CLUSTERS == 10

    def test_env_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("INSIGHT_MAX_CLUSTERS", "3")
        assert self._settings().INSIGHT_MAX_CLUSTERS == 3


# ------------------------------------------------------------------ Task 2 engine


NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def _mk_cluster(name: str, n_members: int, priority: float | None):
    from app.models.cluster import Cluster

    return Cluster(
        id=uuid4(),
        name=f"ins-it-{name}",
        summary="cụm test",
        feedback_count=n_members,
        first_seen=NOW - timedelta(days=2),
        last_seen=NOW - timedelta(days=1),
        current_count=n_members,
        previous_count=0,
        growth_ratio=9.99 if n_members else 0.0,
        is_emerging=False,
        is_spike=False,
        suggested_priority=priority,
    )


def _mk_member(i: int, cluster_id) -> object:
    """Member severity cycle critical→high→medium→low, confidence giảm theo i."""
    from app.models.feedback import Feedback

    sev = ("critical", "high", "medium", "low")[i % 4]
    return Feedback(
        external_ref=f"ins-it-{cluster_id.hex[:8]}-{i}",
        source="unit-test",
        created_at=NOW - timedelta(hours=i),
        raw_content=f"RAWMARKER-{cluster_id.hex[:6]}-{i} never leaves boundary",
        sanitized_content=f"sanitized nội dung {i} của cụm {cluster_id.hex[:6]}",
        severity=sev,
        sentiment="negative",
        confidence=round(1.0 - i * 0.1, 2),
        cluster_id=cluster_id,
    )


@pytest.fixture()
def _needs_real_db():
    if not db_reachable():
        pytest.skip(_SKIP_MSG)


@pytest.fixture()
def _no_commit(db_session, monkeypatch):
    """No-op commit TRÊN SESSION TEST để run_insights không phá DB dev chung."""
    monkeypatch.setattr(db_session, "commit", lambda: None)


class TestBuildClusterPayload:
    """Payload prompt: PII boundary + caps (Step 2.3)."""

    def _cluster(self):
        return _mk_cluster("payload", 12, 0.5)

    def test_no_raw_content_leaks(self) -> None:
        from app.services.insight import build_cluster_payload

        cluster = self._cluster()
        members = [_mk_member(i, cluster.id) for i in range(12)]
        payload = loads(build_cluster_payload(cluster, members))
        text = repr(payload)
        assert "RAWMARKER" not in text                      # raw không bao giờ ra khỏi biên
        assert any("sanitized" in s["text"] for s in payload["snippets"])

    def test_snippet_caps_8_items_200_chars_newest_first(self) -> None:
        from app.services.insight import build_cluster_payload

        cluster = self._cluster()
        members = [_mk_member(i, cluster.id) for i in range(12)]  # 12 > 8
        long = _mk_member(99, cluster.id)
        long.sanitized_content = "x" * 500                  # dài hơn trần 200
        long.created_at = NOW + timedelta(hours=1)          # member MỚI NHẤT hẳn
        members.append(long)
        payload = loads(build_cluster_payload(cluster, members))

        assert len(payload["snippets"]) == 8                # cap 8
        assert len(payload["snippets"][0]["text"]) <= 200   # cắt đúng trần
        # member mới nhất đứng đầu (created_at = NOW − 0h)
        assert payload["snippets"][0]["feedback_id"] == str(long.id)

    def test_carries_trend_labels_and_choice_list(self) -> None:
        from app.services.insight import build_cluster_payload

        cluster = self._cluster()
        members = [_mk_member(i, cluster.id) for i in range(3)]
        members[0].categories = ["hiệu năng", "hiệu năng"]
        payload = loads(build_cluster_payload(cluster, members))

        assert payload["cluster"]["suggested_priority"] == 0.5
        assert payload["labels"]["severity"]["critical"] == 1   # cycle: 1 critical
        assert payload["labels"]["categories"].count("hiệu năng") == 2
        chosen = {s["feedback_id"] for s in payload["snippets"]}
        assert chosen == {str(m.id) for m in members}       # danh sách để LLM chọn dẫn chứng


class TestFilterEvidence:
    """Server-side validate dẫn chứng (Step 2.4)."""

    def test_whitelist_filters_fake(self) -> None:
        from app.services.insight import filter_evidence

        valid = [uuid4() for _ in range(5)]
        fake1, fake2 = uuid4(), uuid4()
        draft_ids = [valid[0], fake1, valid[1], valid[2], fake2, valid[3], valid[4]]
        out = filter_evidence(draft_ids, set(valid))
        assert set(out) <= set(valid)
        assert len(out) == 5                                # 2 fake bị bỏ

    def test_cap_5_when_more_valid_than_limit(self) -> None:
        from app.services.insight import filter_evidence

        valid = [uuid4() for _ in range(7)]
        assert len(filter_evidence(valid, set(valid))) == 5

    def test_keeps_draft_order_dedup(self) -> None:
        from app.services.insight import filter_evidence

        a, b = uuid4(), uuid4()
        assert filter_evidence([b, a, b, a], {a, b}) == [b, a]

    def test_empty_after_filter_is_none(self) -> None:
        from app.services.insight import filter_evidence

        assert filter_evidence([uuid4(), uuid4()], {uuid4()}) is None


class TestDefaultEvidence:
    """Fallback 0-dẫn-chứng-hợp-le: 3 member priority cao nhất (Step 2.4)."""

    def test_top3_by_severity_then_confidence(self) -> None:
        from app.services.insight import default_evidence

        cid = uuid4()
        # m0 critical/conf 1.0 · m1 high/0.9 · m2 medium/0.8 · m3 low/0.7 · m4 critical/0.6
        members = [_mk_member(i, cid) for i in range(5)]
        out = default_evidence(members)
        assert out == [members[0].id, members[4].id, members[1].id]  # crit, crit, high

    def test_fewer_than_three_members(self) -> None:
        from app.services.insight import default_evidence

        cid = uuid4()
        members = [_mk_member(i, cid) for i in range(2)]
        assert len(default_evidence(members)) == 2


class TestRunInsights:
    """Orchestration Step 2.5–2.7 — LLM mock hoàn toàn."""

    def _settings(self, cap: int = 10):
        from app.core.config import Settings

        return Settings(
            _env_file=None,
            DATABASE_URL="postgresql+psycopg://t:t@h/db",
            INSIGHT_MAX_CLUSTERS=cap,
        )

    @staticmethod
    def _mock_llm(monkeypatch, responder):
        import app.services.insight as mod

        calls: list[str] = []

        def fake(system, user, schema, **kwargs):
            calls.append(user)
            return responder(len(calls) - 1)

        monkeypatch.setattr(mod, "chat_structured", fake)
        return calls

    @staticmethod
    def _draft(evidence_ids):
        from app.schemas.insight import InsightDraft

        return InsightDraft(
            title="Tiêu đề insight test",
            summary="Tóm tắt test.",
            suggested_action="Hành động test.",
            evidence_feedback_ids=evidence_ids,
        )

    def _insight_rows(self, db_session):
        from app.models.insight import Insight

        return db_session.query(Insight).order_by(Insight.title).all()

    def test_cap_limits_llm_calls(
        self, db_session, monkeypatch, _needs_real_db, _no_commit
    ) -> None:
        from app.services.insight import run_insights

        clusters = [_mk_cluster(f"c{i:02d}", 2, round(0.01 * (i + 1), 2)) for i in range(15)]
        for c in clusters:
            db_session.add(c)
            db_session.add_all([_mk_member(0, c.id), _mk_member(1, c.id)])
        db_session.flush()

        calls = self._mock_llm(monkeypatch, lambda _: self._draft([]))

        stats = run_insights(db_session, settings=self._settings(cap=10), now=NOW)

        assert len(calls) == 10                    # 15 cụm → đúng 10 call
        assert stats.insights_generated == 10 and stats.skipped == 0
        handled = {r.cluster_id for r in self._insight_rows(db_session)}
        top10 = {c.id for c in clusters[5:]}       # priority cao = c14…c05
        assert handled == top10

    def test_evidence_whitelist_applied(
        self, db_session, monkeypatch, _needs_real_db, _no_commit
    ) -> None:
        from app.services.insight import run_insights

        cluster = _mk_cluster("wh", 3, 0.9)
        db_session.add(cluster)
        members = [_mk_member(i, cluster.id) for i in range(3)]
        db_session.add_all(members)
        db_session.flush()

        real, fake = members[0].id, uuid4()
        self._mock_llm(monkeypatch, lambda _: self._draft([real, fake]))

        run_insights(db_session, settings=self._settings(), now=NOW)

        rows = self._insight_rows(db_session)
        assert len(rows) == 1
        assert rows[0].evidence_ids == [str(real)]          # id lạ bị lọc

    def test_all_fake_ids_falls_back_to_top3_members(
        self, db_session, monkeypatch, _needs_real_db, _no_commit
    ) -> None:
        from app.services.insight import run_insights

        cluster = _mk_cluster("fb", 4, 0.9)
        db_session.add(cluster)
        members = [_mk_member(i, cluster.id) for i in range(4)]
        db_session.add_all(members)
        db_session.flush()

        self._mock_llm(monkeypatch, lambda _: self._draft([uuid4(), uuid4()]))

        run_insights(db_session, settings=self._settings(), now=NOW)

        rows = self._insight_rows(db_session)
        assert len(rows) == 1                               # vẫn lưu, không skip
        assert rows[0].evidence_ids == [
            str(members[0].id), str(members[1].id), str(members[2].id),
        ]

    def test_one_cluster_fail_skips_without_blocking(
        self, db_session, monkeypatch, _needs_real_db, _no_commit
    ) -> None:
        from app.services.llm_client import LLMStructureError

        from app.services.insight import run_insights

        low, high = _mk_cluster("lo", 2, 0.1), _mk_cluster("hi", 2, 0.9)
        for c in (low, high):
            db_session.add(c)
            db_session.add_all([_mk_member(0, c.id), _mk_member(1, c.id)])
        db_session.flush()

        def responder(n):
            if n == 0:                                      # cụm ưu tiên CAO gọi trước
                raise LLMStructureError("chain thất bại")
            return self._draft([])

        calls = self._mock_llm(monkeypatch, responder)

        stats = run_insights(db_session, settings=self._settings(), now=NOW)

        assert len(calls) == 2                              # cụm còn lại vẫn được xử lý
        assert stats.skipped == 1 and stats.insights_generated == 1
        assert self._insight_rows(db_session)[0].cluster_id == low.id

    def test_rerun_replaces_all_and_resets_status(
        self, db_session, monkeypatch, _needs_real_db, _no_commit
    ) -> None:
        from sqlalchemy import func, select

        from app.models.enums import ReviewStatus
        from app.models.insight import Insight

        from app.services.insight import run_insights

        cluster = _mk_cluster("rr", 3, 0.9)
        db_session.add(cluster)
        db_session.add_all([_mk_member(i, cluster.id) for i in range(3)])
        db_session.flush()

        base = db_session.execute(select(func.count()).select_from(Insight)).scalar()
        self._mock_llm(monkeypatch, lambda _: self._draft([]))

        run_insights(db_session, settings=self._settings(), now=NOW)
        run_insights(db_session, settings=self._settings(), now=NOW)

        after = db_session.execute(select(func.count()).select_from(Insight)).scalar()
        assert after == base + 1                            # replace-all, không nhân bản
        row = db_session.query(Insight).first()
        assert row.review_status == ReviewStatus.unreviewed.value

