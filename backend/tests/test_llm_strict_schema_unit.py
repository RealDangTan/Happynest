"""Unit — cờ `strict` của Mode A chỉ bật khi schema đạt chuẩn strict (2026-11-05).

Audit llm_call_logs: với openai/gpt-4o-mini, ~50% attempt plan/evaluate/synthesize/
name_cluster/schema_map là 400 "Invalid schema for response_format" vì schema Pydantic
tự sinh ($defs, khóa optional, object tự do) bị gửi kèm strict=true.
"""

from pydantic import BaseModel

from app.models.enums import LlmCallType
from app.services import llm_client
from app.services.llm_client import _strict_compatible


def test_strict_compatible_rules():
    ok = {"type": "object", "additionalProperties": False, "required": ["a"],
          "properties": {"a": {"type": "array", "items": {
              "type": "object", "additionalProperties": False, "required": ["b"],
              "properties": {"b": {"anyOf": [{"type": "string"}, {"type": "null"}]}}}}}}
    assert _strict_compatible(ok)
    assert not _strict_compatible({**ok, "required": []})                       # khóa optional
    assert not _strict_compatible({**ok, "additionalProperties": True})
    assert not _strict_compatible({"type": "object"})                           # dict tự do
    assert not _strict_compatible({**ok, "$defs": {}})


class _Loose(BaseModel):
    name: str
    note: str | None = None


def test_mode_a_sends_strict_false_for_generated_schema(monkeypatch):
    seen = {}

    def fake_api(messages, response_format, model=None, max_tokens=None):
        seen["fmt"] = response_format
        return '{"name": "x"}', {"prompt": 1, "completion": 1}

    monkeypatch.setattr(llm_client, "_api_call", fake_api)
    monkeypatch.setattr(llm_client, "_record_attempt", lambda **kwargs: None)
    out = llm_client.chat_structured("sys", "user", _Loose, call_type=LlmCallType.plan,
                                     prompt_version="t", model="m")
    assert out.name == "x"
    assert seen["fmt"]["json_schema"]["strict"] is False


def test_agent_schemas_strictness_matches_provider_evidence():
    from app.schemas.taxonomy import TaxonomyProposalOut
    from understand_agent.nodes import EvaluateOut, PlannerOut

    assert llm_client._is_strict_schema(TaxonomyProposalOut)  # 0 lỗi 400 trong log
    assert llm_client._is_strict_schema(EvaluateOut)          # schema inline viết tay
    assert not llm_client._is_strict_schema(PlannerOut)       # params là object tự do
