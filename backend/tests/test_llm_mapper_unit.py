"""Unit — chuẩn hoá proposal của LLM mapper (E2E 2026-11-05).

gpt-4o-mini đề xuất `created_at → PROMOTE occurred_at`; approve ở Gate #1 bị 422
vì occurred_at là core. PROMOTE vào key đã có phải thành MAP cùng key.
"""

from app.services.llm_mapper import MappingProposal, normalize_promotions

EXISTING = [{"key": "feedback_text"}, {"key": "occurred_at"}, {"key": "source"},
            {"key": "source_record_id"}, {"key": "app_version"}]


def _proposal(*items):
    return MappingProposal.model_validate({"mappings": list(items)})


def test_promote_to_existing_core_key_becomes_map():
    out = normalize_promotions(_proposal({
        "source_field": "created_at", "decision": "PROMOTE", "confidence": 0.9, "reason": "thời gian",
        "candidate": {"key": "occurred_at", "label": "Occurred", "type": "datetime"},
    }), EXISTING)
    item = out.mappings[0]
    assert (item.decision, item.target, item.candidate) == ("MAP", "occurred_at", None)
    assert "Chuẩn hoá" in item.reason and item.confidence == 0.9


def test_promote_to_existing_product_field_becomes_map():
    out = normalize_promotions(_proposal({
        "source_field": "version", "decision": "PROMOTE", "confidence": 0.8, "reason": "r",
        "candidate": {"key": "app_version", "label": "App version", "type": "category"},
    }), EXISTING)
    assert out.mappings[0].decision == "MAP" and out.mappings[0].target == "app_version"


def test_genuinely_new_promotion_and_other_decisions_untouched():
    out = normalize_promotions(_proposal(
        {"source_field": "country", "decision": "PROMOTE", "confidence": 0.8, "reason": "r",
         "candidate": {"key": "country", "label": "Country", "type": "category"}},
        {"source_field": "rating", "decision": "AMBIGUOUS", "confidence": 0.6, "reason": "r"},
    ), EXISTING)
    assert [m.decision for m in out.mappings] == ["PROMOTE", "AMBIGUOUS"]
    assert out.mappings[0].candidate.key == "country"
