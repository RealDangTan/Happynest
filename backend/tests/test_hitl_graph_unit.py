"""Unit tests HITL graph — Phase 13 Task 3.6 (13-hitl-langgraph.md §3.3).

Mock HOÀN TOÀN seams DB/Presidio + InMemorySaver — không chạm Supabase,
không event loop thật của psycopg, chạy offline trong suite mặc định.
Mục tiêu: ngữ nghĩa 3 action + điều kiện record_correction + idempotency
guard + bộ phân loại trạng thái thread.
"""

import uuid
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.services import hitl_graph as hg
from app.models.enums import ReviewStatus, Sentiment, Severity


def _fake_feedback(**overrides) -> SimpleNamespace:
    base = dict(
        id=uuid.uuid4(),
        categories=["dịch thuật"],
        ai_issue=None,
        sentiment=Sentiment.negative,  # ORM trả Python enum — giả lập y hệt
        severity=Severity.high,
        sanitized_content="app dịch chậm <PHONE_NUMBER>",
        pii_detected=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture()
def fake_db(monkeypatch):
    """Thay toàn bộ seams DB bằng store in-memory đếm được."""
    state: dict = {"fb": _fake_feedback(), "statuses": [], "sanitize_calls": []}

    def load(feedback_id):
        return state["fb"]

    def persist_sanitize(feedback_id, edited_text):
        state["sanitize_calls"].append(edited_text)
        # giả lập Presidio: nội dung mới chứa số điện thoại giả lập → masked
        state["fb"].sanitized_content = edited_text.replace("0900", "<PHONE_NUMBER>")
        state["fb"].pii_detected = "0900" in edited_text
        return {
            "sanitized_content": state["fb"].sanitized_content,
            "pii_detected": state["fb"].pii_detected,
        }

    def set_status(feedback_id, status):
        state["statuses"].append(status)

    logged: list[dict] = []
    review_exists: list[bool] = []

    monkeypatch.setattr(hg, "_load_feedback", load)
    monkeypatch.setattr(hg, "_persist_sanitize", persist_sanitize)
    monkeypatch.setattr(hg, "_set_status", set_status)
    monkeypatch.setattr(
        hg,
        "_review_exists",
        lambda thread_id, action: bool(review_exists and review_exists[-1]),
    )
    monkeypatch.setattr(hg, "_write_review_rows", lambda **kw: logged.append(kw))
    state["logged"] = logged
    state["review_exists"] = review_exists
    return state


def _drive(fake_db, resume_payload: dict) -> dict:
    """Chạy trọn vẹn 1 review trên InMemorySaver: invoke tới interrupt rồi resume."""
    graph = hg.build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": f"hitl-{fake_db['fb'].id}"}}
    graph.invoke({"feedback_id": str(fake_db["fb"].id), "reviewer_id": str(uuid.uuid4())}, config)
    snap = graph.get_state(config)
    assert hg._next_graph_step(snap) == "resume", "phải đậu ở interrupt prepare_review"
    graph.invoke(Command(resume=resume_payload), config)
    return graph.get_state(config).values


# ------------------------------------------------------------------- approve

def test_approve_keeps_content_and_skips_correction(fake_db):
    before_content = fake_db["fb"].sanitized_content
    values = _drive(fake_db, {"action": "approve"})
    assert values["final_status"] == ReviewStatus.approved.value
    assert fake_db["fb"].sanitized_content == before_content  # không đụng content
    assert fake_db["logged"] == []  # approve KHÔNG ghi correction/human_review


# ---------------------------------------------------------------------- edit

def test_edit_runs_presidio_and_records_positive_example(fake_db):
    values = _drive(
        fake_db,
        {"action": "edit", "edited_content": "số mới 0900123456", "reason": "bỏ PII"},
    )
    assert values["final_status"] == ReviewStatus.edited.value
    assert fake_db["sanitize_calls"] == ["số mới 0900123456"]  # Presidio TRƯỚC khi lưu
    assert len(fake_db["logged"]) == 1
    log = fake_db["logged"][0]
    # corrected_value: NHÃN CŨ giữ nguyên + sanitized_content MỚI (plan §3.2)
    assert log["corrected_value"]["categories"] == ["dịch thuật"]
    assert log["corrected_value"]["severity"] == "high"
    # fake presidio chỉ mask prefix "0900" — đủ chứng minh content đã đổi
    assert log["corrected_value"]["sanitized_content"] == "số mới <PHONE_NUMBER>123456"
    assert log["original"]["sanitized_content"] == "app dịch chậm <PHONE_NUMBER>"
    assert log["edited"]["pii_detected"] is True


# -------------------------------------------------------------------- reject

def test_reject_records_negative_empty_labels(fake_db):
    values = _drive(fake_db, {"action": "reject", "reason": "spam"})
    assert values["final_status"] == ReviewStatus.rejected.value
    log = fake_db["logged"][0]
    # tín hiệu ÂM hoàn toàn cho few-shot
    assert log["corrected_value"] == {
        "categories": [],
        "ai_issue": None,
        "severity": None,
        "sentiment": None,
    }
    assert log["original"]["categories"] == ["dịch thuật"]  # snapshot pre-review


# ------------------------------------------------------- idempotency guard

def test_duplicate_guard_skips_rewrite(fake_db):
    fake_db["review_exists"].append(True)  # marker `_thread` trùng → node chạy lại
    _drive(fake_db, {"action": "reject"})
    assert fake_db["logged"] == []


# -------------------------------------------------- trạng thái thread (409)

def test_next_graph_step_classification():
    tid = "t"

    def snap(values, nxt, interrupts):
        return SimpleNamespace(
            values=values,
            next=nxt,
            tasks=(SimpleNamespace(interrupts=interrupts),),
            config={"configurable": {"thread_id": tid}},
        )

    assert hg._next_graph_step(snap({}, (), [])) == "start"
    assert hg._next_graph_step(snap({"a": 1}, ("prepare_review",), [object()])) == "resume"
    # crash ngay TẠI interrupt: tasks rỗng nhưng next chỉ về prepare_review
    assert hg._next_graph_step(snap({"a": 1}, ("prepare_review",), [])) == "resume"
    assert hg._next_graph_step(snap({"a": 1}, ("apply_action",), [])) == "continue"
    assert hg._next_graph_step(snap({"a": 1}, (), [])) == "completed"
