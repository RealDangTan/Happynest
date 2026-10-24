"""Integration — manual taxonomy CRUD (owner 2026-10-23).

⚠️ Marker `integration` — DB Supabase thật, KHÔNG LLM. Seed taxonomy của
test_product dọn sạch sau test (giữ canonical gốc migration 0010).
Contract: POST/PATCH/DELETE /api/taxonomies/nodes* — slug bất biến (plan 31),
bump taxonomy_version khi tập nhãn đổi (create/delete), KHÔNG bump khi rename.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.product import Product
from app.models.taxonomy import Taxonomy
from app.models.user import User
from app.services import taxonomy_service
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration


def _login(client: TestClient, account: str = "primary") -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[account], "password": TEST_PASSWORDS[account]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def crud_env(test_product):
    """Sạch toàn bộ taxonomy của test_product trước/sau; trả product_id."""
    def _clean():
        with SessionLocal() as db:
            db.query(Taxonomy).filter(
                Taxonomy.product_id == test_product.id
            ).delete(synchronize_session=False)
            db.commit()

    _clean()
    yield {"product_id": str(test_product.id)}
    _clean()


def _version_of(product_id: str) -> int:
    with SessionLocal() as db:
        return int(
            db.scalar(select(Product.taxonomy_version).where(Product.id == uuid.UUID(product_id)))
            or 0
        )


def _node_by_slug(product_id: str, slug: str) -> Taxonomy | None:
    with SessionLocal() as db:
        return db.scalar(
            select(Taxonomy).where(
                Taxonomy.product_id == uuid.UUID(product_id), Taxonomy.slug == slug
            )
        )


def test_create_root_and_child_slugs_and_version_bump(client, crud_env) -> None:
    headers = _login(client)
    pid = crud_env["product_id"]
    before = _version_of(pid)

    root = client.post(
        "/api/taxonomies/nodes",
        json={
            "product_id": pid,
            "name": "Delivery",
            "name_vi": "Giao hàng",
            "description": "Vận chuyển đơn.",
        },
        headers=headers,
    )
    assert root.status_code == 201, root.text
    assert root.json()["slug"] == "delivery"
    assert root.json()["name"] == "Delivery"
    assert root.json()["name_vi"] == "Giao hàng"
    assert root.json()["status"] == "active"
    assert root.json()["kind"] == "canonical"

    child = client.post(
        "/api/taxonomies/nodes",
        json={
            "product_id": pid,
            "name": "Delivery Time",
            "name_vi": "Thời gian giao",
            "parent_slug": "delivery",
        },
        headers=headers,
    )
    assert child.status_code == 201, child.text
    assert child.json()["slug"] == "delivery.delivery_time"
    assert child.json()["parent_id"] == root.json()["id"]

    # name_vi bỏ trống → fallback chính name (không bao giờ rỗng)
    no_vi = client.post(
        "/api/taxonomies/nodes",
        json={"product_id": pid, "name": "Packaging"},
        headers=headers,
    )
    assert no_vi.status_code == 201, no_vi.text
    assert no_vi.json()["name_vi"] == "Packaging"

    assert _version_of(pid) == before + 3  # mỗi lần tạo bump 1

    # Đóng cho engine: get_taxonomy_labels thấy node mới (slug → name, name_vi)
    with SessionLocal() as session:
        labels = {
            slug: (name, name_vi)
            for slug, name, name_vi in taxonomy_service.get_taxonomy_labels(
                session, uuid.UUID(pid)
            )
        }
    assert labels["delivery"] == ("Delivery", "Giao hàng")
    assert labels["delivery.delivery_time"] == ("Delivery Time", "Thời gian giao")
    assert labels["packaging"] == ("Packaging", "Packaging")


def test_create_duplicate_name_conflict_409(client, crud_env) -> None:
    headers = _login(client)
    pid = crud_env["product_id"]
    first = client.post(
        "/api/taxonomies/nodes", json={"product_id": pid, "name": "Thanh toán"}, headers=headers
    )
    assert first.status_code == 201
    dup = client.post(
        "/api/taxonomies/nodes", json={"product_id": pid, "name": "thanh toán"}, headers=headers
    )
    assert dup.status_code == 409
    assert "Thanh toán" in dup.json()["detail"] or "thanh toán" in dup.json()["detail"]


def test_create_bad_parent_422(client, crud_env) -> None:
    resp = client.post(
        "/api/taxonomies/nodes",
        json={"product_id": crud_env["product_id"], "name": "X", "parent_slug": "khong_ton_tai"},
        headers=_login(client),
    )
    assert resp.status_code == 422


def test_rename_keeps_slug_and_clears_description(client, crud_env) -> None:
    headers = _login(client)
    pid = crud_env["product_id"]
    created = client.post(
        "/api/taxonomies/nodes",
        json={"product_id": pid, "name": "Ổn định", "description": "Crash, freeze."},
        headers=headers,
    )
    slug = created.json()["slug"]
    version_before = _version_of(pid)

    renamed = client.patch(
        f"/api/taxonomies/nodes/{slug}",
        json={"product_id": pid, "name": "Ổn định & Crash", "description": None},
        headers=headers,
    )
    assert renamed.status_code == 200, renamed.text
    body = renamed.json()
    assert body["name"] == "Ổn định & Crash"
    assert body["slug"] == slug  # plan 31: slug bất biến
    assert body["description"] is None
    assert _version_of(pid) == version_before  # rename KHÔNG bump

    # patch name_vi đơn lẻ: đổi nhãn hiển thị, GIỮ nguyên name canonical
    vi_only = client.patch(
        f"/api/taxonomies/nodes/{slug}",
        json={"product_id": pid, "name_vi": "Ổn định & sự cố"},
        headers=headers,
    )
    assert vi_only.status_code == 200, vi_only.text
    assert vi_only.json()["name"] == "Ổn định & Crash"
    assert vi_only.json()["name_vi"] == "Ổn định & sự cố"
    assert _version_of(pid) == version_before  # vẫn không bump

    missing = client.patch(
        "/api/taxonomies/nodes/khong_co",
        json={"product_id": pid, "name": "Y"},
        headers=headers,
    )
    assert missing.status_code == 404


def test_delete_leaf_conflict_on_parent_then_cleanup(client, crud_env) -> None:
    headers = _login(client)
    pid = crud_env["product_id"]
    root = client.post(
        "/api/taxonomies/nodes", json={"product_id": pid, "name": "Tài khoản"}, headers=headers
    ).json()
    child = client.post(
        "/api/taxonomies/nodes",
        json={"product_id": pid, "name": "OTP", "parent_slug": root["slug"]},
        headers=headers,
    ).json()

    blocked = client.delete(
        f"/api/taxonomies/nodes/{root['slug']}?product_id={pid}", headers=headers
    )
    assert blocked.status_code == 409

    removed = client.delete(
        f"/api/taxonomies/nodes/{child['slug']}?product_id={pid}", headers=headers
    )
    assert removed.status_code == 204
    assert _node_by_slug(pid, child["slug"]) is None

    removed_root = client.delete(
        f"/api/taxonomies/nodes/{root['slug']}?product_id={pid}", headers=headers
    )
    assert removed_root.status_code == 204

    missing = client.delete(
        f"/api/taxonomies/nodes/{root['slug']}?product_id={pid}", headers=headers
    )
    assert missing.status_code == 404


def test_crud_isolated_by_product_ownership(client, crud_env, seeded_users) -> None:
    """Product của account khác → 404 (isolation 2026-10-22), không lộ tồn tại."""
    headers = _login(client, "primary")
    with SessionLocal() as db:
        product = Product(
            name=f"crud-iso-{uuid.uuid4().hex[:8]}",
            owner_id=seeded_users["secondary"].id,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        foreign_pid = str(product.id)
    try:
        for method, url, body in (
            ("post", "/api/taxonomies/nodes", {"product_id": foreign_pid, "name": "X"}),
            ("patch", "/api/taxonomies/nodes/any", {"product_id": foreign_pid, "name": "Y"}),
        ):
            resp = getattr(client, method)(url, json=body, headers=headers)
            assert resp.status_code == 404, resp.text
        resp = client.delete(
            f"/api/taxonomies/nodes/any?product_id={foreign_pid}", headers=headers
        )
        assert resp.status_code == 404
    finally:
        with SessionLocal() as db:
            row = db.get(Product, uuid.UUID(foreign_pid))
            if row is not None:
                db.delete(row)
                db.commit()
