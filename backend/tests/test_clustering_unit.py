"""Unit test thuần clustering — Phase 14 Task 2 + Task 3 Step 3.5.

Không chạm DB: members là SimpleNamespace, LLM mock/raise qua monkeypatch.
Công thức chuẩn copy nguyên xi từ plan 14 §3 Task 2 — fixture phủ cả 4 nhánh:
spike / emerging / ratio bình thường / cụm cũ xa. Phần engine phủ: số cụm,
noise không vào group, excluded_count, payload chỉ chứa sanitized (PII),
fallback naming khi LLM fail.
"""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np

from app.services import clustering
from app.services.clustering import (
    NamingOut,
    apply_names,
    build_naming_payload,
    cluster_embeddings,
    compute_trend,
    group_feedbacks,
    split_embedded,
)
from app.services.llm_client import LLMStructureError

NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)

SETTINGS_STUB = SimpleNamespace(
    CLUSTER_WINDOW_DAYS=30,
    CLUSTER_SPIKE_RATIO=2.0,
    CLUSTER_SPIKE_MIN_CURRENT=5,
    CLUSTER_EMERGING_MIN=3,
)

# Stub thêm cho phần engine (Task 3) — min_cluster_size nhỏ để toy matrix ra cụm
ENGINE_SETTINGS_STUB = SimpleNamespace(
    CLUSTER_MIN_SIZE=5,
    CLUSTER_WINDOW_DAYS=30,
    CLUSTER_SPIKE_RATIO=2.0,
    CLUSTER_SPIKE_MIN_CURRENT=5,
    CLUSTER_EMERGING_MIN=3,
)


def _member(days_ago: float, severity: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        occurred_at=NOW - timedelta(days=days_ago),
        ai_analysis={"severity": severity} if severity else None,
    )


def test_branch_spike() -> None:
    """current≥min_current và gấp đôi previous → spike, ratio 2.0."""
    members = (
        [_member(45) for _ in range(4)]      # previous window [−60d, −30d)
        + [_member(5) for _ in range(8)]     # current window [−30d, now]
        + [_member(5, "high") for _ in range(3)]
    )
    t = compute_trend(members, NOW, SETTINGS_STUB)
    assert t["feedback_count"] == 15
    assert t["current_count"] == 11
    assert t["previous_count"] == 4
    assert t["growth_ratio"] == 2.75
    assert t["is_spike"] is True
    assert t["is_emerging"] is False
    # 0.5·min(15/50,1)=0.15 · +0.3 spike · +0.2·(3/15)=0.04 → 0.49
    assert t["suggested_priority"] == 0.49
    assert t["first_seen"] == min(m.occurred_at for m in members)
    assert t["last_seen"] == max(m.occurred_at for m in members)


def test_branch_emerging() -> None:
    """previous==0, current≥EMERGING_MIN → cụm hoàn toàn mới, ratio trần 9.99."""
    members = [_member(10) for _ in range(5)]
    t = compute_trend(members, NOW, SETTINGS_STUB)
    assert t["current_count"] == 5
    assert t["previous_count"] == 0
    assert t["growth_ratio"] == 9.99
    assert t["is_spike"] is False
    assert t["is_emerging"] is True


def test_branch_normal_ratio_below_thresholds() -> None:
    """Có cả hai cửa sổ nhưng chưa chạm ngưỡng spike → chỉ ratio thường."""
    members = [_member(40) for _ in range(6)] + [_member(10) for _ in range(4)]
    t = compute_trend(members, NOW, SETTINGS_STUB)
    assert t["current_count"] == 4
    assert t["previous_count"] == 6
    assert t["growth_ratio"] == 0.67  # round(4/6, 2)
    assert t["is_spike"] is False     # current 4 < SPIKE_MIN_CURRENT
    assert t["is_emerging"] is False


def test_branch_stale_cluster() -> None:
    """Toàn bộ member ngoài 2 cửa sổ → current=previous=0, ratio 0.0."""
    members = [_member(100) for _ in range(7)]
    t = compute_trend(members, NOW, SETTINGS_STUB)
    assert t["feedback_count"] == 7
    assert t["current_count"] == 0
    assert t["previous_count"] == 0
    assert t["growth_ratio"] == 0.0
    assert t["is_spike"] is False
    assert t["is_emerging"] is False


# ------------------------------------------------------- Task 3 — engine thuần

_DIM = 8


def _fb(idx: int, embedding, **kwargs) -> SimpleNamespace:
    return SimpleNamespace(id=f"fb-{idx}", embedding=embedding, **kwargs)


def _toy_matrix() -> tuple[list[SimpleNamespace], np.ndarray]:
    """2 cụm tách biệt rõ trong không gian cosine + noise — seed cố định.

    Số điểm noise cố ý < CLUSTER_MIN_SIZE (5) để chúng bất khả tự lập thành
    cụm thứ 3 — chỉ có thể là noise hoặc bị hút vào cụm sẵn.
    """
    rng = np.random.default_rng(42)
    base_a = np.zeros(_DIM); base_a[0] = 1.0
    base_b = np.zeros(_DIM); base_b[1] = 1.0
    vecs = []
    vecs += [base_a + rng.normal(scale=0.01, size=_DIM) for _ in range(12)]
    vecs += [base_b + rng.normal(scale=0.01, size=_DIM) for _ in range(12)]
    noise = rng.uniform(0.2, 0.8, size=(4, _DIM))   # 4 < min_cluster_size
    X = np.asarray(vecs + list(noise), dtype=np.float32)
    rows = [
        _fb(i, v, feedback_text=f"sanitized {i}", raw_content="RAW",
            ai_analysis={"confidence": 0.9, "topics": ["cat"]}, occurred_at=NOW)
        for i, v in enumerate(X)
    ]
    return rows, X


def test_cluster_embeddings_finds_two_clusters_and_noise() -> None:
    rows, X = _toy_matrix()
    labels = cluster_embeddings(X, ENGINE_SETTINGS_STUB)
    real = sorted(set(labels) - {-1})
    assert len(real) == 2                      # đúng số cụm mô phỏng
    assert (labels == -1).sum() >= 1           # noise tồn tại và bị đánh dấu −1


def test_group_feedbacks_excludes_noise_and_orders_by_size() -> None:
    rows, X = _toy_matrix()
    labels = cluster_embeddings(X, ENGINE_SETTINGS_STUB)
    groups = group_feedbacks(rows, labels)
    assigned = sum(len(g.members) for g in groups)
    assert assigned == len(rows) - (labels == -1).sum()
    for g in groups:
        for m in g.members:
            assert labels[int(str(m.id).split("-")[1])] != -1  # noise không vào nhóm
    # size giảm dần → idx ổn định giữa các run
    sizes = [len(g.members) for g in groups]
    assert sizes == sorted(sizes, reverse=True)


def test_split_embedded_counts_missing_vectors() -> None:
    _, X = _toy_matrix()
    rows = [
        _fb(0, X[0]), _fb(1, None), _fb(2, X[1]), _fb(3, None), _fb(4, None),
    ]
    embedded, excluded = split_embedded(rows)
    assert len(embedded) == 2
    assert excluded == 3                       # đếm đủ row thiếu vector (C5)


def test_naming_payload_sanitized_only() -> None:
    """PII boundary: payload naming KHÔNG bao giờ chứa raw_content."""
    rows, _ = _toy_matrix()
    rows[0].raw_content = "SĐT thật 0901234567 của Nguyễn Văn A"
    rows[0].feedback_text = "sanitized an toàn"
    groups = [clustering.MemberGroup(label_idx=0, members=rows[:6])]
    payload = build_naming_payload(groups)
    data = json.loads(payload)
    assert "0901234567" not in payload and "Nguyễn" not in payload
    assert data["clusters"][0]["samples"][0] == "sanitized an toàn"


def test_apply_names_happy_path_covers_all() -> None:
    groups = [clustering.MemberGroup(label_idx=i, members=[_member(1)]) for i in range(2)]
    naming = NamingOut.model_validate({
        "clusters": [
            {"idx": 0, "name": "Lỗi đăng nhập", "summary": "Người dùng không login được."},
            {"idx": 1, "name": "App chậm", "summary": "Màn hình tải quá lâu."},
        ]
    })
    apply_names(groups, naming)
    assert groups[0].name == "Lỗi đăng nhập"
    assert groups[1].name == "App chậm"


def test_apply_names_llm_fail_falls_back_without_cost() -> None:
    """LLStructureError → mọi nhóm có tên fallback, không còn phụ thuộc LLM."""
    rows, X = _toy_matrix()
    for r in rows:                                 # mọi member cùng topics →
        r.ai_analysis = {"topics": ["performance", "bug"]}  # summary nào cũng ghép được top
    groups = group_feedbacks(rows, cluster_embeddings(X, ENGINE_SETTINGS_STUB))
    apply_names(groups, None)                  # nhánh LLM fail hoàn toàn
    for g in groups:
        assert g.name.startswith("Cụm #")
        assert "performance" in g.summary      # summary ghép top topics


def test_apply_names_partial_coverage_fills_gap() -> None:
    """LLM trả thiếu 1 idx → idx đó tự lấp bằng fallback."""
    groups = [clustering.MemberGroup(label_idx=i, members=[_member(1)]) for i in range(2)]
    naming = NamingOut.model_validate({
        "clusters": [{"idx": 1, "name": "Chỉ cụm 1", "summary": "s"}]
    })
    apply_names(groups, naming)
    assert groups[0].name.startswith("Cụm #")  # idx 0 bị bỏ sót → fallback
    assert groups[1].name == "Chỉ cụm 1"


def test_run_clustering_end_to_end_with_mocks(monkeypatch) -> None:
    """run_clustering qua fake Session in-memory: stats khớp, noise không gán cụm.

    Fake session ghi nhận add()/flush()/commit thay vì đụng DB thật (phần DB
    orchestration thật do suite integration phủ trên Supabase — Task 4).
    """
    from datetime import timezone as tz

    now = datetime.now(tz.utc)
    rows, X = _toy_matrix()
    rows.append(_fb(999, None, feedback_text="x", raw_content="y",
                    ai_analysis=None, occurred_at=now))

    class _Result:
        def scalars(self):
            return self

        def all(self):
            return rows

    class _FakeSession:
        def __init__(self):
            self.added = []
            self.committed = False

        def execute(self, *a, **k):
            return _Result()

        def add(self, obj):
            self.added.append(obj)

        def flush(self):
            for c in self.added:
                if getattr(c, "id", None) is None:
                    c.id = f"c-{len(self.added)}"

        def commit(self):
            self.committed = True

        def rollback(self):  # pragma: no cover — nhánh lỗi do integration phủ
            pass

    session = _FakeSession()

    captured: dict = {}

    def fake_chat(system, user, schema, **kwargs):
        captured["payload"] = user
        captured["call_type"] = kwargs["call_type"]
        return NamingOut.model_validate({
            "clusters": [
                {"idx": 0, "name": "Cụm A", "summary": "Nhóm A"},
                {"idx": 1, "name": "Cụm B", "summary": "Nhóm B"},
            ]
        })

    monkeypatch.setattr(clustering, "chat_structured", fake_chat)

    stats = clustering.run_clustering(session, ENGINE_SETTINGS_STUB, now=now)

    assert stats.clusters_upserted == 2
    total_embedded = 28                       # 12 + 12 + 4 noise
    assert stats.excluded_no_embedding == 1
    # Bất biến C5: mọi row có embedding nằm hết trong assigned hoặc unassigned.
    # Số noise chính xác KHÔNG khóa cứng — HDBSCAN được phép hút điểm xa vào cụm.
    assert stats.assigned_count + stats.unassigned_count == total_embedded
    assert session.committed is True
    assert len(session.added) == 2
    # mỗi cluster nhận trend fields đầy đủ từ compute_trend
    for c in session.added:
        assert c.feedback_count > 0
        assert c.growth_ratio in (0.0, 9.99) or isinstance(c.growth_ratio, float)
    # đúng 1 call naming / run, đúng call_type
    assert captured["call_type"] == clustering.LlmCallType.name_cluster
    assert "RAW" not in captured["payload"]    # PII boundary qua cả đường mock


def test_run_clustering_empty_db_is_safe(monkeypatch) -> None:
    """DB trống hoàn toàn → stats 0, vẫn commit sạch không nổ."""

    class _EmptyResult:
        def scalars(self):
            return self

        def all(self):
            return []

    class _FakeSession:
        def __init__(self):
            self.executed = []
            self.committed = False

        def execute(self, stmt, *a, **k):
            self.executed.append(stmt)
            return _EmptyResult()

        def add(self, obj):  # pragma: no cover
            raise AssertionError("không được insert cluster khi DB trống")

        def flush(self):  # pragma: no cover
            pass

        def commit(self):
            self.committed = True

        def rollback(self):  # pragma: no cover
            pass

    session = _FakeSession()

    def fail_chat(*a, **k):  # pragma: no cover — không được gọi LLM khi rỗng
        raise AssertionError("không gọi naming khi không có cụm")

    monkeypatch.setattr(clustering, "chat_structured", fail_chat)
    stats = clustering.run_clustering(session, ENGINE_SETTINGS_STUB, now=NOW)
    assert stats == clustering.ClusteringRunStats(0, 0, 0, 0)
    assert session.committed is True
