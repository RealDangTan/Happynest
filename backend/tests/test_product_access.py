"""Real PostgreSQL regression: per-account workspace isolation (2026-10-22).

Account A tạo product → account B (đăng ký riêng) KHÔNG thấy ở list, không
đọc/sửa/xoá được (404), nhưng có thể tạo product CÙNG TÊN cho chính mình
(name unique per-owner). Thay thế test_shared_access.py của contract cũ.
"""

import uuid
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.product import Product
from app.models.user import User

pytestmark = pytest.mark.integration


def test_new_accounts_are_isolated_per_account():
    suffix = uuid.uuid4().hex
    emails = [f"isolated-{suffix}-{i}@example.test" for i in range(2)]
    product_name = f"isolated-product-{suffix}"
    product_id = None
    try:
        # closing() closes HTTP clients without starting the application lifespan.
        with closing(TestClient(app)) as first, closing(TestClient(app)) as second:
            for client, email in zip((first, second), emails, strict=True):
                registered = client.post("/api/auth/register", json={
                    "email": email, "password": "isolated-test-pass-123"})
                assert registered.status_code == 201, registered.text
                assert set(registered.json()) == {"id", "email"}
                assert client.post("/api/auth/token", data={
                    "username": email, "password": "isolated-test-pass-123"}
                ).status_code == 200

            # Account mới đăng ký bắt đầu với workspace TRỐNG.
            assert second.get("/api/products").json()["items"] == []

            created = first.post("/api/products", json={"name": product_name})
            assert created.status_code == 201, created.text
            product_id = created.json()["id"]

            # B không thấy product của A: list trống với B và 404 trực tiếp.
            assert second.get("/api/products").json()["items"] == []
            assert second.get(f"/api/products/{product_id}").status_code == 404
            assert second.get(f"/api/products/{product_id}/schema").status_code == 404
            assert second.patch(f"/api/products/{product_id}", json={
                "description": "Updated by another account"
            }).status_code == 404
            assert second.delete(f"/api/products/{product_id}").status_code == 404

            # Name unique PER-OWNER: B tạo được product cùng tên, A vẫn thấy
            # product của A nguyên vẹn.
            twin = second.post("/api/products", json={"name": product_name})
            assert twin.status_code == 201, twin.text
            assert twin.json()["id"] != product_id
            listed = first.get("/api/products").json()
            assert [p["id"] for p in listed["items"]] == [product_id]

            # A xoá product của chính mình thành công; B không xoá được của A.
            assert second.delete(f"/api/products/{twin.json()['id']}").status_code == 200
            assert first.delete(f"/api/products/{product_id}").status_code == 200
            assert first.get(f"/api/products/{product_id}").status_code == 404
    finally:
        with SessionLocal() as db:
            if product_id:
                db.execute(delete(Product).where(Product.id == uuid.UUID(product_id)))
            db.execute(delete(User).where(User.email.in_(emails)))
            db.commit()
