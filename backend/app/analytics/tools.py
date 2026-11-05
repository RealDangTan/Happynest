"""Analytics Engine — 9 MVP tools cho UNDERSTAND agent (VoC OS §29–37).

Chỉ ĐỘC — tool thuần SQL/pgvector (trừ semantic_search sinh query embedding
qua embedder). Mỗi kết quả aggregate ĐI KÈM coverage của dimension được dùng
(§19). Chặn trần: MAX_RAW_FEEDBACK_PER_TOOL=30 row text/tool (§40).

Tool thứ 9 `search_similar_cases` cần bảng insights (plan 25 tạo) → đăng ký ở
phase 25; tại đây 8 tool (ghi chú trong docs/plans/24-analytics-engine.md).

KHÔNG expose HTTP — registry nội bộ cho agent (plan 25 dùng ToolSpec pattern).
"""

import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field
from sqlalchemy import Float, case, cast, func, select
from sqlalchemy.orm import Session

from app.analytics.query_compiler import UnknownFieldError, base_query
from app.core.config import get_settings
from app.models.cluster import Cluster
from app.models.feedback import Feedback
from app.services import schema_registry
from app.services.coverage import field_coverage
from app.services.embedder import embed_one

# ------------------------------------------------------------------ inputs


class GetSchemaInput(BaseModel):
    pass


class ProfileFieldInput(BaseModel):
    field: str = Field(min_length=1, max_length=80)


class AggregateInput(BaseModel):
    filters: dict[str, str] = Field(default_factory=dict)
    group_by: str = Field(min_length=1, max_length=80)
    metric: str = Field(default="count", pattern="^(count|avg_confidence)$")


class ComparePeriodsInput(BaseModel):
    filters: dict[str, str] = Field(default_factory=dict)
    current: str = Field(pattern="^(last_7_days|last_30_days)$")
    previous: str = Field(pattern="^(previous_7_days|previous_30_days)$")


class SegmentInput(BaseModel):
    filters: dict[str, str] = Field(default_factory=dict)
    dimensions: list[str] = Field(min_length=1, max_length=5)


class SemanticSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    filters: dict[str, str] = Field(default_factory=dict)
    k: int = Field(default=8, ge=1, le=30)


class RepresentativeInput(BaseModel):
    filters: dict[str, str] = Field(default_factory=dict)
    n: int = Field(default=6, ge=1, le=30)


class InspectClusterInput(BaseModel):
    cluster_id: str = Field(pattern=r"^[0-9a-fA-F-]{36}$")


class SearchSimilarCasesInput(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    k: int = Field(default=3, ge=1, le=10)


# ------------------------------------------------------------------ helpers


def _load_schema(db: Session, product_id: uuid.UUID) -> dict[str, dict]:
    """{field_key: field_def} của active schema."""
    active = schema_registry.get_active_schema(db, product_id)
    return {f["key"]: f for f in schema_registry.schema_fields(active)}


def _require_field(db: Session, product_id: uuid.UUID, field: str) -> None:
    if field not in _load_schema(db, product_id):
        raise UnknownFieldError(
            f"Field '{field}' không có trong product schema — chỉ dùng field "
            "đã được Gate #1 phê duyệt."
        )


def _count_in_window(
    db: Session,
    product_id: uuid.UUID,
    filters: dict | None,
    start: datetime,
    end: datetime,
) -> int:
    stmt = (
        base_query(db, product_id, filters)
        .with_only_columns(func.count())
        .where(Feedback.occurred_at >= start, Feedback.occurred_at < end)
        .order_by(None)
    )
    return int(db.scalar(stmt) or 0)


# ------------------------------------------------------------------- tools


def get_schema(db: Session, product_id: uuid.UUID, inp: GetSchemaInput) -> dict:
    """VoC OS §31: dimensions + coverage."""
    cov = field_coverage(db, product_id)
    dimensions = [
        {
            "field": key,
            "type": fdef.get("type", "category"),
            "coverage": cov.get(key, 0.0),
        }
        for key, fdef in _load_schema(db, product_id).items()
    ]
    return {"dimensions": dimensions}


def profile_field(db: Session, product_id: uuid.UUID, inp: ProfileFieldInput) -> dict:
    """VoC OS §32: coverage, distinct, top_values ≤5 của 1 field."""
    _require_field(db, product_id, inp.field)
    cov = field_coverage(db, product_id).get(inp.field, 0.0)
    # Expression dựng MỘT LẦN rồi tái dùng — SELECT và GROUP BY phải là CÙNG
    # một object, nếu không bind param khác tên → PG GroupingError.
    col = Feedback.data[inp.field].astext
    rows = db.execute(
        select(col.label("val"), func.count().label("n"))
        .where(
            Feedback.product_id == product_id,
            col.isnot(None),
        )
        .group_by(col)
        .order_by(func.count().desc())
        .limit(5)
    ).all()
    distinct = db.scalar(
        select(func.count(func.distinct(col))).where(Feedback.product_id == product_id)
    )
    return {
        "field": inp.field,
        "coverage": cov,
        "distinct": int(distinct or 0),
        "top_values": [[r.val, int(r.n)] for r in rows],
    }


#: Chiều nhãn AI (enrichment `ai_analysis`) group được bên cạnh field schema —
#: whitelist cố định, LLM chỉ gửi TÊN chiều (§68). Owner duyệt 2026-11-05: trước
#: đó agent không trả lời được "X% phản hồi tiêu cực là lỗi độ chính xác".
AI_SCALAR_DIMENSIONS = ("sentiment", "severity", "intent", "ai_issue")
AI_DIMENSIONS = (*AI_SCALAR_DIMENSIONS, "topic", "source")


def _topics_array():
    return Feedback.ai_analysis["topics"]


def _dimension_expr(db: Session, product_id: uuid.UUID, key: str):
    """Biểu thức SQL cho 1 chiều scalar; `topic` (multi-label) xử lý riêng."""
    if key in AI_SCALAR_DIMENSIONS:
        return Feedback.ai_analysis[key].astext
    if key == "source":
        return Feedback.source
    _require_field(db, product_id, key)
    return Feedback.data[key].astext


def _ai_dimension_coverage(db: Session, product_id: uuid.UUID, key: str) -> float:
    """Tỉ lệ feedback của product có giá trị ở chiều AI (topic: mảng không rỗng)."""
    if key == "topic":
        # CASE: jsonb_array_length nổ trên scalar — chỉ đo khi đúng là mảng
        has_value = case(
            (func.jsonb_typeof(_topics_array()) == "array", func.jsonb_array_length(_topics_array())),
            else_=0,
        ) > 0
    else:
        has_value = _dimension_expr(db, product_id, key).is_not(None)
    total, with_value = db.execute(
        select(func.count(), func.count().filter(has_value))
        .where(Feedback.product_id == product_id)
    ).one()
    return round(int(with_value) / int(total), 4) if total else 0.0


def _coverage_for(db: Session, product_id: uuid.UUID, key: str) -> float:
    if key in AI_DIMENSIONS:
        return _ai_dimension_coverage(db, product_id, key)
    return field_coverage(db, product_id).get(key, 0.0)


def aggregate_feedback(db: Session, product_id: uuid.UUID, inp: AggregateInput) -> dict:
    """VoC OS §33: GROUP BY field schema HOẶC nhãn AI + metric; coverage đi kèm.

    `topic` là multi-label: 1 feedback nhiều topic được đếm ở mỗi topic
    (`multi_label=True` trong kết quả để agent không cộng dồn thành tổng)."""
    conf = cast(Feedback.ai_analysis["confidence"].astext, Float)
    multi = inp.group_by == "topic"
    if multi:
        sub = (
            base_query(db, product_id, inp.filters)
            .where(func.jsonb_typeof(_topics_array()) == "array")
            .with_only_columns(
                func.jsonb_array_elements_text(_topics_array()).label("val"),
                conf.label("conf"),
            )
            .order_by(None)
            .subquery()
        )
        columns = [sub.c.val.label("val"), func.count().label("n")]
        if inp.metric == "avg_confidence":
            columns.append(func.avg(sub.c.conf).label("avg_conf"))
        stmt = select(*columns).group_by(sub.c.val).order_by(func.count().desc())
    else:
        col = _dimension_expr(db, product_id, inp.group_by)  # một object duy nhất (xem profile_field)
        columns = [col.label("val"), func.count().label("n")]
        if inp.metric == "avg_confidence":
            columns.append(func.avg(conf).label("avg_conf"))
        stmt = (
            base_query(db, product_id, inp.filters)
            .with_only_columns(*columns)
            .group_by(col)
            .order_by(func.count().desc())
        )
    rows = db.execute(stmt).all()
    data = [
        {
            "value": r.val,
            "count": int(r.n),
            "avg_confidence": round(float(r.avg_conf), 4)
            if inp.metric == "avg_confidence" and r.avg_conf is not None
            else None,
        }
        for r in rows
    ]
    out = {
        "group_by": inp.group_by,
        "metric": inp.metric,
        "coverage": _coverage_for(db, product_id, inp.group_by),
        "rows": data[:20],
    }
    if multi:
        out["multi_label"] = True
    return out


def compare_periods(db: Session, product_id: uuid.UUID, inp: ComparePeriodsInput) -> dict:
    """VoC OS §34: count hiện tại vs kỳ trước + change_pct."""
    now = datetime.now(timezone.utc)
    days = 7 if inp.current.endswith("7_days") else 30
    cur_start = now - timedelta(days=days)
    prev_end = cur_start
    prev_start = prev_end - timedelta(days=days)
    current = _count_in_window(db, product_id, inp.filters, cur_start, now)
    previous = _count_in_window(db, product_id, inp.filters, prev_start, prev_end)
    change_pct = (
        round((current - previous) / previous * 100, 2)
        if previous
        else (999.0 if current else 0.0)
    )
    return {
        "current_window": inp.current,
        "previous_window": inp.previous,
        "current": current,
        "previous": previous,
        "change_pct": change_pct,
    }


def segment_feedback(db: Session, product_id: uuid.UUID, inp: SegmentInput) -> dict:
    """VoC OS §35: per-dimension {coverage, top, share} trong tập được filter."""

    def _top_share(field: str) -> dict:
        if field == "topic":
            # multi-label: coverage = row có ≥1 topic; share = row chứa top topic
            base = (
                base_query(db, product_id, inp.filters)
                .with_only_columns(Feedback.id, _topics_array().label("val"))
                .order_by(None)
            )
            rows = db.execute(base).all()
            lists = [r.val for r in rows if isinstance(r.val, list) and r.val]
            coverage = round(len(lists) / len(rows), 4) if rows else 0.0
            if not lists:
                return {"coverage": coverage, "top": None, "share": 0.0}
            counter: dict[str, int] = {}
            for topics in lists:
                for t in {str(x) for x in topics}:
                    counter[t] = counter.get(t, 0) + 1
            top, count = max(counter.items(), key=lambda kv: kv[1])
            return {"coverage": coverage, "top": top, "share": round(count / len(lists), 4),
                    "multi_label": True}
        expr = _dimension_expr(db, product_id, field)
        base = (
            base_query(db, product_id, inp.filters)
            .with_only_columns(Feedback.id, expr.label("val"))
            .order_by(None)
        )
        rows = db.execute(base).all()
        vals = [r.val for r in rows if r.val]
        coverage = round(len(vals) / len(rows), 4) if rows else 0.0
        if not vals:
            return {"coverage": coverage, "top": None, "share": 0.0}
        counter = {}
        for v in vals:
            counter[v] = counter.get(v, 0) + 1
        top, count = max(counter.items(), key=lambda kv: kv[1])
        return {"coverage": coverage, "top": top, "share": round(count / len(vals), 4)}

    return {"segments": {dim: _top_share(dim) for dim in inp.dimensions}}


def semantic_search(db: Session, product_id: uuid.UUID, inp: SemanticSearchInput) -> dict:
    """VoC OS §36: pgvector cosine kNN — CHỈ trả relevant records (≤30).

    Query embedding sinh bằng embedder (câu do agent tự viết, không chứa raw
    feedback); filter theo product + filters TRƯỚC khi ORDER BY distance
    (exact scan — dataset ≤1500, no ANN per locked decision).
    """
    k = min(inp.k, get_settings().MAX_RAW_FEEDBACK_PER_TOOL)
    vector = embed_one(inp.query)
    rows = db.execute(
        base_query(db, product_id, inp.filters)
        .with_only_columns(
            Feedback.id,
            Feedback.source,
            Feedback.feedback_text,
            (1 - Feedback.embedding.cosine_distance(vector)).label("score"),
        )
        .where(Feedback.embedding.is_not(None))
        .order_by(Feedback.embedding.cosine_distance(vector))
        .limit(k)
    ).all()
    return {
        "results": [
            {
                "id": str(r.id),
                "source": r.source,
                "snippet": (r.feedback_text or "")[:200],
                "score": round(float(r.score), 4),
            }
            for r in rows
        ]
    }


def representative_feedback(db: Session, product_id: uuid.UUID, inp: RepresentativeInput) -> dict:
    """VoC OS §37: mẫu đa dạng — xen kẽ source, dedup text, ≤ MAX_RAW."""

    n = min(inp.n, get_settings().MAX_RAW_FEEDBACK_PER_TOOL)
    rows = db.execute(
        base_query(db, product_id, inp.filters)
        .with_only_columns(Feedback.id, Feedback.source, Feedback.feedback_text)
        .order_by(Feedback.occurred_at.desc())
        .limit(n * 4)
    ).all()
    by_source: dict[str, list] = {}
    seen_text: set[str] = set()
    for r in rows:
        key = (r.feedback_text or "")[:80]
        if key in seen_text:
            continue
        seen_text.add(key)
        by_source.setdefault(r.source, []).append(r)
    picked: list = []
    while len(picked) < n and any(by_source.values()):
        for src in list(by_source):
            if by_source[src] and len(picked) < n:
                picked.append(by_source[src].pop(0))
    return {
        "samples": [
            {
                "feedback_id": str(r.id),
                "source": r.source,
                "text": (r.feedback_text or "")[:300],
            }
            for r in picked
        ]
    }


def inspect_cluster(db: Session, product_id: uuid.UUID, inp: InspectClusterInput) -> dict:
    """VoC OS §30: stored trend + live metrics của 1 cụm."""
    cluster = db.get(Cluster, uuid.UUID(inp.cluster_id))
    if cluster is None:
        raise LookupError(f"Cluster {inp.cluster_id} không tồn tại.")
    member_count = int(
        db.scalar(
            select(func.count())
            .select_from(Feedback)
            .where(Feedback.cluster_id == cluster.id, Feedback.product_id == product_id)
        )
        or 0
    )
    if not member_count:
        raise LookupError("Không có nhóm phản hồi này trong sản phẩm đang điều tra.")
    mixed_products = bool(db.scalar(select(
        select(Feedback.id).where(
            Feedback.cluster_id == cluster.id, Feedback.product_id != product_id,
        ).exists()
    )))
    sev_col = Feedback.ai_analysis["severity"].astext  # một object (xem profile_field)
    sev_rows = db.execute(
        select(sev_col.label("sev"), func.count().label("n"))
        .where(Feedback.cluster_id == cluster.id, Feedback.product_id == product_id)
        .group_by(sev_col)
    ).all()
    return {
        "cluster_id": str(cluster.id),
        "name": "Nhóm phản hồi trong sản phẩm" if mixed_products else cluster.name,
        "summary": "Chỉ đếm phản hồi thuộc sản phẩm đang điều tra; xu hướng toàn cụm không áp dụng." if mixed_products else cluster.summary,
        "feedback_count": member_count,
        "live_member_count": member_count,
        "growth_ratio": None if mixed_products else cluster.growth_ratio,
        "is_emerging": None if mixed_products else cluster.is_emerging,
        "is_spike": None if mixed_products else cluster.is_spike,
        "suggested_priority": None if mixed_products else cluster.suggested_priority,
        "severity_dist": {r.sev: int(r.n) for r in sev_rows if r.sev},
    }


def search_similar_cases(db: Session, product_id: uuid.UUID, inp: SearchSimilarCasesInput) -> dict:
    """VoC OS §30 tool 9: precedent retrieval — kNN trên insights.embedding
    (organizational memory; insights chỉ tồn tại sau Gate #2 approve/edit)."""
    from app.models.insight import Insight

    k = inp.k
    vector = embed_one(inp.query)
    rows = db.execute(
        select(
            Insight.id,
            Insight.title,
            Insight.finding,
            Insight.status,
            (1 - Insight.embedding.cosine_distance(vector)).label("score"),
        )
        .where(
            Insight.product_id == product_id,
            Insight.embedding.is_not(None),
            Insight.status.in_(["approved", "edited"]),
        )
        .order_by(Insight.embedding.cosine_distance(vector))
        .limit(k)
    ).all()
    return {
        "cases": [
            {
                "insight_id": str(r.id),
                "title": r.title,
                "finding": r.finding[:300],
                "status": r.status,
                "score": round(float(r.score), 4),
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------- registry


class ToolSpec:
    """Metadata + executor cho router agent (plan 25)."""

    def __init__(self, name: str, description: str, input_model: type, executor):
        self.name = name
        self.description = description
        self.input_model = input_model
        self.executor = executor

    def __call__(self, db: Session, product_id: uuid.UUID, params: dict) -> dict:
        parsed = self.input_model.model_validate(params)
        return self.executor(db, product_id, parsed)


TOOLS: dict[str, ToolSpec] = {
    spec.name: spec
    for spec in [
        ToolSpec("get_schema", "List product analytical dimensions with coverage", GetSchemaInput, get_schema),
        ToolSpec("profile_field", "Coverage, distinct count and top values of one field", ProfileFieldInput, profile_field),
        ToolSpec("aggregate_feedback", "Group-by counts (or avg confidence) over filtered feedback; group_by = a schema field key or an AI label dimension: sentiment, severity, intent, ai_issue, topic (multi-label slug), source", AggregateInput, aggregate_feedback),
        ToolSpec("compare_periods", "Count an issue in current vs previous window with change_pct", ComparePeriodsInput, compare_periods),
        ToolSpec("segment_feedback", "Coverage/top/share per dimension for a filtered issue set; dimensions = schema field keys and/or sentiment, severity, intent, ai_issue, topic, source", SegmentInput, segment_feedback),
        ToolSpec("semantic_search", "Cosine kNN over feedback embeddings, filtered and capped", SemanticSearchInput, semantic_search),
        ToolSpec("representative_feedback", "Diverse representative verbatims interleaved by source", RepresentativeInput, representative_feedback),
        ToolSpec("inspect_cluster", "Stored trend fields plus live member/severity metrics of one cluster", InspectClusterInput, inspect_cluster),
        ToolSpec("search_similar_cases", "Retrieve similar past insights (precedents) by semantic similarity", SearchSimilarCasesInput, search_similar_cases),
    ]
}
