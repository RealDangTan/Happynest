"""Taxonomy governance service — VoC OS §21 (plan 23).

Canonical taxonomy KHÔNG BAO GIỜ tự mutate bởi AI:
- Feedback classify xong → topics khớp taxonomy hiện có (canonical active +
  emerging active) → OK.
- Topic lạ → accumulate thành emerging theme (status=pending_review,
  evidence_count += 1/feedback) → human review (Gate endpoint) →
  approve (lên canonical) / merge (gộp vào node khác) / reject.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.taxonomy import Taxonomy

#: Nhánh canonical gốc seed cho product mới (VoC OS §20) — migration 0010
#: cũng seed cho products tồn tại.
DEFAULT_ROOTS = ("AI Quality", "Search", "Account", "Performance", "Other")


def get_taxonomy_names(db: Session, product_id: uuid.UUID) -> list[str]:
    """Names có thể dùng khi classify: canonical active + emerging active +
    emerging PENDING_REVIEW (chưa duyệt nhưng đã tồn tại — không nhân bản
    case-variant trong hàng chờ)."""
    rows = db.scalars(
        select(Taxonomy.name).where(
            Taxonomy.product_id == product_id,
            Taxonomy.status.in_(["active", "pending_review"]),
        )
    ).all()
    return list(rows)


def seed_default_taxonomy(db: Session, product_id: uuid.UUID) -> None:
    """Tạo 5 nhánh canonical gốc nếu product chưa có taxonomy nào."""
    exists = db.scalars(
        select(Taxonomy.id).where(Taxonomy.product_id == product_id).limit(1)
    ).first()
    if exists is not None:
        return
    for name in DEFAULT_ROOTS:
        db.add(
            Taxonomy(product_id=product_id, name=name, kind="canonical", status="active")
        )
    db.commit()


def accumulate_emerging(
    db: Session,
    product_id: uuid.UUID,
    topics: list[str],
    *,
    taxonomy_names: list[str] | None = None,
) -> list[str]:
    """Đưa topic LẠ về hàng chờ emerging — idempotent theo (product, name).

    Trả list topic names KHÔNG có trong taxonomy (các emerging mới/cập nhật).
    Gọi SAU khi classify trong runner (plan 23 Task 3).
    """
    if taxonomy_names is None:
        taxonomy_names = get_taxonomy_names(db, product_id)
    known = {n.casefold() for n in taxonomy_names}
    now = datetime.now(timezone.utc)
    new_topics: list[str] = []

    for topic in topics or []:
        if not isinstance(topic, str) or not topic.strip():
            continue
        topic = topic.strip()
        if topic.casefold() in known:
            continue
        new_topics.append(topic)
        row = db.scalars(
            select(Taxonomy).where(
                Taxonomy.product_id == product_id,
                Taxonomy.name == topic,
            )
        ).first()
        if row is None:
            db.add(
                Taxonomy(
                    product_id=product_id,
                    name=topic,
                    kind="emerging",
                    status="pending_review",
                    evidence_count=1,
                    first_seen=now,
                    last_seen=now,
                )
            )
        elif row.status == "pending_review":
            row.evidence_count += 1
            row.last_seen = now
        # status merged/rejected → không tái kích hoạt (human đã quyết)
    db.commit()
    return new_topics


def approve_theme(db: Session, theme: Taxonomy) -> Taxonomy:
    """Approve emerging → trở thành canonical node active."""
    theme.kind = "canonical"
    theme.status = "active"
    db.commit()
    db.refresh(theme)
    return theme


def reject_theme(db: Session, theme: Taxonomy) -> Taxonomy:
    theme.status = "rejected"
    db.commit()
    db.refresh(theme)
    return theme


def merge_theme(db: Session, theme: Taxonomy, target: Taxonomy) -> Taxonomy:
    """Merge: feedback topics trỏ sang tên node đích; theme bị đánh dấu merged."""
    rows = db.scalars(
        select(Feedback).where(
            Feedback.product_id == theme.product_id,
            Feedback.ai_analysis["topics"].contains([theme.name]),
        )
    ).all()
    for fb in rows:
        analysis = dict(fb.ai_analysis or {})
        topics = analysis.get("topics") or []
        analysis["topics"] = [target.name if t == theme.name else t for t in topics]
        fb.ai_analysis = analysis
    theme.status = "merged"
    target.evidence_count = (target.evidence_count or 0) + theme.evidence_count
    target.last_seen = datetime.now(timezone.utc)
    db.commit()
    db.refresh(theme)
    return theme
