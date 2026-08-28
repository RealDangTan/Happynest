"""Integration test LISTEN import flow + Gate #1 — plan 22 Task 4/5.

⚠️ Marker `integration` — DB Supabase thật; LLM mapper MOCK hoàn toàn
(monkeypatch `build_mapping_proposal` trong import_service) — không call LLM
thật, đúng nguyên tắc an toàn chi phí của suite.

Kịch bản (VoC OS §6/§13 DoD):
- Import 1 (schema chưa có): proposal PROMOTE 2 field → Gate #1 approve →
  schema v1 active + rows imported đúng JSONB zones;
- Import 2 (schema có sẵn): proposal MAP vào schema hiện có → KHÔNG tạo
  version mới;
- AMBIGUOUS + approve → 422 (human phải remap/promote/demote/ignore);
- decision thiếu/dư field → 422; re-decision → 409.
"""

import csv
import io
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.models.product_schema import ProductSchema
from app.schemas.import_ import MappingItemOut, MappingProposalOut
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration


def _login(client: TestClient, role: UserRole = UserRole.pm) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _csv_bytes(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


def _proposal(items: list[dict]) -> MappingProposalOut:
    return MappingProposalOut(
        mappings=[MappingItemOut.model_validate(m) for m in items]
    )


def _patch_mapper(monkeypatch, proposal: MappingProposalOut) -> None:
    from app.services import import_service as mod

    monkeypatch.setattr(mod, "build_mapping_proposal", lambda *a, **k: proposal)


def _base_rows() -> list[dict]:
    return [
        {
            "message": "App crash khi xuất file",
            "date": "2026-08-01T10:00:00+00:00",
            "plan": "enterprise",
            "build": "2.17",
            "agent_name": "Anna",
            "junk_id": "1",
            "ext_id": "listen-001",
        },
        {
            "message": "Search chậm quá",
            "date": "2026-08-02T10:00:00+00:00",
            "plan": "free",
            "build": "2.16",
            "agent_name": "Bob",
            "junk_id": "2",
            "ext_id": "listen-002",
        },
    ]


_FIRST_PROPOSAL = _proposal(
    [
        {"source_field": "message", "decision": "MAP", "target": "feedback_text",
         "confidence": 0.97, "reason": "text", "needs_human_review": False},
        {"source_field": "date", "decision": "MAP", "target": "occurred_at",
         "confidence": 0.95, "reason": "iso time", "needs_human_review": False},
        {"source_field": "plan", "decision": "PROMOTE",
         "candidate": {"key": "customer_plan", "label": "Customer Plan", "type": "category"},
         "confidence": 0.9, "reason": "analytical across sources", "needs_human_review": False},
        {"source_field": "build", "decision": "PROMOTE",
         "candidate": {"key": "app_version", "label": "App Version", "type": "category"},
         "confidence": 0.93, "reason": "version", "needs_human_review": False},
        {"source_field": "agent_name", "decision": "SOURCE_META",
         "confidence": 0.9, "reason": "source-only", "needs_human_review": False},
        {"source_field": "junk_id", "decision": "IGNORE",
         "confidence": 0.99, "reason": "no value", "needs_human_review": False},
        {"source_field": "ext_id", "decision": "MAP", "target": "source_record_id",
         "confidence": 0.95, "reason": "row id", "needs_human_review": False},
    ]
)

_REMAP_PROPOSAL = _proposal(
    [
        {"source_field": "message", "decision": "MAP", "target": "feedback_text",
         "confidence": 0.97, "reason": "text", "needs_human_review": False},
        {"source_field": "date", "decision": "MAP", "target": "occurred_at",
         "confidence": 0.95, "reason": "iso time", "needs_human_review": False},
        {"source_field": "plan", "decision": "MAP", "target": "customer_plan",
         "confidence": 0.9, "reason": "same concept", "needs_human_review": False},
        {"source_field": "build", "decision": "MAP", "target": "app_version",
         "confidence": 0.93, "reason": "same concept", "needs_human_review": False},
        {"source_field": "ext_id", "decision": "MAP", "target": "source_record_id",
         "confidence": 0.95, "reason": "row id", "needs_human_review": False},
    ]
)

_AMBIGUOUS_PROPOSAL = _proposal(
    [
        {"source_field": "message", "decision": "MAP", "target": "feedback_text",
         "confidence": 0.97, "reason": "text", "needs_human_review": False},
        {"source_field": "score", "decision": "AMBIGUOUS",
         "confidence": 0.4, "reason": "CSAT 1-5 hay NPS 0-10?",
         "needs_human_review": True},
    ]
)


@pytest.fixture()
def _env(test_product, monkeypatch):
    """Product id + dọn rác (feedback/import/schema/file raw) sau test."""
    state = {"product_id": test_product.id, "import_ids": [], "files": []}
    yield state
    with SessionLocal() as db:
        if state["import_ids"]:
            db.query(Feedback).filter(
                Feedback.import_id.in_(state["import_ids"])
            ).delete(synchronize_session=False)
            db.query(Import).filter(Import.id.in_(state["import_ids"])).delete(
                synchronize_session=False
            )
        db.query(ProductSchema).filter(
            ProductSchema.product_id == test_product.id
        ).delete(synchronize_session=False)
        db.commit()
    for f in state["files"]:
        Path(f).unlink(missing_ok=True)


def _upload(client, auth, monkeypatch, proposal, _env, rows=None, product_id=None):
    _patch_mapper(monkeypatch, proposal)
    raw = _csv_bytes(rows or _base_rows())
    resp = client.post(
        "/api/imports",
        files={"file": ("listen.csv", raw, "text/csv")},
        data={"product_id": str(product_id or _env["product_id"])},
        headers=auth,
    )
    if resp.status_code == 201:
        body = resp.json()
        _env["import_ids"].append(uuid.UUID(body["id"]))
        if body.get("storage_path"):
            _env["files"].append(body["storage_path"])
    return resp


def _approve_all(mapping_json: dict, action: str = "approve") -> dict:
    return {
        "decisions": [
            {"source_field": m["source_field"], "action": action}
            for m in mapping_json["mappings"]
        ]
    }


def test_first_import_bootstraps_schema_and_imports(client, monkeypatch, _env):
    auth = _login(client)
    resp = _upload(client, auth, monkeypatch, _FIRST_PROPOSAL, _env)
    assert resp.status_code == 201, resp.text
    imp = resp.json()
    assert imp["status"] == "mapping_review"
    assert imp["storage_path"]

    mapping = client.get(f"/api/imports/{imp['id']}/mapping", headers=auth).json()
    assert {m["source_field"] for m in mapping["mappings"]} == {
        "message", "date", "plan", "build", "agent_name", "junk_id", "ext_id",
    }

    dec = client.post(
        f"/api/imports/{imp['id']}/mapping/decision",
        json=_approve_all(mapping),
        headers=auth,
    )
    assert dec.status_code == 200, dec.text
    report = dec.json()
    assert report["imported"] == 2 and report["failed"] == 0
    assert report["schema_version"] == 1

    # Schema v1 active với 2 field promote
    schema_resp = client.get(f"/api/products/{_env['product_id']}/schema", headers=auth).json()
    assert schema_resp["schema"]["version"] == 1
    keys = {f["key"] for f in schema_resp["schema"]["definition"]["fields"]}
    assert keys == {"customer_plan", "app_version"}

    # Rows đúng JSONB zones
    with SessionLocal() as db:
        rows = db.scalars(
            select(Feedback).where(Feedback.import_id == uuid.UUID(imp["id"]))
        ).all()
        assert len(rows) == 2
        r1 = next(r for r in rows if r.source_record_id == "listen-001")
        assert r1.feedback_text == "App crash khi xuất file"
        assert r1.data == {"customer_plan": "enterprise", "app_version": "2.17"}
        assert r1.source_meta == {"agent_name": "Anna"}
        assert r1.occurred_at == datetime.fromisoformat("2026-08-01T10:00:00+00:00")
        assert r1.import_id == uuid.UUID(imp["id"])

    # Re-decision → 409 (import đã applied)
    dec2 = client.post(
        f"/api/imports/{imp['id']}/mapping/decision",
        json=_approve_all(mapping),
        headers=auth,
    )
    assert dec2.status_code == 409

    # Import dở khác bị chặn 409 cho cùng product? — import này đã applied nên
    # trạng thái sạch; upload thứ hai ngay sau đó phải OK (test thứ 2 phủ).


def test_second_import_maps_into_existing_schema(client, monkeypatch, _env):
    auth = _login(client)
    r1 = _upload(client, auth, monkeypatch, _FIRST_PROPOSAL, _env)
    assert r1.status_code == 201
    dec = client.post(
        f"/api/imports/{r1.json()['id']}/mapping/decision",
        json=_approve_all(client.get(f"/api/imports/{r1.json()['id']}/mapping", headers=auth).json()),
        headers=auth,
    )
    assert dec.status_code == 200 and dec.json()["schema_version"] == 1

    # Import 2: cùng cột, tên khác → MAP vào schema hiện có, KHÔNG promote
    rows = [
        {
            "message": "Vẫn crash",
            "date": "2026-08-05T10:00:00+00:00",
            "plan": "pro",
            "build": "2.17",
            "ext_id": "listen-003",
        },
    ]
    resp = _upload(client, auth, monkeypatch, _REMAP_PROPOSAL, _env, rows=rows)
    assert resp.status_code == 201
    mapping = client.get(f"/api/imports/{resp.json()['id']}/mapping", headers=auth).json()
    dec2 = client.post(
        f"/api/imports/{resp.json()['id']}/mapping/decision",
        json=_approve_all(mapping),
        headers=auth,
    )
    assert dec2.status_code == 200, dec2.text
    # §13: schema KHÔNG mở rộng khi concept đã có
    assert dec2.json()["schema_version"] == 1

    with SessionLocal() as db:
        row = db.scalars(
            select(Feedback).where(Feedback.source_record_id == "listen-003")
        ).one()
        assert row.data == {"customer_plan": "pro", "app_version": "2.17"}
        assert row.source_meta == {}


def test_ambiguous_cannot_be_approved(client, monkeypatch, _env):
    auth = _login(client)
    rows = [
        {"message": "Ổn", "score": "5", "ext_id": "listen-amb-1"},
    ]
    resp = _upload(client, auth, monkeypatch, _AMBIGUOUS_PROPOSAL, _env, rows=rows)
    assert resp.status_code == 201
    mapping = client.get(f"/api/imports/{resp.json()['id']}/mapping", headers=auth).json()
    # approve máy móc AMBIGUOUS → 422
    dec = client.post(
        f"/api/imports/{resp.json()['id']}/mapping/decision",
        json=_approve_all(mapping),
        headers=auth,
    )
    assert dec.status_code == 422
    # human demote score → source_meta, remap thành công
    body = {
        "decisions": [
            {"source_field": "message", "action": "approve"},
            {"source_field": "score", "action": "demote"},
        ]
    }
    dec2 = client.post(
        f"/api/imports/{resp.json()['id']}/mapping/decision",
        json=body,
        headers=auth,
    )
    assert dec2.status_code == 200, dec2.text
    assert dec2.json()["imported"] == 1


def test_decision_must_cover_all_fields(client, monkeypatch, _env):
    auth = _login(client)
    resp = _upload(client, auth, monkeypatch, _FIRST_PROPOSAL, _env)
    assert resp.status_code == 201
    # thiếu 1 field → 422
    body = {
        "decisions": [
            {"source_field": "message", "action": "approve"},
        ]
    }
    dec = client.post(
        f"/api/imports/{resp.json()['id']}/mapping/decision",
        json=body,
        headers=auth,
    )
    assert dec.status_code == 422
    # dư field lạ → 422
    body = {
        "decisions": _approve_all(
            client.get(f"/api/imports/{resp.json()['id']}/mapping", headers=auth).json()
        )["decisions"]
        + [{"source_field": "unknown_col", "action": "ignore"}]
    }
    dec = client.post(
        f"/api/imports/{resp.json()['id']}/mapping/decision",
        json=body,
        headers=auth,
    )
    assert dec.status_code == 422


def test_import_requires_auth_and_bad_extension(client, monkeypatch, _env):
    # anon → 401
    raw = _csv_bytes(_base_rows())
    assert client.post(
        "/api/imports",
        files={"file": ("x.csv", raw, "text/csv")},
        data={"product_id": str(_env["product_id"])},
    ).status_code == 401

    auth = _login(client)
    resp = client.post(
        "/api/imports",
        files={"file": ("not_csv.txt", b"hello", "text/plain")},
        data={"product_id": str(_env["product_id"])},
        headers=auth,
    )
    assert resp.status_code == 422


def test_coverage_endpoint(client, monkeypatch, _env):
    """Coverage per field sau import (VoC OS §19)."""
    auth = _login(client)
    resp = _upload(client, auth, monkeypatch, _FIRST_PROPOSAL, _env)
    imp_id = resp.json()["id"]
    mapping = client.get(f"/api/imports/{imp_id}/mapping", headers=auth).json()
    dec = client.post(
        f"/api/imports/{imp_id}/mapping/decision",
        json=_approve_all(mapping),
        headers=auth,
    )
    assert dec.status_code == 200

    cov = client.get(
        f"/api/products/{_env['product_id']}/schema/coverage", headers=auth
    ).json()
    assert cov["total_records"] >= 2
    assert cov["coverage"]["customer_plan"] == pytest.approx(1.0)
    assert cov["coverage"]["app_version"] == pytest.approx(1.0)
