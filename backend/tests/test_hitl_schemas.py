"""Unit tests schemas HITL — Phase 13 Task 2 (13-hitl-langgraph.md §3.2).

Thuần Pydantic, KHÔNG DB — chạy offline trong suite mặc định.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.hitl import CorrectionIn, CorrectionOut, ReviewIn


# ------------------------------------------------------------------- ReviewIn

def test_review_edit_without_content_rejected():
    with pytest.raises(ValidationError):
        ReviewIn.model_validate({"action": "edit"})


def test_review_edit_blank_content_rejected():
    for blank in ("", "   ", "\n\t"):
        with pytest.raises(ValidationError):
            ReviewIn.model_validate({"action": "edit", "edited_content": blank})


def test_review_edit_with_content_accepted():
    body = ReviewIn.model_validate(
        {"action": "edit", "edited_content": "nội dung đã sửa", "reason": "sai nhãn"}
    )
    assert body.edited_content == "nội dung đã sửa"


def test_review_approve_accepts_extra_content_field():
    """approve kèm edited_content thừa → chấp nhận (schema không chặn; graph sẽ bỏ qua)."""
    body = ReviewIn.model_validate(
        {"action": "approve", "edited_content": "bị bỏ qua"}
    )
    assert body.action == "approve"


def test_review_unknown_action_rejected():
    with pytest.raises(ValidationError):
        ReviewIn.model_validate({"action": "delete"})



# --------------------------------------------------------------- CorrectionIn

def test_correction_empty_body_rejected():
    with pytest.raises(ValidationError):
        CorrectionIn.model_validate({})


def test_correction_all_null_labels_rejected():
    with pytest.raises(ValidationError):
        CorrectionIn.model_validate(
            {"categories": None, "ai_issue": None, "severity": None, "sentiment": None}
        )


def test_correction_single_label_accepted():
    body = CorrectionIn.model_validate({"severity": "high", "note": "đánh giá lại"})
    assert body.label_updates() == {"severity": "high"}


def test_correction_bad_enum_value_rejected():
    with pytest.raises(ValidationError):
        CorrectionIn.model_validate({"ai_issue": "khong-phai-enum"})


def test_correction_blank_category_item_rejected():
    with pytest.raises(ValidationError):
        CorrectionIn.model_validate({"categories": ["hợp lệ", "  "]})



# -------------------------------------------------------------- CorrectionOut

def _fake_feedback() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        source="test",
        external_ref="hitl-schema-1",
        created_at=__import__("datetime").datetime(2026, 8, 25),
        imported_at=__import__("datetime").datetime(2026, 8, 25),
        review_status="edited",
        pii_detected=True,
        severity="high",
        categories=["dịch thuật"],
        ai_issue=None,
        sentiment="negative",
        confidence=0.9,
        requires_human_review=True,
        sanitized_content="nội dung <PHONE_NUMBER>",
    )


def test_correction_out_flat_response_shape():
    out = CorrectionOut.model_validate(_fake_feedback())
    assert out.correction_recorded is False  # default khi chưa set


def test_correction_out_flag_set_true():
    fb = _fake_feedback()
    base = CorrectionOut.model_validate(fb)
    final = base.model_copy(update={"correction_recorded": True})
    assert final.correction_recorded is True
    assert final.review_status == "edited"
    # PII boundary: shape response không có field raw_content
    assert "raw_content" not in CorrectionOut.model_fields
