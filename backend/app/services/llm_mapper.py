"""LLM Schema Mapper — VOICE: propose; KHÔNG BAO GIỜ tự mutate schema (VoC OS §11).

Input: existing_schema (core + product fields) + incoming_profiles (deterministic
profiler). Output per source_field: MAP | PROMOTE | SOURCE_META | IGNORE |
AMBIGUOUS + confidence + reason (VoC OS §10). AMBIGUOUS/needs_human_review=true
→ Gate #1 bắt buộc human quyết.

Quy tắc nhúng trong prompt:
- Promotion test §14: field chỉ PROMOTE khi còn hợp lý về mặt phân tích nếu
  feedback đến từ NGUỒN KHÁC cùng product; chỉ meaningful trong nguồn gốc
  (ticket_status, agent...) → SOURCE_META.
- Remap imports sau (§13): ưu tiên MAP vào schema hiện có, chỉ propose mở rộng
  khi là khái niệm MỚI thật sự.
- LLM KHÔNG được: đổi schema ngầm, xoá field, viết lại nghĩa lịch sử, import
  thẳng production.
"""

from pydantic import BaseModel, Field

from app.models.enums import LlmCallType
from app.services.llm_client import chat_structured

PROMPT_VERSION = "v1"

SYSTEM_PROMPT_V1 = """Bạn là chuyên gia schema mapping cho hệ thống Voice of Customer. \
Nhiệm vụ: với MỖI cột trong incoming_profiles, quyết định cách xử lý khi nạp vào \
product schema hiện có.

Mỗi cột trả về một decision:
- "MAP": cột chính là một field đã có trong existing_schema → điền `target` bằng key của field đó.
- "PROMOTE": cột là khái niệm phân tích MỚI, còn hợp lý nếu feedback đến từ nguồn khác cùng product \
(như app_version, country, device) → đề xuất field mới `candidate` {key (snake_case), label, type: category|numeric|datetime|text|boolean}.
- "SOURCE_META": cột chỉ meaningful trong nguồn gốc này (ticket_status, agent_name, response_id...) → lưu source metadata.
- "IGNORE": không có giá trị phân tích (row_number, debug_id...).
- "AMBIGUOUS": nghĩa không rõ (vd cột "score" — CSAT 1–5 hay NPS 0–10?) → cần human review, giải thích trong `reason`.

Ưu tiên MAP vào schema hiện có trước khi PROMOTE (import thứ N chỉ mở rộng khi \
là khái niệm thật sự mới). Core fields (feedback_text, occurred_at, source, \
source_record_id) là đích MAP đặc biệt — mọi CSV PHẢI có ít nhất một cột MAP vào \
feedback_text và một cột MAP vào occurred_at nếu cột thời gian tồn tại.

Với MỖI cột trả về: {source_field, decision, target?, candidate?, confidence [0..1], \
reason ≤2 câu, needs_human_review (true khi AMBIGUOUS hoặc confidence < 0.8)}.

Chỉ trả về JSON object khớp schema."""


class CandidateField(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,60}$")
    label: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=500)
    type: str = Field(pattern="^(category|numeric|datetime|text|boolean)$")


class MappingItem(BaseModel):
    source_field: str
    decision: str = Field(pattern="^(MAP|PROMOTE|SOURCE_META|IGNORE|AMBIGUOUS)$")
    target: str | None = None            # key field đích khi MAP (core hoặc product field)
    candidate: CandidateField | None = None  # khi PROMOTE
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=500)
    needs_human_review: bool = False


class MappingProposal(BaseModel):
    """Output tổng của một lượt map — persist vào imports.mapping_proposal."""

    mappings: list[MappingItem] = Field(min_length=1)

    def item_for(self, source_field: str) -> MappingItem | None:
        return next((m for m in self.mappings if m.source_field == source_field), None)


def build_mapping_proposal(
    existing_schema_fields: list[dict],
    incoming_profiles: list[dict],
) -> MappingProposal:
    """Gọi LLM với profiles (KHÔNG BAO GIỜ data raw) → MappingProposal."""
    import json

    user_payload = json.dumps(
        {
            "existing_schema": existing_schema_fields,
            "incoming_profiles": incoming_profiles,
        },
        ensure_ascii=False,
    )
    return chat_structured(
        SYSTEM_PROMPT_V1,
        user_payload,
        MappingProposal,
        call_type=LlmCallType.schema_map,
        prompt_version=PROMPT_VERSION,
    )
