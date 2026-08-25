"""Integration tests Phase 13 — HITL reviews/corrections end-to-end (plan §3.4.5).

⚠️ Marker `integration`: chạm Supabase thật (feedbacks + 4 bảng checkpoint
LangGraph qua AsyncPostgresSaver) + Presidio thật cho action=edit. Mỗi graph
flow tốn nhiều lần checkpoint-write qua WAN (~vài chục giây) — chạy riêng:
    uv run pytest -m integration tests/test_hitl_flow_integration.py -v

Không có call LLM nào trong phase này (review là thao tác người dùng).

Dọn rác theo external_ref prefix `hitl-it-` + thread checkpoint tương ứng
(quy ước conftest Phase 11 — DB dev dùng chung).
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.main import app
from app.models.correction_example import CorrectionExample
from app.models.enums import ReviewStatus, Sentiment, Severity
from app.models.feedback import Feedback
from app.models.human_review import HumanReview
from app.models.user import UserRole
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

SOURCE = "test-hitl13"
REF_PREFIX = "hitl-it-"

_CHECKPOINT_TABLES = ("checkpoint_writes", "checkpoint_blobs", "checkpoints")


# ----------------------------------------------------------------- seed/cleanup


def _seed_feedback(ref: str, *, pending: bool, classified: bool = True) -> uuid.UUID:
    """Seed 1 row feedback trực tiếp (không LLM, không presidio — content sạch sẵn)."""
    with SessionLocal() as db:
        fb = Feedback(
            source=SOURCE,
            external_ref=f"{REF_PREFIX}{ref}-{uuid.uuid4().hex[:8]}",
            raw_content=f"nội dung test hitl {ref} (không PII)",
            sanitized_content=f"app chậm khi export file [{ref}]",
            created_at=datetime.now(timezone.utc),
            categories=["nhãn-test"] if classified else None,
            ai_issue=None,
            sentiment=Sentiment.negative,
            severity=Severity.medium,
            confidence=0.9,
            requires_human_review=pending,
            review_status=ReviewStatus.pending if pending else ReviewStatus.unreviewed,
        )
        db.add(fb)
        db.commit()
        return fb.id


def _cleanup(ids: list[uuid.UUID]) -> None:
    with SessionLocal() as db:
        for fid in ids:
            tid = f"hitl-{fid}"
            db.execute(
                text("DELETE FROM correction_examples WHERE feedback_id = CAST(:fid AS uuid)"),
                {"fid": str(fid)},
            )
            db.execute(
                text("DELETE FROM human_reviews WHERE feedback_id = CAST(:fid AS uuid)"),
                {"fid": str(fid)},
            )
            for table in _CHECKPOINT_TABLES:
                db.execute(text(f"DELETE FROM {table} WHERE thread_id = :tid"), {"tid": tid})
        db.query(Feedback).filter(Feedback.source == SOURCE).delete(
            synchronize_session=False
        )
        db.commit()


@pytest.fixture()
def hitl_rows():
    """Gom id mọi row seed trong test để teardown dọn sạch (kể cả checkpoint)."""
    ids: list[uuid.UUID] = []
    yield ids
    _cleanup(ids)


# ------------------------------------------------------------------- helpers


def _login(client: TestClient, role: UserRole = UserRole.pm) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[role], "password": TEST_PASSWORDS[role]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _reviews_count(feedback_id: uuid.UUID) -> list[HumanReview]:
    with SessionLocal() as db:
        return (
            db.query(HumanReview)
            .filter(HumanReview.feedback_id == feedback_id)
            .all()
        )


def _examples_count(feedback_id: uuid.UUID) -> list[CorrectionExample]:
    with SessionLocal() as db:
        return (
            db.query(CorrectionExample)
            .filter(CorrectionExample.feedback_id == feedback_id)
            .all()
        )


# ------------------------------------------------------- POST /reviews flows


def test_review_approve_end_to_end(client, hitl_rows):
    fid = _seed_feedback("approve", pending=True)
    hitl_rows.append(fid)
    headers = _login(client)

    resp = client.post(f"/api/reviews/{fid}", json={"action": "approve"}, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["review_status"] == "approved"
    assert body["id"] == str(fid)

    # Approve KHÔNG ghi dòng log nào (contract C3: side effect chỉ edit/reject);
    # graph chạy qua nhiều lần checkpoint-write mà vẫn không sinh row thừa.
    assert _reviews_count(fid) == []
    assert _examples_count(fid) == []  # approve không nuôi few-shot

    # Review lặp → 409 (route pre-check thấy status đã approved)
    dup = client.post(f"/api/reviews/{fid}", json={"action": "approve"}, headers=headers)
    assert dup.status_code == 409


def test_review_edit_runs_presidio_and_records_example(client, hitl_rows):
    fid = _seed_feedback("edit", pending=True)
    hitl_rows.append(fid)
    headers = _login(client)

    resp = client.post(
        f"/api/reviews/{fid}",
        json={
            "action": "edit",
            "edited_content": "gọi hotline 0900 123 456 để được hỗ trợ",
            "reason": "người dùng bổ sung thông tin liên hệ",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["review_status"] == "edited"
    # Presidio TRƯỚC khi lưu: raw người dùng gõ KHÔNG BAO GIỜ nằm nguyên trong DB
    assert "<PHONE_NUMBER>" in body["sanitized_content"]
    assert "0900 123 456" not in body["sanitized_content"]
    assert body["pii_detected"] is True

    examples = _examples_count(fid)
    assert len(examples) == 1
    corrected = examples[0].corrected_value
    # ngữ nghĩa plan §3.2: NHÃN CŨ giữ nguyên + sanitized_content mới
    assert corrected["categories"] == ["nhãn-test"]
    assert corrected["sanitized_content"] == body["sanitized_content"]
    assert len(_reviews_count(fid)) == 1


def test_review_reject_records_negative_example(client, hitl_rows):
    fid = _seed_feedback("reject", pending=True)
    hitl_rows.append(fid)
    headers = _login(client)

    resp = client.post(
        f"/api/reviews/{fid}", json={"action": "reject", "reason": "spam/quảng cáo"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["review_status"] == "rejected"
    # content nguyên vẹn khi reject
    assert resp.json()["sanitized_content"] == f"app chậm khi export file [reject]"

    examples = _examples_count(fid)
    assert len(examples) == 1
    assert examples[0].corrected_value == {
        "categories": [],
        "ai_issue": None,
        "severity": None,
        "sentiment": None,
    }


def test_review_edit_without_content_is_422(client, hitl_rows):
    fid = _seed_feedback("edit422", pending=True)
    hitl_rows.append(fid)
    headers = _login(client)

    resp = client.post(f"/api/reviews/{fid}", json={"action": "edit"}, headers=headers)
    assert resp.status_code == 422
    assert _reviews_count(fid) == []  # không ghi gì xuống DB


def test_review_unknown_feedback_404(client):
    headers = _login(client)
    resp = client.post(
        f"/api/reviews/{uuid.uuid4()}", json={"action": "approve"}, headers=headers
    )
    assert resp.status_code == 404


def test_review_requires_auth(client, hitl_rows):
    fid = _seed_feedback("anon", pending=True)
    hitl_rows.append(fid)
    client.cookies.clear()
    resp = client.post(f"/api/reviews/{fid}", json={"action": "approve"})
    assert resp.status_code == 401


# -------------------------------------------------- POST /corrections flows


def test_correction_updates_labels_and_feeds_loop(client, hitl_rows):
    fid = _seed_feedback("corr", pending=False, classified=True)
    hitl_rows.append(fid)
    headers = _login(client, UserRole.operations)  # operations cũng được quyền

    resp = client.post(
        f"/api/corrections/{fid}",
        json={"severity": "critical", "categories": ["mất dữ liệu"], "note": "đánh giá lại"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["correction_recorded"] is True
    assert body["severity"] == "critical"
    assert body["categories"] == ["mất dữ liệu"]
    assert body["sentiment"] == "negative"  # nhãn không gửi → giữ nguyên

    with SessionLocal() as db:
        row = db.get(Feedback, fid)
        assert row.severity is Severity.critical
    examples = _examples_count(fid)
    assert len(examples) == 1
    assert examples[0].corrected_value["severity"] == "critical"
    assert examples[0].reason == "đánh giá lại"
    reviews = _reviews_count(fid)
    assert len(reviews) == 1 and reviews[0].action.value == "edit"


def test_correction_empty_body_422(client, hitl_rows):
    fid = _seed_feedback("corr422", pending=False)
    hitl_rows.append(fid)
    headers = _login(client)
    resp = client.post(f"/api/corrections/{fid}", json={}, headers=headers)
    assert resp.status_code == 422


def test_correction_unclassified_feedback_409(client, hitl_rows):
    fid = _seed_feedback("corr409", pending=False, classified=False)
    hitl_rows.append(fid)
    headers = _login(client)
    resp = client.post(
        f"/api/corrections/{fid}", json={"severity": "low"}, headers=headers
    )
    assert resp.status_code == 409


def test_correction_unknown_feedback_404(client):
    headers = _login(client)
    resp = client.post(
        f"/api/corrections/{uuid.uuid4()}", json={"severity": "low"}, headers=headers
    )
    assert resp.status_code == 404
