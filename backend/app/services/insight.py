"""Insight engine — Phase 15 (plan 15 §3 Task 2).

Evidence-backed: mỗi insight PHẢI trỏ tới feedback id THẬT thuộc đúng cụm.
LLM chỉ ĐỀ XUẤT dẫn chứng từ danh sách id được cung cấp trong payload; server
whitelist-filter sau khi nhận, và fallback 3 member ưu tiên cao nhất khi
không còn dẫn chứng hợp lệ (Step 2.4 — insight không bao giờ thiếu dẫn chứng).

⚠️ PII boundary: snippet trong payload cắt TỪ `sanitized_content` —
`raw_content` không bao giờ ra khỏi biên sanitize (test assert ở
tests/test_insights_unit.py).

Kiến trúc tách lớp như clustering.py: `build_cluster_payload`,
`filter_evidence`, `default_evidence` thuần Python/không DB; chỉ
`run_insights` chạm Session (unit test mock chat_structured + no-op commit).
"""

import json
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.cluster import Cluster
from app.models.enums import LlmCallType, ReviewStatus, Severity
from app.models.feedback import Feedback
from app.models.insight import Insight
from app.schemas.insight import InsightDraft
from app.services.llm_client import LLMStructureError, chat_structured

logger = get_logger(__name__)

INSIGHT_PROMPT_VERSION = "v1"
_SNIPPET_CHARS = 200      # trần ký tự 1 snippet (Step 2.3)
_MAX_SNIPPETS = 8         # tối đa 8 member mới nhất vào payload (Step 2.3)
_EVIDENCE_LIMIT = 5       # tối đa 5 dẫn chứng/insight (Step 2.4, khớp C2)
_DEFAULT_EVIDENCE_COUNT = 3

_SEVERITY_RANK = {s.value: i for i, s in enumerate(Severity)}   # low=0 … critical=3

_INSIGHT_SYSTEM = (
    "Bạn là trợ lý phân tích phản hồi người dùng về sản phẩm AI. Input là JSON "
    "của MỘT cụm phản hồi đã ẩn danh: số liệu trend, nhãn tổng hợp và các "
    "trích dẫn mẫu kèm feedback_id.\n"
    "Viết tiếng Việt:\n"
    "- 'title': tên vấn đề ngắn gọn (≤120 ký tự).\n"
    f"- 'summary': tóm tắt 2–4 câu (≤600 ký tự), MỖI nhận định phải dựa trên "
    "các trích dẫn được cung cấp.\n"
    f"- 'suggested_action': đề xuất hành động cụ thể cho PM (≤400 ký tự).\n"
    f"- 'evidence_feedback_ids': chọn tối đa {_EVIDENCE_LIMIT} feedback_id làm "
    "dẫn chứng, CHỈ TRONG danh sách được cung cấp — không bịa id.\n"
    "Trả về JSON object duy nhất khớp schema yêu cầu."
)


def _sev_value(member) -> str | None:
    sev = getattr(member, "severity", None)
    return getattr(sev, "value", sev)


def _sev_rank(member) -> int:
    return _SEVERITY_RANK.get(_sev_value(member), -1)


def _conf(member) -> float:
    c = getattr(member, "confidence", None)
    return float(c) if c is not None else -1.0


# ------------------------------------------------------------------ pure layer


def build_cluster_payload(cluster, members: Sequence[Feedback]) -> str:
    """JSON payload prompt cho 1 cụm (Step 2.3): trend numbers + nhãn tổng hợp
    + ≤8 snippet 200 ký tự cắt từ sanitized_content của member MỚI NHẤT, kèm
    feedback_id để LLM chọn dẫn chứng."""
    newest_first = sorted(members, key=lambda m: m.created_at, reverse=True)
    snippets = []
    for m in newest_first[:_MAX_SNIPPETS]:
        text = (getattr(m, "sanitized_content", None) or "").strip()
        if text:
            snippets.append({"feedback_id": str(m.id), "text": text[:_SNIPPET_CHARS]})

    severity_counts = Counter(
        v for m in members if (v := _sev_value(m)) is not None
    )
    categories = [
        cat for m in members for cat in (getattr(m, "categories", None) or [])
        if isinstance(cat, str)
    ]
    return json.dumps(
        {
            "cluster": {
                "name": cluster.name,
                "feedback_count": cluster.feedback_count,
                "current_count": cluster.current_count,
                "previous_count": cluster.previous_count,
                "growth_ratio": cluster.growth_ratio,
                "is_emerging": cluster.is_emerging,
                "is_spike": cluster.is_spike,
                "suggested_priority": cluster.suggested_priority,
            },
            "labels": {"severity": dict(severity_counts), "categories": categories},
            "snippets": snippets,
        },
        ensure_ascii=False,
    )


def filter_evidence(
    draft_ids: Sequence[UUID], valid_ids: set[UUID]
) -> list[UUID] | None:
    """Whitelist Step 2.4: chỉ giữ id THẬT thuộc cụm, giữ thứ tự draft,
    dedup, cắt còn ≤5. Rỗng sau lọc → None (caller dùng fallback)."""
    seen: set[UUID] = set()
    out: list[UUID] = []
    for fid in draft_ids:
        if fid not in valid_ids or fid in seen:
            continue
        seen.add(fid)
        out.append(fid)
        if len(out) == _EVIDENCE_LIMIT:
            break
    return out or None


def default_evidence(members: Sequence[Feedback]) -> list[UUID]:
    """Fallback 0-dẫn-chứng-hợp-le: 3 member 'priority' cao nhất — severity
    giảm dần, tie-break confidence giảm dần, cuối cùng mới nhất trước."""
    ranked = sorted(members, key=lambda m: m.created_at, reverse=True)
    ranked.sort(key=lambda m: (-_sev_rank(m), -_conf(m)))
    return [m.id for m in ranked[:_DEFAULT_EVIDENCE_COUNT]]


# ------------------------------------------------------------------ orchestration


@dataclass
class InsightsRunStats:
    insights_generated: int
    skipped: int
    duration_ms: int


def run_insights(
    db: Session,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> InsightsRunStats:
    """Sinh insight cho các cụm ưu tiên cao, replace-all idempotent (Step 2.6).

    Thứ tự như run_clustering: LLM calls chạy TRƯỚC transaction ghi DB; sau đó
    DELETE toàn bộ insights cũ → INSERT insight mới (`review_status='unreviewed'`)
    → commit. 1 cụm fail fallback chain → skip cụm đó, không hỏng cụm khác
    (Step 2.5). `now` chưa dùng trong công thức nào — giữ đối xứng run_clustering.
    """
    settings = settings or get_settings()
    t0 = time.perf_counter()

    clusters = (
        db.execute(
            select(Cluster)
            .order_by(Cluster.suggested_priority.desc().nullslast())
            .limit(settings.INSIGHT_MAX_CLUSTERS)
        )
        .scalars()
        .all()
    )

    generated = skipped = 0
    accepted: list[tuple[Cluster, InsightDraft, list[Feedback]]] = []
    for cluster in clusters:
        members = (
            db.execute(
                select(Feedback)
                .where(Feedback.cluster_id == cluster.id)
                .order_by(Feedback.created_at.desc())
            )
            .scalars()
            .all()
        )
        if not members:                     # cụm không còn member nào → bỏ (Step 2.2)
            skipped += 1
            continue
        try:
            draft = chat_structured(
                _INSIGHT_SYSTEM,
                build_cluster_payload(cluster, members),
                InsightDraft,
                call_type=LlmCallType.generate_insight,
                prompt_version=INSIGHT_PROMPT_VERSION,
            )
        except LLMStructureError as exc:    # 1 cụm fail không chặn cụm khác (Step 2.5)
            logger.warning("insight skip cluster %s (LLM fail): %s", cluster.name, exc)
            skipped += 1
            continue
        accepted.append((cluster, draft, members))

    db.execute(delete(Insight))             # replace-all trong 1 transaction (Step 2.6)
    for cluster, draft, members in accepted:
        evidence = filter_evidence(draft.evidence_feedback_ids, {m.id for m in members})
        if evidence is None:
            evidence = default_evidence(members)
        db.add(
            Insight(
                cluster_id=cluster.id,
                title=draft.title[:120],
                summary=draft.summary[:600],
                suggested_action=draft.suggested_action[:400],
                evidence_ids=[str(u) for u in evidence],
                review_status=ReviewStatus.unreviewed,
            )
        )
        generated += 1
    db.flush()                              # commit tự flush; tường minh để test thấy
    db.commit()

    stats = InsightsRunStats(
        insights_generated=generated,
        skipped=skipped,
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )
    logger.info(
        "insights run: %s generated, %s skipped (%s ms)",
        stats.insights_generated, stats.skipped, stats.duration_ms,
    )
    return stats
