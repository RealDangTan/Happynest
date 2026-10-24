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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import LlmCallType
from app.models.feedback import Feedback
from app.models.product import Product
from app.models.taxonomy import Taxonomy
from app.schemas.taxonomy import TopicRecommendationOut, TaxonomyProposalOut
from app.services.llm_client import chat_structured

#: Nhánh canonical gốc seed cho product mới (VoC OS §20) — migration 0010 seed
#: tên tiếng Anh, 0021 vi hóa `name` (2026-10-22), 0023 ĐẢO lại (2026-10-23):
#: `name` = tiếng Anh canonical (codebook classify nhất quán), `name_vi` =
#: tiếng Việt chỉ để hiển thị. Slug vẫn do slugify(`name`) sinh — khớp bộ
#: slug gốc của migration 0010 (ai_quality, search, account, performance, other).
DEFAULT_ROOTS: tuple[tuple[str, str], ...] = (
    ("AI Quality", "Chất lượng AI"),
    ("Search", "Tìm kiếm"),
    ("Account", "Tài khoản"),
    ("Performance", "Hiệu năng"),
    ("Other", "Khác"),
)


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


def get_taxonomy_labels(db: Session, product_id: uuid.UUID) -> list[tuple[str, str, str | None]]:
    """(slug, name, name_vi) của node ACTIVE — tập đóng cho enricher (plan 32).

    Chỉ status="active" (pending_review KHÔNG được phép làm nhãn — spec §2:
    chỉ Active Taxonomy được apply). Tự backfill slug (idempotent) trước khi
    đọc, nên node legacy không bị bỏ sót. `name` = tiếng Anh canonical,
    `name_vi` = nhãn hiển thị tiếng Việt (gloss cho prompt classify)."""
    ensure_slugs(db, product_id)
    rows = db.execute(
        select(Taxonomy.slug, Taxonomy.name, Taxonomy.name_vi).where(
            Taxonomy.product_id == product_id,
            Taxonomy.status == "active",
            Taxonomy.slug.is_not(None),
        )
    ).all()
    return [(slug, name, name_vi) for slug, name, name_vi in rows]


def seed_default_taxonomy(db: Session, product_id: uuid.UUID) -> None:
    """Tạo 5 nhánh canonical gốc nếu product chưa có taxonomy nào."""
    exists = db.scalars(
        select(Taxonomy.id).where(Taxonomy.product_id == product_id).limit(1)
    ).first()
    if exists is not None:
        return
    for en_name, vi_name in DEFAULT_ROOTS:
        db.add(
            Taxonomy(
                product_id=product_id,
                name=en_name,
                name_vi=vi_name,
                kind="canonical",
                status="active",
            )
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
# Manual CRUD (owner 2026-10-23): human tự tay xây/sửa taxonomy trên Active
# Taxonomy — cùng ràng buộc closed-set với apply_proposal: slug tự sinh theo
# plan 31 (bất biến), name canonical/active unique case-insensitive.
# ---------------------------------------------------------------------------

class TaxonomyValidationError(ValueError):
    """Input CRUD sai (parent lạ, tên rỗng…) — route quy 422."""


class TaxonomyConflictError(ValueError):
    """Trùng name hoặc xóa node còn con — route quy 409."""


def _active_node_by_slug(
    db: Session, product_id: uuid.UUID, slug: str
) -> Taxonomy | None:
    return db.scalar(
        select(Taxonomy).where(
            Taxonomy.product_id == product_id,
            Taxonomy.slug == slug,
            Taxonomy.status == "active",
            Taxonomy.kind == "canonical",
        )
    )


def _bump_version(db: Session, product: Product) -> int:
    """Re-fetch trong session hiện tại: `product` có thể DETACHED (fixture) —
    mutation trên detached không bao giờ commit (xem apply_proposal)."""
    product_row = db.get(Product, product.id)
    assert product_row is not None
    product_row.taxonomy_version = (product_row.taxonomy_version or 1) + 1
    return product_row.taxonomy_version


def create_manual_node(
    db: Session,
    product: Product,
    *,
    name: str,
    parent_slug: str | None = None,
    description: str | None = None,
    name_vi: str | None = None,
) -> Taxonomy:
    """Tạo node canonical/active mới trên taxonomy hiện có + bump version.

    Slug sinh theo plan 31 (root = slugify(name), con = `cha.con`), tự thêm
    hậu tố _2/_3 khi trùng. `name` = tiếng Anh canonical; `name_vi` hiển thị
    tiếng Việt (bỏ trống → fallback `name`). Commit do hàm này tự quản (khớp
    apply_proposal)."""
    ensure_slugs(db, product.id)
    name_clean = name.strip()
    if not name_clean:
        raise TaxonomyValidationError("Tên chủ đề không được rỗng.")
    if len(name_clean) > 100:
        raise TaxonomyValidationError("Tên chủ đề tối đa 100 ký tự.")
    name_vi_clean = name_vi.strip() if name_vi else None
    if name_vi_clean and len(name_vi_clean) > 100:
        raise TaxonomyValidationError("Tên hiển thị tối đa 100 ký tự.")

    parent: Taxonomy | None = None
    if parent_slug:
        parent = _active_node_by_slug(db, product.id, parent_slug)
        if parent is None:
            raise TaxonomyValidationError(
                f"parent slug '{parent_slug}' không tồn tại trong taxonomy active."
            )

    active_names = db.scalars(
        select(Taxonomy.name).where(
            Taxonomy.product_id == product.id, Taxonomy.status == "active"
        )
    ).all()
    if any(n.casefold() == name_clean.casefold() for n in active_names):
        raise TaxonomyConflictError(
            f"Đã có chủ đề active tên '{name_clean}' (so sánh bỏ qua hoa/thường)."
        )

    all_rows = db.scalars(
        select(Taxonomy).where(Taxonomy.product_id == product.id)
    ).all()
    slug_taken = {r.slug for r in all_rows if r.slug}
    base = slugify(name_clean)
    if parent is not None and parent.slug:
        base = f"{parent.slug}.{base}"
    slug, i = base, 2
    while slug in slug_taken:
        slug = f"{base}_{i}"
        i += 1

    node = Taxonomy(
        id=uuid.uuid4(),
        product_id=product.id,
        parent_id=parent.id if parent is not None else None,
        name=name_clean,
        name_vi=name_vi_clean or name_clean,
        slug=slug,
        description=(description or None),
        kind="canonical",
        status="active",
    )
    db.add(node)
    _bump_version(db, product)
    db.commit()
    db.refresh(node)
    return node


def update_manual_node(
    db: Session,
    product: Product,
    *,
    slug: str,
    name: str | None = None,
    description: str | None = None,
    name_vi: str | None = None,
) -> Taxonomy | None:
    """Đổi tên canonical / tên hiển thị tiếng Việt / mô tả node active. Slug
    BẤT BIẾN (plan 31 — dataset cũ không vỡ); KHÔNG bump version (chỉ đổi
    hiển thị, không đổi tập nhãn). `description=None` = xóa mô tả;
    `name_vi=None` = GIỮ NGUYÊN nhãn hiển thị (khác semantics xóa của
    description — nhãn hiển thị không bao giờ được trống). Trả None khi slug
    không tồn tại (→ 404)."""
    node = _active_node_by_slug(db, product.id, slug)
    if node is None:
        return None
    if name is not None:
        name_clean = name.strip()
        if not name_clean:
            raise TaxonomyValidationError("Tên chủ đề không được rỗng.")
        if len(name_clean) > 100:
            raise TaxonomyValidationError("Tên chủ đề tối đa 100 ký tự.")
        if name_clean.casefold() != node.name.casefold():
            siblings = db.scalars(
                select(Taxonomy).where(
                    Taxonomy.product_id == product.id, Taxonomy.status == "active"
                )
            ).all()
            if any(
                r.id != node.id and r.name.casefold() == name_clean.casefold()
                for r in siblings
            ):
                raise TaxonomyConflictError(
                    f"Đã có chủ đề active tên '{name_clean}'."
                )
        node.name = name_clean
    if name_vi is not None:
        name_vi_clean = name_vi.strip()
        if not name_vi_clean:
            raise TaxonomyValidationError("Tên hiển thị không được rỗng.")
        if len(name_vi_clean) > 100:
            raise TaxonomyValidationError("Tên hiển thị tối đa 100 ký tự.")
        node.name_vi = name_vi_clean
    node.description = description
    db.commit()
    db.refresh(node)
    return node


def delete_manual_node(db: Session, product: Product, *, slug: str) -> Taxonomy | None:
    """Xóa node canonical/active (KHÔNG đụng dữ liệu cũ: `ai_analysis.topics`
    giữ nguyên slug — FE hiển thị fallback). Node còn con (mọi status) →
    conflict. Bump version (tập nhãn đóng đổi). Trả None khi không có slug
    (→ 404); trả node đã xóa (instance giữ attrs sau delete) để route log."""
    node = _active_node_by_slug(db, product.id, slug)
    if node is None:
        return None
    child_count = db.scalar(
        select(func.count()).select_from(Taxonomy).where(Taxonomy.parent_id == node.id)
    )
    if int(child_count or 0) > 0:
        raise TaxonomyConflictError(
            f"Chủ đề '{node.name}' còn chủ đề con — xóa/dời con trước khi xóa."
        )
    db.delete(node)
    _bump_version(db, product)
    db.commit()
    return node


# ---------------------------------------------------------------------------
# GPT taxonomy proposal (plan 31 — spec Listen §2): GPT discovers, human applies
# ---------------------------------------------------------------------------

PROMPT_VERSION_TAXONOMY = "v5"

# v4→v5 (2026-10-24): (1) sampling không còn "N feedback mới nhất" (bias theo
# đợt sự cố gần đây) — `_stratified_samples` gộp trùng lặp, chia corpus thành
# bucket thời gian đều, round-robin mỗi bucket; prompt nhận `corpus_stats`
# (tổng thật, khoảng thời gian, nguồn, số trùng gộp) + sample kèm
# occurred_at/source để model KHÔNG suy tần suất từ mẫu. (2) Chạy tốt khi
# user KHÔNG đưa context: suy luận loại sản phẩm từ product + sample. (3) Quy
# tắc nhất quán thuật ngữ (Title Case, từ điển thuật ngữ chuẩn ngành, không
# pha VI trong name EN). Nguyên tắc PHÂN CÔNG TRỤC + 2 lớp name/name_vi của
# v4 giữ nguyên.
_GENERATE_SYSTEM = """Bạn là chuyên gia thiết kế taxonomy phân loại phản hồi người dùng (VoC) về sản phẩm số có tính năng AI — \
vai trò của bạn là người soạn codebook nghiên cứu UX. \
Văn phong làm việc: tiếng Việt, trộn thuật ngữ kỹ thuật tiếng Anh là bình thường.

Nguyên tắc số 1 — PHÂN CÔNG TRỤC: taxonomy chỉ trả lời MỘT câu hỏi: "feedback nói VỀ CÁI GÌ?" \
(chủ đề / mảng sản phẩm). Các trục khác đã có trường riêng của pipeline, KHÔNG được nhét vào tên topic:
- Tốt/xấu, khen/chê → sentiment. Tên topic KHÔNG chứa "tốt", "tệ", "hay", "kém", "good", "bad".
- Bug / feature request / câu hỏi / khen → intent. Tên topic KHÔNG cần chữ "lỗi", "error", "yêu cầu thêm".
- Mức độ / trạng thái sự cố ("chậm", "quá nhiều", "hay giật", "mất kết nối", "slow", "broken") → severity. \
Tên topic KHÔNG chứa từ chỉ mức độ hay trạng thái.
Ví dụ chuyển hoá: "Sync note-taking chậm" → topic "Note Sync"; "Quá nhiều quảng cáo" → "Advertising"; \
"Chế độ offline cho voice" → "Voice Mode".

INPUT (payload user):
- `product`: tên + mô tả sản phẩm. `context` (product_type/use_case/persona) CÓ THỂ TRỐNG — khi đó tự suy \
loại sản phẩm & người dùng từ `product` + `sample_feedback`; KHÔNG hỏi lại, KHÔNG từ chối, KHÔNG bịa chi tiết \
không có bằng chứng (chỉ dùng product name/description và nội dung feedback).
- `corpus_stats`: bối cảnh corpus THẬT (tổng feedback, khoảng thời gian, phân bố nguồn, số bản trùng đã gộp). \
Dùng để kiểm tra độ phủ, KHÔNG dùng để suy tần suất chủ đề.
- `sample_feedback`: các feedback ĐÃ ẨN DANH, được CHỌN PHÂN TẦNG đều theo thời gian (round-robin các bucket) \
nên một đợt sự cố gần đây KHÔNG chiếm ưu thế trong mẫu. Mỗi mục có `occurred_at` + `source` + `text`. \
Nhiều feedback nói CHUNG một sự cố (dù rải across thời gian) vẫn là MỘT chủ đề — tần suất thật nằm ở \
intent/severity, không phải việc tạo nhiều topic gần giống nhau.
- `existing_taxonomy`: các topic ĐANG CÓ (name + name_vi + description) — ưu tiên tái dùng; `parent` có thể là \
một name trong đó để gắn khía cạnh mới vào nhánh hiện có.

Nhiệm vụ: từ sample + corpus_stats + existing_taxonomy, đề xuất topic hierarchy 2 cấp (gốc → con) \
là BỘ NHÃN ĐÓNG cho các run phân loại feedback TƯƠNG LAI — bộ phân loại chỉ thấy TÊN topic, nên topic \
phải tự giải thích được và xếp được cả feedback chưa tồn tại.

Một topic đạt chuẩn:
- name: danh từ / cụm danh từ TIẾNG ANH ≤ 4 từ chỉ MẢNG hoặc TÍNH NĂNG của sản phẩm — viết Title Case \
("Note Sync", KHÔNG "note sync"); dùng thuật ngữ chuẩn ngành như một sản phẩm chuyên nghiệp dùng: \
Account Management, Onboarding, Notifications, Data Sync, Performance, Billing & Payments, Privacy & Security, \
AI Output Quality; KHÔNG trộn chữ tiếng Việt vào `name`; KHÔNG phải câu hay mô tả vấn đề của một tính năng \
cụ thể; KHÔNG chép nguyên câu của user; KHÔNG chứa động từ/trạng thái. `name` là nhãn canonical dùng cho mọi \
run phân loại — LUÔN tiếng Anh bất kể ngôn ngữ của sample feedback.
- name_vi: BẮT BUỘC — cụm danh từ TIẾNG VIỆT ≤ 4 từ tương ứng 1:1 với `name`; KHÔNG dịch word-by-word khi \
cộng đồng VN dùng nguyên thuật ngữ (giữ "Sync", "UI/UX", "Onboarding", "Prompt" như bình thường); \
vd "Note Sync" → "Đồng bộ ghi chú", "Billing & Payments" → "Thanh toán", "AI Output Quality" → "Chất lượng đầu ra AI".
- description BẮT BUỘC (1–2 câu, tiếng Việt): tiêu chí cái gì THUỘC và cái gì KHÔNG THUỘC topic, \
kèm vài từ khoá đặc trưng (tiếng Việt + tiếng Anh).

Cấu trúc & độ phủ:
- 3–6 topic GỐC là các mảng lớn của sản phẩm/dịch vụ; mỗi gốc 0–5 topic CON là tính năng/khía cạnh, \
chỉ thêm khi sample có đủ bằng chứng.
- MECE: topic KHÔNG chồng lấn (một feedback xếp đúng 1 topic chính); gộp tất cả phủ ≥ 90% sample. \
Chủ đề chỉ có 1–2 sample ủng hộ → KHÔNG tạo topic riêng, gộp vào topic rộng phù hợp.
- TRƯỚC KHI TRẢ JSON: rà checklist chiều phi chức năng trên TOÀN BỘ sample (mỗi mục — có bằng chứng \
trong sample không? chưa chắc = bỏ, KHÔNG bịa): hiệu năng/tốc độ, ổn định/crash, đồng bộ/dữ liệu, \
tài khoản/đăng nhập, giá/gói/thanh toán, quảng cáo/monetization, onboarding/kích hoạt, quyền riêng \
tư/bảo mật, UI/UX, chất lượng đầu ra AI (hallucination/sai/không hữu ích), hỗ trợ khách hàng.
- KHÔNG tạo topic "Khác/Other" (hệ thống có sẵn), KHÔNG tạo topic về cảm xúc/sentiment/mức độ.
- `parent` phải là `name` CHÍNH XÁC (tiếng Anh) của một topic khác trong danh sách hoặc trong \
existing_taxonomy; None cho topic gốc.

Ví dụ HÌNH THỨC đúng (app GIAO ĐỒ ĂN — chỉ minh hoạ cấu trúc, KHÔNG copy nội dung):
- Gốc "Delivery" (name_vi "Giao hàng") → con "Delivery Time" ("Thời gian giao"), "Delivery Fee" ("Phí giao hàng")
- Gốc "Orders & Payment" ("Đơn & Thanh toán") → con "Order Status" ("Trạng thái đơn"), "Refund" ("Hoàn tiền")
- Gốc "Food Quality" ("Chất lượng món") → con "Dish Search" ("Tìm kiếm món")
Feedback "shipper giao trễ 2 tiếng, quá kém" → topic "Delivery → Delivery Time" \
("trễ", "kém" nằm ở sentiment/severity, KHÔNG nằm trong tên topic).

Chỉ trả về JSON object khớp schema, không text thừa."""


def _stratified_samples(
    db: Session,
    product_id: uuid.UUID,
    *,
    limit: int,
    pool_cap: int = 1000,
) -> tuple[list[dict], dict]:
    """Chọn mẫu feedback phân tầng theo THỜI GIAN (prompt v5, 2026-10-24).

    Thay cho "N feedback mới nhất" (bias theo đợt sự cố gần đây — một wave bug
    chiếm hết slot mẫu): gộp trùng lặp văn bản, chia corpus thành bucket thời
    gian đều, round-robin mỗi bucket oldest→newest → mẫu phủ TOÀN BỘ khoảng
    thời gian. Trả (samples, corpus_stats) — stats vào prompt để model biết
    bối cảnh corpus thật (tổng/khoảng thời gian/nguồn/số trùng gộp) thay vì
    suy tần suất từ mẫu. Deterministic, KHÔNG tốn LLM. Dataset ≤ 1500 rows
    (AGENTS.md) nên pool_cap 1000 luôn phủ toàn corpus thực tế.

    ⚠️ PII boundary: chỉ cột `feedback_text` (đã qua presidio khi ingest) được
    đưa ra — `raw_content` không bao giờ.
    """
    rows = db.execute(
        select(
            Feedback.occurred_at,
            Feedback.source,
            Feedback.feedback_text,
        )
        .where(
            Feedback.product_id == product_id,
            Feedback.feedback_text.is_not(None),
        )
        .order_by(Feedback.occurred_at.desc(), Feedback.id.desc())
        .limit(pool_cap)
    ).all()

    pool_size = len(rows)
    # Gộp trùng lặp văn bản (giữ bản MỚI NHẤT — rows đã order desc).
    seen: set[str] = set()
    unique: list = []
    duplicates_merged = 0
    for row in rows:
        key = " ".join((row.feedback_text or "").split()).casefold()
        if not key:
            continue
        if key in seen:
            duplicates_merged += 1
            continue
        seen.add(key)
        unique.append(row)

    if not unique:
        return [], {
            "total_feedback_in_pool": pool_size,
            "unique_texts": 0,
            "duplicates_merged": duplicates_merged,
        }

    unique_asc = list(reversed(unique))  # oldest → newest
    t_min, t_max = unique_asc[0].occurred_at, unique_asc[-1].occurred_at
    n_buckets = max(1, min(limit, 10, len(unique_asc)))
    span = (t_max - t_min).total_seconds()

    buckets: list[list] = [[] for _ in range(n_buckets)]
    for row in unique_asc:
        if span <= 0:
            idx = 0
        else:
            idx = min(
                n_buckets - 1,
                int((row.occurred_at - t_min).total_seconds() / (span / n_buckets)),
            )
        buckets[idx].append(row)

    # Round-robin mỗi bucket (oldest trước) cho đến khi đủ limit.
    samples: list[dict] = []
    cursors = [0] * n_buckets
    while len(samples) < limit:
        took = False
        for b in range(n_buckets):
            if cursors[b] >= len(buckets[b]):
                continue
            row = buckets[b][cursors[b]]
            cursors[b] += 1
            samples.append(
                {
                    "occurred_at": row.occurred_at.date().isoformat(),
                    "source": row.source,
                    "text": row.feedback_text,
                }
            )
            took = True
            if len(samples) >= limit:
                break
        if not took:
            break  # cạn pool trước limit

    sources: dict[str, int] = {}
    for row in unique_asc:
        sources[row.source] = sources.get(row.source, 0) + 1
    stats = {
        "total_feedback_in_pool": pool_size,
        "unique_texts": len(unique_asc),
        "duplicates_merged": duplicates_merged,
        "date_range": {
            "from": t_min.date().isoformat(),
            "to": t_max.date().isoformat(),
        },
        "sources": dict(sorted(sources.items(), key=lambda kv: -kv[1])),
        "time_buckets_stratified": n_buckets,
        "sampled": len(samples),
    }
    return samples, stats


def generate_proposal(
    db: Session,
    product: Product,
    *,
    sample_size: int = 30,
    context: dict | None = None,
) -> tuple[TaxonomyProposalOut, int]:
    """GPT sinh proposal taxonomy từ sample feedback PHÂN TẦNG (ĐÃ SANITIZE).

    ⚠️ PII boundary: chỉ `feedback_text` (đã qua presidio) được đưa vào prompt —
    `raw_content` KHÔNG BAO GIỜ. Proposal STATELESS — không đụng DB tới khi
    human gọi apply. Product chưa có feedback nào → TaxonomyValidationError
    (route quy 422) — không đốt LLM call để bịa taxonomy không có bằng chứng.

    Trả (proposal, sample_count)."""
    samples, stats = _stratified_samples(db, product.id, limit=sample_size)
    if not samples:
        raise TaxonomyValidationError(
            "Chưa có phản hồi nào đã ẩn danh để sinh taxonomy — nhập phản hồi trước rồi mới generate."
        )
    existing = get_active_taxonomy_context(db, product.id)
    payload = {
        "product": {"name": product.name, "description": product.description},
        "context": context or {},
        "corpus_stats": stats,
        "existing_taxonomy": existing,
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
                # Không có name_vi (human bỏ trống khi sửa proposal) → fallback
                # chính `name` để nhãn hiển thị không bao giờ rỗng.
                name_vi=(topic.name_vi.strip() if topic.name_vi else None) or topic.name.strip(),
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


# ---------------------------------------------------------------------------
# GPT topic recommendation (plan 34 — spec Listen §4): taxonomy evolves từ
# pool uncategorized qua HUMAN apply — không per-record auto-emerging.
# ---------------------------------------------------------------------------

PROMPT_VERSION_RECOMMEND = "v4"

# v3→v4 (2026-10-23): hai lớp name (EN canonical + name_vi hiển thị) như
# _GENERATE_SYSTEM; nguyên tắc PHÂN CÔNG TRỤC + guard `sanitize_recommendations`
# của v3 giữ nguyên. Bằng chứng model nhỏ vẫn vi phạm prompt: đề xuất "Sync
# note-taking chậm" con của "Sync note-taking chậm".
_RECOMMEND_SYSTEM = """Bạn là chuyên gia thiết kế taxonomy phân loại phản hồi người dùng (VoC) về sản phẩm AI — \
người soạn codebook nghiên cứu UX. Văn phong làm việc: tiếng Việt, trộn thuật ngữ kỹ thuật tiếng Anh bình thường.

Nguyên tắc số 1 — PHÂN CÔNG TRỤC: topic chỉ ghi CHỦ ĐỀ ("feedback nói VỀ CÁI GÌ"). Sự cố và đánh giá \
("chậm", "quá nhiều", "lỗi", "tệ", "không được") là sentiment/severity/intent — đã có trường riêng, \
KHÔNG bao giờ nằm trong tên topic. Chuyển hoá bắt buộc trước khi đề xuất:
- "Sync note-taking chậm" → "Note Sync" (name_vi "Đồng bộ ghi chú")
- "Quá nhiều quảng cáo" → "Advertising" (name_vi "Quảng cáo")
- "Không đăng nhập được" → "Login & Account" (name_vi "Đăng nhập & Tài khoản")

Bối cảnh: `existing_taxonomy` là các topic đang có (name, name_vi, parent, description). Pool là các feedback \
CHƯA xếp được (uncategorized hoặc độ tin cậy chủ đề thấp). Nhiệm vụ: tìm khoảng trống THẬT SỰ của \
taxonomy và đề xuất TỐI ĐA 5 topic mới để các run phân loại TƯƠNG LAI tái sử dụng — không phải dán \
nhãn cho từng feedback cũ.

Quy tắc:
- GOM trước, đề xuất sau: gom các feedback cùng BẢN CHẤT thành một nhóm; chỉ đề xuất khi có ÍT NHẤT 2 \
feedback ủng hộ (noise đơn lẻ bỏ qua — nhánh Other sẽ xử lý chúng).
- `name`: cụm danh từ TIẾNG ANH ≤ 4 từ chỉ mảng/tính năng (thuật ngữ kỹ thuật viết chuẩn ngành: sync, \
prompt, chatbot) — nhãn canonical cho mọi run phân loại, LUÔN tiếng Anh bất kể ngôn ngữ feedback; KHÔNG \
chép nguyên câu user; KHÔNG chứa trạng thái vấn đề hay mức độ; KHÔNG chứa chữ "error"/"issue" khi nội \
dung chỉ là một tính năng đang gặp sự cố — sự cố thuộc intent/severity.
- `name_vi`: BẮT BUỘC — cụm danh từ TIẾNG VIỆT ≤ 4 từ khớp nghĩa `name` (giữ thuật ngữ kỹ thuật phổ \
biến như sync, prompt, chatbot); đây là nhãn hiển thị trên UI cho người dùng Việt.
- TUYỆT ĐỐI KHÔNG đề xuất topic trùng (kể cả khác hoa/thường/dấu) một `name` trong existing_taxonomy. \
Nếu nội dung đã có topic hiện có chỉ là TÊN CHƯA CHUẨN (đang là mô tả vấn đề như "Sync note-taking \
chậm") thì KHÔNG tạo topic mới/topic con cho nó — đề xuất topic mới chỉ khi là CHỦ ĐỀ khác biệt, \
việc chuẩn hoá tên là human ĐỔI TÊN topic hiện có (slug không đổi).
- `parent` (tùy chọn): `name` CHÍNH XÁC (tiếng Anh) của một topic HIỆN CÓ trong existing_taxonomy BAO \
QUÁT nhất chứa đề tài của topic mới; KHÔNG tự bịa parent; KHÔNG tạo topic con lặp lại phạm vi của \
chính cha (vd không được đề xuất "Advertising" con của "Advertising").
- `evidence_count` = số feedback trong pool ủng hộ topic này.
- `examples`: TỐI ĐA 3 trích NGUYÊN VĂN (ngắn) từ chính các feedback được cung cấp — không bịa.

Chỉ trả về JSON object khớp schema, không text thừa."""


def _norm_label(text: str) -> str:
    """Chuẩn hoá name để so khớp trùng: gọn whitespace + casefold (so sánh
    đề xuất LLM với taxonomy hiện có — chống trùng tên dạng 'Sync note-taking
    chậm' vs 'sync Note-Taking  Chậm')."""
    return " ".join(text.split()).casefold()


def sanitize_recommendations(
    recommendations: list,
    *,
    existing_names: list[str],
) -> list:
    """Guard CHƯƠNG TRÌNH chặn output LLM vi phạm quy tắc recommend trước khi
    tới hàng chờ duyệt của human (model nhỏ vẫn vi phạm prompt — bằng chứng
    2026-10-22): drop topic trùng taxonomy hiện có / trùng nhau; drop parent
    khi parent == name hoặc parent không nằm trong taxonomy hiện có.

    Hoạt động trên TopicRecommendation (không đụng DB, không đụng apply)."""
    existing = {_norm_label(n) for n in existing_names if n and n.strip()}
    out: list = []
    seen: set[str] = set()
    for rec in recommendations:
        name = " ".join((rec.name or "").split())
        if not name:
            continue
        key = _norm_label(name)
        if key in existing or key in seen:
            continue  # trùng topic hiện có / trùng đề xuất khác — không đưa lên GUI
        parent = " ".join(rec.parent.split()) if rec.parent else None
        if parent is not None:
            pkey = _norm_label(parent)
            if pkey == key or pkey not in existing:
                parent = None  # parent == chính nó, hoặc parent lạ → bỏ neo
        seen.add(key)
        name_vi = " ".join(rec.name_vi.split()) if rec.name_vi else None
        out.append(
            type(rec)(
                name=name,
                name_vi=name_vi or name,  # nhãn hiển thị không bao giờ trống
                parent=parent,
                evidence_count=max(1, rec.evidence_count),
                examples=rec.examples[:3],
            )
        )
    return out


def get_active_taxonomy_context(db: Session, product_id: uuid.UUID) -> list[dict]:
    """[{name, name_vi, slug, description, parent}] node ACTIVE — context cấu
    trúc cho prompt generate/recommend (model thấy hierarchy hiện có thay vì
    list tên phẳng, để gắn parent đúng nhánh và không trùng; name_vi để topic
    mới đề xuất đồng bộ bộ nhãn hiển thị tiếng Việt)."""
    rows = list(
        db.scalars(
            select(Taxonomy).where(
                Taxonomy.product_id == product_id, Taxonomy.status == "active"
            )
        ).all()
    )
    by_id = {r.id: r for r in rows}
    return [
        {
            "name": r.name,
            "name_vi": r.name_vi,
            "slug": r.slug,
            "description": r.description,
            "parent": by_id[r.parent_id].name
            if r.parent_id is not None and r.parent_id in by_id
            else None,
        }
        for r in rows
    ]


def find_unclassified_pool(
    db: Session, product_id: uuid.UUID, limit: int = 100
) -> list[Feedback]:
    """Feedback uncategorized HOẶC topic_confidence dưới floor — pool đề xuất."""
    from sqlalchemy import Float, and_, cast, or_

    floor = get_settings().ENRICH_TOPIC_CONFIDENCE_FLOOR
    return list(
        db.scalars(
            select(Feedback)
            .where(
                Feedback.product_id == product_id,
                Feedback.ai_analysis.is_not(None),
                or_(
                    Feedback.ai_analysis["uncategorized"].astext == "true",
                    and_(
                        Feedback.ai_analysis["topic_confidence"].isnot(None),
                        cast(
                            Feedback.ai_analysis["topic_confidence"].astext, Float
                        )
                        < floor,
                    ),
                ),
            )
            .order_by(Feedback.occurred_at.desc())
            .limit(limit)
        ).all()
    )


def recommend_topics(
    db: Session,
    product: Product,
    *,
    pool_limit: int = 100,
) -> tuple[TopicRecommendationOut, int]:
    """GPT đọc pool uncategorized → đề xuất topic mới — STATELESS, human apply.

    Trả (recommendations, pool_count). PII boundary: chỉ `feedback_text` đã
    sanitize được gửi vào prompt."""
    pool = find_unclassified_pool(db, product.id, limit=pool_limit)
    if not pool:
        return TopicRecommendationOut(recommendations=[]), 0
    existing = get_active_taxonomy_context(db, product.id)
    existing_names = [node["name"] for node in existing]
    payload = {
        "product": {"name": product.name},
        "existing_taxonomy": existing,
        "unclassified_feedback": [
            {"id": str(fb.id), "text": fb.feedback_text or "", "topic_confidence": (fb.ai_analysis or {}).get("topic_confidence")}
            for fb in pool
        ],
    }
    result = chat_structured(
        _RECOMMEND_SYSTEM,
        json.dumps(payload, ensure_ascii=False),
        TopicRecommendationOut,
        call_type=LlmCallType.topic_recommend,
        prompt_version=PROMPT_VERSION_RECOMMEND,
    )
    result.recommendations = sanitize_recommendations(
        result.recommendations, existing_names=existing_names
    )
    return result, len(pool)
