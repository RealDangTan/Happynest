"""Per-account workspace isolation (unit, sqlite) — decisions.md 2026-10-22.

Đảo contract của test_shared_access.py (đã xoá cùng commit): account B KHÔNG
thấy/sửa/xoá product của account A; name chỉ unique per-owner; identity layer
vẫn y như trước (401 khi chưa login, /me trả {id, email}).
"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.api.routes import auth, products
from app.core.security import create_access_token, decode_token
from app.models.product import Product
from app.models.user import User


@pytest.fixture()
def isolated_api():
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    User.__table__.create(engine)
    Product.__table__.create(engine)
    with Session(engine) as db:
        owner = User(email="owner@example.test", password_hash="x")
        db.add(owner)
        db.commit()
        db.refresh(owner)
        product = Product(
            owner_id=owner.id,
            name="Owner product",
            description="Created by the owner account",
        )
        db.add(product)
        db.commit()
        pid = str(product.id)
        app = FastAPI()
        app.include_router(auth.router)
        app.include_router(products.router)
        app.dependency_overrides[get_db] = lambda: db

        current = SimpleNamespace(id=uuid.uuid4(), email="other@example.test")
        app.dependency_overrides[get_current_user] = lambda: current
        with TestClient(app) as client:
            yield client, pid, app, current
    engine.dispose()


def test_other_account_list_is_empty(isolated_api):
    client, pid, *_ = isolated_api
    response = client.get("/api/products")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_other_account_cannot_read_update_or_delete(isolated_api):
    client, pid, *_ = isolated_api
    assert client.get(f"/api/products/{pid}").status_code == 404
    assert client.patch(
        f"/api/products/{pid}", json={"name": "Hijacked name"}
    ).status_code == 404
    assert client.delete(f"/api/products/{pid}").status_code == 404


def test_other_account_can_reuse_the_same_name(isolated_api):
    """Name chỉ unique PER-OWNER: hai công ty đều có thể có product cùng tên."""
    client, pid, app, current = isolated_api
    created = client.post("/api/products", json={"name": "Owner product"})
    assert created.status_code == 201, created.text
    assert created.json()["id"] != pid
    # Nhưng trùng tên trong CHÍNH account của mình vẫn 409.
    assert client.post("/api/products", json={"name": "Owner product"}).status_code == 409


def test_owner_still_sees_and_manages_own_product(isolated_api):
    client, pid, app, current = isolated_api
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=_owner_id_from(app), email="owner@example.test"
    )
    response = client.get("/api/products")
    assert [item["id"] for item in response.json()["items"]] == [pid]
    renamed = client.patch(f"/api/products/{pid}", json={"name": "Renamed product"})
    assert renamed.status_code == 200
    assert client.get(f"/api/products/{pid}").json()["name"] == "Renamed product"


def _owner_id_from(app) -> uuid.UUID:
    """Lấy owner id từ override get_db (session sqlite trong fixture)."""
    db = app.dependency_overrides[get_db]()
    row = db.query(User).filter(User.email == "owner@example.test").one()
    return row.id


def test_missing_product_is_still_404(isolated_api):
    client, *_ = isolated_api
    assert client.get(f"/api/products/{uuid.uuid4()}").status_code == 404


def test_anonymous_account_still_requires_login(isolated_api):
    client, pid, app, _ = isolated_api
    del app.dependency_overrides[get_current_user]
    for method, url, kwargs in [
        ("get", "/api/products", {}),
        ("get", f"/api/products/{pid}", {}),
        ("patch", f"/api/products/{pid}", {"json": {"name": "Blocked edit"}}),
    ]:
        assert getattr(client, method)(url, **kwargs).status_code == 401


def test_current_user_response_contains_identity_only(isolated_api):
    client, _, app, current = isolated_api
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"id": str(current.id), "email": "other@example.test"}


def test_access_token_needs_identity_only():
    user_id = str(uuid.uuid4())
    token = create_access_token(sub=user_id)
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert set(payload) == {"sub", "iat", "exp"}
