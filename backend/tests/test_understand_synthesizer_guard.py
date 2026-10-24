"""Unit — synthesizer UNDERSTAND không được persist insight rỗng/hallucinate.

Bối cảnh 2026-10-23 (user report "chưa từng có đoạn chat nào thành công"):
DB cho thấy model yếu echo nguyên system prompt làm title với confidence 1.0
khi chưa có evidence nào — insight rác vẫn được persist vì whitelist rỗng bị
gán lại list rỗng. Guard mới: whitelist rỗng + không còn evidence khả dụng →
_limited_insight trung thực ("Không đủ bằng chứng…", confidence 0.3).
"""

import uuid

import pytest

from understand_agent import nodes as nodes_mod
from understand_agent.nodes import InsightDraft, LLMStructureError, synthesizer

_RUN_ID = str(uuid.uuid4())
_REAL_EV = str(uuid.uuid4())


def _state(**over):
    base = {
        "run_id": _RUN_ID,
        "question": "why did complaints rise?",
        "product_context": {},
        "evaluations": [],
        "evidence": [],
    }
    base.update(over)
    return base


def test_no_evidence_fabricated_ids_falls_back_to_limited_insight(monkeypatch):
    def _fake(system, user, schema, **kwargs):
        return InsightDraft(
            title="Tổng hợp evidence-grounded insight cho người quyết định",
            finding="echo của system prompt",
            finding_confidence=1.0,
            evidence_ids=["EV-BIA"],
        )

    monkeypatch.setattr(nodes_mod, "chat_structured", _fake)
    out = synthesizer(_state())
    assert out["draft_insight"]["title"].startswith("Không đủ bằng chứng")
    assert out["draft_insight"]["finding_confidence"] <= 0.5


def test_all_ids_fabricated_with_real_evidence_gets_real_ids(monkeypatch):
    def _fake(system, user, schema, **kwargs):
        return InsightDraft(
            title="Citation complaints tập trung ở v2.17",
            finding="8/32 feedback nhắc citation lỗi ở v2.17",
            finding_confidence=0.8,
            evidence_ids=["EV-BIA"],
        )

    monkeypatch.setattr(nodes_mod, "chat_structured", _fake)
    out = synthesizer(
        _state(
            evidence=[
                {
                    "evidence_id": _REAL_EV,
                    "tool": "aggregate_feedback",
                    "statement": "aggregate_feedback: {...}",
                }
            ]
        )
    )
    assert out["draft_insight"]["evidence_ids"] == [_REAL_EV]


def test_llm_structure_error_falls_back_to_limited_insight(monkeypatch):
    def _raise(*args, **kwargs):
        raise LLMStructureError("fallback chain thất bại")

    monkeypatch.setattr(nodes_mod, "chat_structured", _raise)
    out = synthesizer(_state())
    assert out["draft_insight"]["title"].startswith("Không đủ bằng chứng")


def test_synthesis_receives_result_beyond_old_truncation_limit(monkeypatch):
    import json
    captured = []
    def fake(system, user, schema, **kwargs):
        captured.append(json.loads(user))
        return InsightDraft(title="Supported", finding="Measured", finding_confidence=.8, evidence_ids=[_REAL_EV])
    monkeypatch.setattr(nodes_mod, "chat_structured", fake)
    synthesizer(_state(evidence=[{"evidence_id":_REAL_EV,"tool":"aggregate_feedback","statement":"x" * 500 + "12 login complaints"}]))
    assert "12 login complaints" in captured[0]["evidence"][0]["statement"]


def test_failed_tools_cannot_become_a_confident_finding(monkeypatch):
    monkeypatch.setattr(nodes_mod, "chat_structured", lambda *_a, **_k: pytest.fail("no usable evidence"))
    out = synthesizer(_state(evidence=[{
        "evidence_id": _REAL_EV, "tool":"representative_feedback", "statement":"{}",
        "payload":{}, "ok":False,
    }]))
    assert out["draft_insight"]["finding_confidence"] <= .5
    assert not out["draft_insight"]["evidence_ids"]


def test_samples_cannot_prove_absence_across_the_product(monkeypatch):
    monkeypatch.setattr(nodes_mod, "chat_structured", lambda *_a, **_k: InsightDraft(
        title="Không có phản hồi về đăng nhập", finding="Không có phản hồi nào về lỗi đăng nhập trong sản phẩm.",
        finding_confidence=1.0, evidence_ids=[_REAL_EV],
    ))
    out = synthesizer(_state(evidence=[{
        "evidence_id":_REAL_EV,"tool":"representative_feedback","statement":"One recent feedback",
        "payload":{"samples":[{"text":"One recent feedback"}]},"ok":True,
    }]))
    assert out["draft_insight"]["title"].startswith("Không đủ bằng chứng")
    assert out["draft_insight"]["finding_confidence"] <= .5
