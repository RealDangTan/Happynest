"""Unit test thuần profiler + schema validation — plan 22 Task 2/Task 1.

Không DB, không LLM: profiler là deterministic (VoC OS §7 — "Do NOT use an LLM
for basic profiling"); schema validation chạy trước DB nên test offline được.
"""

from datetime import datetime

import pytest

from app.services.profiler import _detect_type, profile_columns
from app.services.schema_registry import CORE_KEYS, _validate_definition


# ----------------------------------------------------------------- profiler


def test_detect_type_basic() -> None:
    assert _detect_type(["true", "false", "true"], {"true", "false"}) == "boolean"
    assert _detect_type(["1", "2.5", "10"], {"1", "2.5", "10"}) == "numeric"
    assert _detect_type(["2026-01-01", "2026-02-03"], {"a", "b"}) == "datetime"
    # cardinality thấp → category
    assert _detect_type(["enterprise", "free", "pro"], {"enterprise", "free", "pro"}) == "category"
    # cardinality cao → text
    assert _detect_type([f"msg {i}" for i in range(40)], {f"msg {i}" for i in range(40)}) == "text"


def test_profile_columns_shape() -> None:
    rows = [
        {"version": "2.17", "score": "3", "when": "2026-08-01T00:00:00"},
        {"version": "2.17", "score": "4", "when": "2026-08-02T00:00:00"},
        {"version": "", "score": "5", "when": "2026-08-03T00:00:00"},
    ]
    profiles = {p["name"]: p for p in profile_columns(rows)}

    v = profiles["version"]
    assert v["detected_type"] == "category"
    assert v["missing_rate"] == pytest.approx(1 / 3, rel=1e-3)  # profiler round 4 chữ số
    assert v["cardinality"] == 1
    assert v["sample_values"] == ["2.17"]

    s = profiles["score"]
    assert s["detected_type"] == "numeric"
    assert s["min"] == 3.0 and s["max"] == 5.0

    w = profiles["when"]
    assert w["detected_type"] == "datetime"
    assert w["min"] == "2026-08-01T00:00:00" and w["max"] == "2026-08-03T00:00:00"


def test_profile_empty_column_is_text_missing_1() -> None:
    profiles = profile_columns([{"empty": "", "x": "1"}])
    p = {q["name"]: q for q in profiles}["empty"]
    assert p["detected_type"] == "text"
    assert p["missing_rate"] == 1.0
    assert p["sample_values"] == []


# --------------------------------------------------- schema registry (pure)


def test_validate_definition_rejects_core_key_and_bad_type() -> None:
    with pytest.raises(ValueError, match="system core"):
        _validate_definition({"fields": [{"key": "feedback_text", "type": "text"}]})
    with pytest.raises(ValueError, match="type không hợp lệ"):
        _validate_definition({"fields": [{"key": "plan", "type": "weird"}]})
    with pytest.raises(ValueError, match="trùng"):
        _validate_definition(
            {
                "fields": [
                    {"key": "plan", "type": "category"},
                    {"key": "plan", "type": "text"},
                ]
            }
        )
    # hợp lệ
    _validate_definition({"fields": [{"key": "customer_plan", "type": "category"}]})
    assert "feedback_text" in CORE_KEYS
    assert isinstance(datetime.now(), datetime)  # placeholder giữ import dùng
