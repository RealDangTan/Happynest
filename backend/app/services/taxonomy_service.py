"""Taxonomy governance service — VoC OS §21 (plan 23) + GPT proposal (plan 31).

Plan 23 (legacy, một phần superseded 2026-10-07): canonical KHÔNG tự mutate —
feedback classify xong chỉ khớp taxonomy hiện có; topic lạ trước đây accumulate
thành emerging theme per-record. Plan 31/34: taxonomy CHỈ đến từ (1) GPT
generate proposal → human apply, (2) GPT recommend từ pool uncategorized →
human apply. `accumulate_emerging` GIỮ lại cho hàng chờ pending cũ nhưng
KHÔNG còn gọi từ runner.

Slug (plan 31): id ổn định cho topic label — root = slugify(name), con =
`slug_cha.slugify(name)`; BẤT BIẾN khi rename `name` (dataset cũ không vỡ).
"""

import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import LlmCallType
from app.models.feedback import Feedback
from app.models.product import Product
from app.models.taxonomy import Taxonomy
from app.schemas.taxonomy import TaxonomyProposalOut
from app.services.llm_client import chat_structured

#: Nhánh canonical gốc seed cho product mới (VoC OS §20) — migration 0010
#: cũng seed cho products tồn tại.
DEFAULT_ROOTS = ("AI Quality", "Search", "Account", "Performance", "Other")


# ---------------------------------------------------------------------------
# Slug helpers (plan 31)
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Tên hiển thị → slug ASCII: bỏ dấu tiếng Việt, ký tự lạ → `_`.

    "Thanh toán" → "thanh_toan"; "Payment failure" → "payment_failure"."""
    normalized = unicodedata.normalize("NFD", text)
    ascii_folded = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_folded.casefold()).strip("_")
    return slug[:80] or "topic"


def ensure_slugs(db: Session, product_id: uuid.UUID) -> int:
    """Gán slug cho node còn NULL (legacy/backfill) — idempotent. Con chỉ nhận
    slug sau khi cha có slug (lặp tối đa 3 pass cho hierarchy 3 cấp). Trả số
    node được gán mới."""
    rows = list(
        db.scalars(select(Taxonomy).where(Taxonomy.product_id == product_id)).all()
    )
    by_id = {r.id: r for r in rows}
    taken = {r.slug for r in rows if r.slug}
    assigned = 0
    for _ in range(3):  # depth ≤ 3 (spec §2)
        progress = False
        for row in rows:
            if row.slug is not None:
                continue
            parent = by_id.get(row.parent_id) if row.parent_id else None
            if row.parent_id is not None and (parent is None or parent.slug is None):
                continue  # đợi pass sau
            base = slugify(row.name)
            if parent is not None and parent.slug:
                base = f"{parent.slug}.{base}"
            slug, i = base, 2
            while slug in taken:
                slug = f"{base}_{i}"
                i += 1
            row.slug = slug
            taken.add(slug)
            assigned += 1
            progress = True
        if not progress:
            break
    db.commit()
    return assigned


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


def get_taxonomy_labels(db: Session, product_id: uuid.UUID) -> list[tuple[str, str]]:
    """(slug, name) của node ACTIVE — tập đóng cho enricher (plan 32).

    Chỉ status="active" (pending_review KHÔNG được phép làm nhãn — spec §2:
    chỉ Active Taxonomy được apply). Tự backfill slug (idempotent) trước khi
    đọc, nên node legacy không bị bỏ sót."""
    ensure_slugs(db, product_id)
    rows = db.execute(
        select(Taxonomy.slug, Taxonomy.name).where(
            Taxonomy.product_id == product_id,
            Taxonomy.status == "active",
            Taxonomy.slug.is_not(None),
        )
    ).all()
    return [(slug, name) for slug, name in rows]


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


# ---------------------------------------------------------------------------
# GPT taxonomy proposal (plan 31 — spec Listen §2): GPT discovers, human applies
# ---------------------------------------------------------------------------

PROMPT_VERSION_TAXONOMY = "v1"

_GENERATE_SYSTEM = """Bạn là chuyên gia phân tích phản hồi người dùng (VoC) về sản phẩm số có tính năng AI. \
Văn phong làm việc: tiếng Việt, trộn thuật ngữ kỹ thuật tiếng Anh là bình thường.

Nhiệm vụ: đề xuất TOPIC HIERARCHY 2 cấp để phân loại feedback cho sản phẩm, dựa trên sample feedback và context được cung cấp.

Quy tắc bắt buộc:
- 3–6 chủ đề GỐC; mỗi gốc 0–6 chủ đề CON là khía cạnh cụ thể (ví dụ Payment → Payment failure, Refund).
- `name` ngắn gọn (≤ 6 từ), dùng đúng thuật ngữ người dùng hay nói trong sample.
- KHÔNG tạo topic về cảm xúc/sentiment/mức độ — chỉ chủ đề nội dung.
- `parent` phải là `name` CHÍNH XÁC của một topic khác trong danh sách; None cho topic gốc.
- Phủ tối đa các chủ đề xuất hiện trong sample; không bịa chủ đề không có dấu hiệu.

Chỉ trả về JSON object khớp schema, không text thừa."""


def generate_proposal(
    db: Session,
    product: Product,
    *,
    sample_size: int = 30,
    context: dict | None = None,
) -> tuple[TaxonomyProposalOut, int]:
    """GPT sinh proposal taxonomy từ sample feedback (ĐÃ SANITIZE) + context.

    ⚠️ PII boundary: chỉ `feedback_text` (đã qua presidio) được đưa vào prompt —
    `raw_content` KHÔNG BAO GIỜ. Proposal STATELESS — không đụng DB tới khi
    human gọi apply.

    Trả (proposal, sample_count)."""
    samples = [
        s
        for s in db.scalars(
            select(Feedback.feedback_text)
            .where(
                Feedback.product_id == product.id,
                Feedback.feedback_text.is_not(None),
            )
            .order_by(Feedback.occurred_at.desc())
            .limit(sample_size)
        ).all()
        if s
    ]
    payload = {
        "product": {"name": product.name, "description": product.description},
        "context": context or {},
        "sample_feedback": samples,
    }
    proposal = chat_structured(
        _GENERATE_SYSTEM,
        json.dumps(payload, ensure_ascii=False),
        TaxonomyProposalOut,
        call_type=LlmCallType.taxonomy_generate,
        prompt_version=PROMPT_VERSION_TAXONOMY,
    )
    return proposal, len(samples)


def apply_proposal(
    db: Session, product: Product, proposal: TaxonomyProposalOut
) -> dict:
    """Human apply proposal (có thể đã sửa) → tạo node canonical/active.

    Idempotent: node trùng name (case-insensitive) hoặc trùng slug bị SKIP.
    Parent phải là topic khác trong proposal hoặc node đang tồn tại — violate
    → ValueError (route quy đổi 422). Bump `products.taxonomy_version` MỖI lần
    apply (governance event) — commit do hàm này tự quản (khớp seed_default)."""
    ensure_slugs(db, product.id)
    existing_rows = list(
        db.scalars(select(Taxonomy).where(Taxonomy.product_id == product.id)).all()
    )
    existing_by_name = {r.name.casefold(): r for r in existing_rows}
    slug_taken = {r.slug for r in existing_rows if r.slug}
    new_nodes: dict[str, Taxonomy] = {}
    created: list[Taxonomy] = []
    skipped = 0

    def _parent_for(topic) -> Taxonomy | None:
        if topic.parent is None:
            return None
        key = topic.parent.strip().casefold()
        row = existing_by_name.get(key) or new_nodes.get(key)
        if row is None:
            raise ValueError(
                f"parent '{topic.parent}' của topic '{topic.name}' không tồn tại "
                "trong proposal hoặc taxonomy hiện tại."
            )
        return row

    def _unique_slug(base: str) -> str:
        slug, i = base, 2
        while slug in slug_taken:
            slug = f"{base}_{i}"
            i += 1
        slug_taken.add(slug)
        return slug

    pending = list(proposal.topics)
    for _ in range(len(pending) + 1):
        progress = False
        rest = []
        for topic in pending:
            key = topic.name.strip().casefold()
            if not key:
                skipped += 1
                progress = True
                continue
            if key in existing_by_name or key in new_nodes:
                skipped += 1
                progress = True
                continue
            try:
                parent_row = _parent_for(topic)
            except ValueError:
                rest.append(topic)
                continue
            base = slugify(topic.name)
            if parent_row is not None and parent_row.slug:
                base = f"{parent_row.slug}.{base}"
            node = Taxonomy(
                # id tường minh: default=uuid.uuid4 chỉ populate lúc FLUSH —
                # con tạo trong cùng pass đọc parent_row.id cần giá trị ngay.
                id=uuid.uuid4(),
                product_id=product.id,
                parent_id=parent_row.id if parent_row else None,
                name=topic.name.strip(),
                slug=_unique_slug(base),
                description=topic.description,
                kind="canonical",
                status="active",
            )
            db.add(node)
            new_nodes[key] = node
            created.append(node)
            progress = True
        pending = rest
        if not pending or not progress:
            break
    if pending:
        db.rollback()
        raise ValueError(
            "Proposal chứa topic có parent không tồn tại/vòng lặp: "
            + ", ".join(t.name for t in pending)
        )

    # Re-fetch trong session hiện tại: `product` có thể là instance DETACHED từ
    # session khác (fixture/route) — mutation trên detached không bao giờ commit.
    product_row = db.get(Product, product.id)
    assert product_row is not None
    product_row.taxonomy_version = (product_row.taxonomy_version or 1) + 1
    db.commit()
    return {
        "created": created,
        "skipped": skipped,
        "taxonomy_version": product_row.taxonomy_version,
    }
