"""Real PostgreSQL regression: newly registered accounts share workspaces."""

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


def test_new_accounts_can_share_and_manage_workspace():
    suffix = uuid.uuid4().hex
    emails = [f"shared-{suffix}-{i}@example.test" for i in range(2)]
    product_name = f"shared-product-{suffix}"
    product_id = None
    try:
        # closing() closes HTTP clients without starting the application lifespan.
        with closing(TestClient(app)) as first, closing(TestClient(app)) as second:
            for client, email in zip((first, second), emails, strict=True):
                registered = client.post("/api/auth/register", json={
                    "email": email, "password": "shared-test-pass-123"})
                assert registered.status_code == 201, registered.text
                assert set(registered.json()) == {"id", "email"}
                assert client.post("/api/auth/token", data={
                    "username": email, "password": "shared-test-pass-123"}
                ).status_code == 200
            created = first.post("/api/products", json={"name": product_name})
            assert created.status_code == 201, created.text
            product_id = created.json()["id"]
            listed = second.get("/api/products")
            assert any(p["id"] == product_id for p in listed.json()["items"])
            assert second.get(f"/api/products/{product_id}/schema").status_code == 200
            updated = second.patch(f"/api/products/{product_id}", json={
                "description": "Updated by another account"})
            assert updated.status_code == 200, updated.text
            assert first.get(f"/api/products/{product_id}").json()[
                "description"] == "Updated by another account"
            # Names are unique in the shared workspace, irrespective of account.
            duplicate = second.post("/api/products", json={"name": product_name})
            assert duplicate.status_code == 409
            assert second.delete(f"/api/products/{product_id}").status_code == 200
            assert first.get(f"/api/products/{product_id}").status_code == 404
    finally:
        with SessionLocal() as db:
            if product_id:
                db.execute(delete(Product).where(Product.id == uuid.UUID(product_id)))
            db.execute(delete(User).where(User.email.in_(emails)))
            db.commit()
