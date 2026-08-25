"""Clustering engine — Phase 14 (plan 14 §3 Task 2/3).

Trend formulas là CÔNG THỨC CHUẨN chốt cứng trong plan (executor copy nguyên
xi, không tự chế); đổi scale `suggested_priority` sau này phải qua decisions.

Kiến trúc tách lớp để unit test offline: `cluster_embeddings`,
`group_feedbacks`, `build_naming_payload`, `apply_names`, `split_embedded`
thuần Python/không DB; chỉ `run_clustering` chạm Session (được suite
integration phủ trên data thật — plan §3 Task 4).

⚠️ PII boundary: snippet trong payload naming cắt TỪ `sanitized_content` —
`raw_content` không bao giờ ra khỏi biên sanitize (test assert ở
tests/test_clustering_unit.py).
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
from pydantic import BaseModel, Field as PydField
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.cluster import Cluster
from app.models.enums import LlmCallType
from app.models.feedback import Feedback
from app.models.insight import Insight
from app.services.llm_client import LLMStructureError, chat_structured

logger = get_logger(__name__)

NAMING_PROMPT_VERSION = "v1"
_SNIPPET_CHARS = 200
_SAMPLES_PER_CLUSTER = 5
_NAME_MAX = 80
_SUMMARY_MAX = 300

_NAMING_SYSTEM = (
    "Bạn là trợ lý phân tích phản hồi người dùng. Input là JSON danh sách các "
    "cụm phản hồi đã được gom bởi thuật toán, mỗi cụm có 'idx' và tối đa 5 "
    "trích dẫn mẫu (đãẩn danh). Với MỖI cụm, đặt:\n"
    f"- 'name': tên cụm tiếng Việt ngắn gọn (≤{_NAME_MAX} ký tự), mô tả chủ đề chung.\n"
    f"- 'summary': tóm tắt 1–2 câu tiếng Việt (≤{_SUMMARY_MAX} ký tự) về vấn đề "
    "chính mà các phản hồi trong cụm nêu lên.\n"
    "Trả về JSON object duy nhất khớp schema yêu cầu, giữ đúng 'idx' của từng cụm."
)


class _ClusterNaming(BaseModel):
    """Một entry naming do LLM trả cho 1 cụm."""

    idx: int
    name: str = PydField(max_length=_NAME_MAX)
    summary: str = PydField(max_length=_SUMMARY_MAX)


class NamingOut(BaseModel):
    """Schema structured-output của call naming (đúng 1 call / run)."""

    clusters: list[_ClusterNaming]


@dataclass
class MemberGroup:
    """Một cụm in-memory trước khi ghi DB."""

    label_idx: int
    members: list[Feedback]
    name: str = ""
    summary: str = ""


@dataclass
class ClusteringRunStats:
    clusters_upserted: int
    assigned_count: int
    unassigned_count: int
    excluded_no_embedding: int


# ------------------------------------------------------------------ pure layer


def split_embedded(rows: Sequence[Feedback]) -> tuple[list[Feedback], int]:
    """Tách row thiếu embedding — contract C5 bắt buộc báo excluded count."""
    embedded = [r for r in rows if r.embedding is not None]
    return embedded, len(rows) - len(embedded)


def cluster_embeddings(X: np.ndarray, settings: Settings) -> np.ndarray:
    """HDBSCAN metric cosine — tái dùng bằng chứng spike S4. Label −1 = noise."""
    from sklearn.cluster import HDBSCAN  # import muộn — unit thuần không đụng sklearn

    if len(X) < 2:
        return np.full(len(X), -1, dtype=int)
    return HDBSCAN(
        metric="cosine", min_cluster_size=settings.CLUSTER_MIN_SIZE
    ).fit_predict(X)


def group_feedbacks(feedbacks: Sequence[Feedback], labels: np.ndarray) -> list[MemberGroup]:
    """Gom member theo label ≠ −1; cụm sắp theo size giảm dần để idx ổn định."""
    by_label: dict[int, list[Feedback]] = {}
    for fb, label in zip(feedbacks, labels):
        if label == -1:
            continue  # noise → không gán cụm, cluster_id giữ NULL
        by_label.setdefault(int(label), []).append(fb)
    ordered = sorted(by_label.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    return [MemberGroup(label_idx=i, members=members) for i, (_, members) in enumerate(ordered)]


def build_naming_payload(groups: Sequence[MemberGroup]) -> str:
    """JSON payload naming: ≤5 snippet/cụm cắt từ sanitized_content (PII boundary)."""
    import json

    payload = []
    for group in groups:
        ranked = sorted(
            group.members,
            key=lambda m: m.confidence if m.confidence is not None else -1.0,
            reverse=True,
        )
        snippets = []
        for m in ranked[:_SAMPLES_PER_CLUSTER]:
            text = (m.sanitized_content or "").strip()
            if text:
                snippets.append(text[:_SNIPPET_CHARS])
        payload.append({"idx": group.label_idx, "samples": snippets})
    return json.dumps({"clusters": payload}, ensure_ascii=False)


def _fallback_name(group: MemberGroup) -> tuple[str, str]:
    """Fallback KHÔNG tốn LLM: tên đánh số + summary ghép top categories."""
    cats = Counter(
        cat
        for m in group.members
        for cat in (m.categories or [])
        if isinstance(cat, str)
    )
    top = ", ".join(cat for cat, _ in cats.most_common(3))
    summary = (
        f"Nhóm {len(group.members)} phản hồi cùng chủ đề"
        + (f": {top}" if top else ".")
    )
    return f"Cụm #{group.label_idx}", summary[:_SUMMARY_MAX]


def apply_names(
    groups: list[MemberGroup],
    naming: NamingOut | None,
) -> None:
    """Điền name/summary vào từng nhóm; LLM bỏ sót/fail → fallback không tốn tiền."""
    named: dict[int, _ClusterNaming] = {}
    if naming is not None:
        for entry in naming.clusters:
            if 0 <= entry.idx < len(groups):
                named[entry.idx] = entry
    for group in groups:
        entry = named.get(group.label_idx)
        if entry is not None:
            group.name = entry.name[:_NAME_MAX]
            group.summary = entry.summary[:_SUMMARY_MAX]
        else:
            group.name, group.summary = _fallback_name(group)


# --------------------------------------------------------------- orchestration


def run_clustering(
    db: Session,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> ClusteringRunStats:
    """Chạy trọn vòng clustering idempotent theo thứ tự C5, TRONG 1 transaction.

    DELETE insights → DELETE clusters → NULL feedbacks.cluster_id → INSERT
    cụm mới (trend + naming) → gán lại membership → commit. Lỗi giữa chừng →
    rollback, DB về trạng thái cũ.
    """
    settings = settings or get_settings()
    now = now or datetime.now(timezone.utc)

    rows = db.execute(select(Feedback)).scalars().all()
    feedbacks, excluded = split_embedded(rows)

    if not feedbacks:
        # Không có vector nào: vẫn phải xoá sạch cụm cũ để trạng thái nhất quán
        db.execute(delete(Insight))
        db.execute(delete(Cluster))
        db.execute(update(Feedback).values(cluster_id=None))
        db.commit()
        return ClusteringRunStats(0, 0, 0, excluded)

    X = np.stack([np.asarray(fb.embedding, dtype=np.float32) for fb in feedbacks])
    groups = group_feedbacks(feedbacks, cluster_embeddings(X, settings))

    naming: NamingOut | None = None
    if groups:
        try:
            naming = chat_structured(
                _NAMING_SYSTEM,
                build_naming_payload(groups),
                NamingOut,
                call_type=LlmCallType.name_cluster,
                prompt_version=NAMING_PROMPT_VERSION,
            )
        except LLMStructureError as exc:
            logger.warning("cluster naming fallback (LLM fail): %s", exc)
    apply_names(groups, naming)

    assigned = sum(len(g.members) for g in groups)
    unassigned = len(feedbacks) - assigned

    # --- Rebuild idempotent trong 1 transaction (thứ tự C5) ---
    db.execute(delete(Insight))          # insights FK trỏ clusters → xoá trước
    db.execute(delete(Cluster))
    db.execute(
        update(Feedback)
        .values(cluster_id=None)
        .execution_options(synchronize_session=False)
    )
    for fb in rows:                      # đồng bộ identity map MỌI row đang load
        fb.cluster_id = None

    total_members = 0
    try:
        for group in groups:
            trend = compute_trend(group.members, now, settings)
            cluster = Cluster(
                name=group.name,
                summary=group.summary,
                **trend,
            )
            db.add(cluster)
            db.flush()                    # cần cluster.id trước khi gán member
            for fb in group.members:
                fb.cluster_id = cluster.id
            total_members += len(group.members)
        db.commit()
    except Exception:                     # lỗi giữa chừng → DB về trạng thái cũ
        db.rollback()
        raise

    stats = ClusteringRunStats(
        clusters_upserted=len(groups),
        assigned_count=total_members,
        unassigned_count=unassigned,
        excluded_no_embedding=excluded,
    )
    logger.info(
        "clustering run: %s clusters, %s assigned, %s unassigned (+%s no-embedding)",
        stats.clusters_upserted, stats.assigned_count,
        stats.unassigned_count, stats.excluded_no_embedding,
    )
    return stats


def compute_trend(
    members: Sequence, now: datetime, settings: Settings
) -> dict:
    """Tính trend fields cho 1 cụm từ members (duck-typed: created_at, severity).

    Công thức chuẩn plan 14 §3 Task 2 — xem header module trước khi sửa.
    """
    window = timedelta(days=settings.CLUSTER_WINDOW_DAYS)
    current_cut = now - window          # [now−W, now]
    previous_cut = now - 2 * window     # [now−2W, now−W)

    in_current = [m for m in members if current_cut <= m.created_at <= now]
    in_previous = [
        m for m in members if previous_cut <= m.created_at < current_cut
    ]
    current = len(in_current)
    previous = len(in_previous)

    # growth_ratio: chặn inf ra JSON — previous==0 → trần 9.99 khi có current
    if previous > 0:
        growth_ratio = round(current / previous, 2)
    else:
        growth_ratio = 9.99 if current > 0 else 0.0

    is_spike = (
        previous > 0
        and current >= settings.CLUSTER_SPIKE_MIN_CURRENT
        and current / previous >= settings.CLUSTER_SPIKE_RATIO
    )
    is_emerging = previous == 0 and current >= settings.CLUSTER_EMERGING_MIN

    created = sorted(m.created_at for m in members)
    high_critical = sum(
        1 for m in members if getattr(m, "severity", None) in ("high", "critical")
    )
    suggested_priority = round(
        0.5 * min(len(members) / 50, 1)
        + 0.3 * (1 if (is_spike or is_emerging) else 0)
        + 0.2 * (high_critical / len(members)),
        2,
    )

    return {
        "feedback_count": len(members),
        "first_seen": created[0],
        "last_seen": created[-1],
        "current_count": current,
        "previous_count": previous,
        "growth_ratio": growth_ratio,
        "is_emerging": is_emerging,
        "is_spike": is_spike,
        "suggested_priority": suggested_priority,
    }
