"""Integration test Analytics Engine — plan 24 (VoC OS §29–37).

⚠️ Marker `integration` — DB Supabase thật. KHÔNG LLM; semantic_search monkeypatch
embed_one (query embedding fake) — tool phải kNN đúng theo vector tay.

Đủ 8 tool + query compiler (field lạ bị từ chối, coverage đi kèm, cap ≤30).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.feedback import Feedback
from app.models.product import Product
from app.models.product_schema import ProductSchema
from app.services.embedder import store_embedding
from app.services.schema_registry import create_active_version

pytestmark = pytest.mark.integration

_DIM = 1536
_PRODUCT_NAME = "analytics-test-product"


def _unit_vec(idx: int) -> list[float]:
    raw = [0.0] * _DIM
    raw[idx] = 1.0
    return raw


@pytest.fixture()
def seeded():
    """Product DEDICATED (tránh nhiễm data suite khác dùng chung test_product) +
    schema active (2 field) + 6 feedback có embedding tay + data JSONB."""
    with SessionLocal() as db:
        product = db.scalars(
            select(Product).where(Product.name == _PRODUCT_NAME)
        ).first()
        if product is None:
            product = Product(name=_PRODUCT_NAME, description="analytics suite fixture")
            db.add(product)
            db.commit()
            db.refresh(product)
        # dọn rác lần trước
        db.query(Feedback).filter(Feedback.product_id == product.id).delete(
            synchronize_session=False
        )
        db.query(ProductSchema).filter(
            ProductSchema.product_id == product.id
        ).delete(synchronize_session=False)
        db.commit()
        create_active_version(
            db,
            product.id,
            {"fields": [
                {"key": "app_version", "label": "App Version", "type": "category"},
                {"key": "customer_plan", "label": "Plan", "type": "category"},
            ]},
        )
        now = datetime.now(timezone.utc)
        for i in range(6):
            fb = Feedback(
                product_id=product.id,
                source="web" if i % 2 == 0 else "mobile",
                source_record_id=f"analytics-{i}",
                occurred_at=now - timedelta(days=i),
                raw_content=f"noi dung {i} (khong PII)",
                feedback_text=f"feedback number {i}",
                data={
                    "app_version": "2.17" if i < 4 else "2.16",
                    "customer_plan": "enterprise" if i < 3 else "free",
                },
                ai_analysis={
                    "topics": ["Search"] if i < 4 else ["Account"],
                    "severity": "high" if i < 2 else "low",
                    "sentiment": "negative",
                    "confidence": 0.9,
                },
            )
            db.add(fb)
            db.flush()
            store_embedding(db, fb, _unit_vec(0 if i < 4 else 1))
        db.commit()
    yield product
    with SessionLocal() as db:
        db.query(Feedback).filter(Feedback.product_id == product.id).delete(
            synchronize_session=False
        )
        db.query(ProductSchema).filter(
            ProductSchema.product_id == product.id
        ).delete(synchronize_session=False)
        db.commit()


def _call(tool: str, params: dict, seeded) -> dict:
    from app.analytics.tools import TOOLS

    with SessionLocal() as db:
        return TOOLS[tool](db, seeded.id, params)


def test_get_schema_lists_dimensions_with_coverage(seeded) -> None:
    out = _call("get_schema", {}, seeded)
    keys = {d["field"] for d in out["dimensions"]}
    assert keys == {"app_version", "customer_plan"}
    cov = {d["field"]: d["coverage"] for d in out["dimensions"]}
    assert cov["app_version"] == pytest.approx(1.0)


def test_profile_field_top_values(seeded) -> None:
    out = _call("profile_field", {"field": "app_version"}, seeded)
    assert out["coverage"] == pytest.approx(1.0)
    assert out["distinct"] == 2
    assert out["top_values"][0] == ["2.17", 4]


def test_unknown_field_rejected(seeded) -> None:
    from app.analytics.query_compiler import UnknownFieldError

    with pytest.raises(UnknownFieldError):
        _call("profile_field", {"field": "made_up_field"}, seeded)
    with pytest.raises(UnknownFieldError):
        _call("aggregate_feedback", {"group_by": "made_up_field"}, seeded)


def test_aggregate_group_by_with_topic_filter(seeded) -> None:
    out = _call(
        "aggregate_feedback",
        {"filters": {"topic": "Search"}, "group_by": "customer_plan", "metric": "count"},
        seeded,
    )
    assert out["coverage"] == pytest.approx(1.0)
    rows = {r["value"]: r["count"] for r in out["rows"]}
    assert rows == {"enterprise": 3, "free": 1}


def test_compare_periods_change_pct(seeded) -> None:
    out = _call(
        "compare_periods",
        {"filters": {"topic": "Search"}, "current": "last_7_days", "previous": "previous_7_days"},
        seeded,
    )
    assert out["current"] == 4 and out["previous"] == 0
    assert out["change_pct"] == 999.0  # previous=0 + current>0 → trần


def test_segment_feedback_coverage_and_share(seeded) -> None:
    out = _call(
        "segment_feedback",
        {"filters": {"topic": "Search"}, "dimensions": ["app_version", "customer_plan"]},
        seeded,
    )
    seg = out["segments"]
    assert seg["app_version"] == {"coverage": 1.0, "top": "2.17", "share": 1.0}
    assert seg["customer_plan"]["top"] == "enterprise"
    assert seg["customer_plan"]["share"] == pytest.approx(0.75)


def test_semantic_search_ranks_by_vector(seeded, monkeypatch) -> None:
    from app.analytics import tools as tools_mod

    monkeypatch.setattr(tools_mod, "embed_one", lambda text: _unit_vec(0))
    out = _call("semantic_search", {"query": "anything", "k": 3}, seeded)
    assert len(out["results"]) == 3
    assert all(r["score"] > 0.999 for r in out["results"])  # cùng e0
    assert all("feedback number" in r["snippet"] for r in out["results"])


def test_representative_feedback_interleaves_sources_and_dedups(seeded) -> None:
    out = _call("representative_feedback", {"filters": {"topic": "Search"}, "n": 4}, seeded)
    sources = [s["source"] for s in out["samples"]]
    # 6 row Search: 3 web + 3 mobile, xen kẽ → không bao giờ 2 web liên tiếp đầu
    assert len(sources) == 4
    assert sources[0] != sources[1]
    assert len({s["text"] for s in out["samples"]}) == 4  # dedup text


def test_inspect_cluster_metrics(seeded) -> None:
    from app.models.cluster import Cluster

    with SessionLocal() as db:
        cluster = Cluster(
            id=uuid.uuid4(), name="Cụm Search", summary="-", feedback_count=2,
            first_seen=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
            current_count=2, previous_count=0, growth_ratio=9.99,
            is_emerging=True, is_spike=False, suggested_priority=0.6,
        )
        db.add(cluster)
        db.flush()
        rows = db.scalars(
            select(Feedback)
            .where(Feedback.product_id == seeded.id)
            .order_by(Feedback.occurred_at.desc())  # 2 row mới nhất = severity high
            .limit(2)
        ).all()
        for r in rows:
            r.cluster_id = cluster.id
        db.commit()
        cluster_id = cluster.id
    try:
        out = _call("inspect_cluster", {"cluster_id": str(cluster_id)}, seeded)
        assert out["live_member_count"] == 2
        assert out["is_emerging"] is True
        assert set(out["severity_dist"]) == {"high"}
    finally:
        with SessionLocal() as db:
            # gỡ membership TRƯỚC khi xoá cluster (FK feedback.cluster_id)
            db.query(Feedback).filter(Feedback.cluster_id == cluster_id).update(
                {"cluster_id": None}, synchronize_session=False
            )
            cluster = db.get(Cluster, cluster_id)
            if cluster is not None:
                db.delete(cluster)
            db.commit()
