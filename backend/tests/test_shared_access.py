"""Authenticated accounts share workspaces; identity still requires login."""

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
def shared_api():
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    User.__table__.create(engine)
    Product.__table__.create(engine)
    with Session(engine) as db:
        product = Product(name="Shared product", description="Created before this account")
        db.add(product)
        db.commit()
        pid = str(product.id)
        app = FastAPI()
        app.include_router(auth.router)
        app.include_router(products.router)
        app.dependency_overrides[get_db] = lambda: db
        account = SimpleNamespace(id=uuid.uuid4(), email="shared-test@example.test")
        app.dependency_overrides[get_current_user] = lambda: account
        with TestClient(app) as client:
            yield client, pid, app
    engine.dispose()


def test_account_lists_existing_shared_product(shared_api):
    client, pid, _ = shared_api
    response = client.get("/api/products")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [pid]


def test_account_reads_existing_shared_product(shared_api):
    client, pid, _ = shared_api
    response = client.get(f"/api/products/{pid}")
    assert response.status_code == 200
    assert response.json()["name"] == "Shared product"


def test_account_updates_existing_shared_product(shared_api):
    client, pid, _ = shared_api
    response = client.patch(f"/api/products/{pid}", json={"name": "Renamed product"})
    assert response.status_code == 200
    assert client.get(f"/api/products/{pid}").json()["name"] == "Renamed product"


def test_missing_product_is_still_404(shared_api):
    client, _, _ = shared_api
    assert client.get(f"/api/products/{uuid.uuid4()}").status_code == 404


def test_anonymous_account_still_requires_login(shared_api):
    client, pid, app = shared_api
    del app.dependency_overrides[get_current_user]
    for method, url, kwargs in [
        ("get", "/api/products", {}),
        ("get", f"/api/products/{pid}", {}),
        ("patch", f"/api/products/{pid}", {"json": {"name": "Blocked edit"}}),
    ]:
        assert getattr(client, method)(url, **kwargs).status_code == 401


def test_current_user_response_contains_identity_only(shared_api):
    client, _, app = shared_api
    account = SimpleNamespace(id=uuid.uuid4(), email="identity@example.test")
    app.dependency_overrides[get_current_user] = lambda: account
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"id": str(account.id), "email": "identity@example.test"}


def test_access_token_needs_identity_only():
    user_id = str(uuid.uuid4())
    token = create_access_token(sub=user_id)
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert set(payload) == {"sub", "iat", "exp"}
