"""Bounded ACT reasoning drafts and immutable, server-grounded snapshots."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Lens = Literal["product", "discovery", "engineering", "ux", "risk", "customer_success", "finance"]
ActionKind = Literal["mitigate", "improve", "investigate"]
ShortText = Annotated[str, Field(min_length=1, max_length=400)]


def require_schema_properties(schema: dict) -> None:
    """Strict providers require nullable properties to be present, too.

    Keep Python-side defaults for existing fixtures and legacy API compatibility;
    the LLM schema requires explicit nulls rather than omitted properties.
    """
    schema["required"] = list(schema.get("properties", {}))
    for prop in schema.get("properties", {}).values():
        prop.pop("default", None)


class SupportModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True,
        json_schema_extra=require_schema_properties,
    )


class Perspective(SupportModel):
    lens: Lens
    assessment: ShortText


class PracticeApplication(SupportModel):
    card_id: str = Field(min_length=1, max_length=60)
    application: ShortText


class Alternative(SupportModel):
    recommendation: ShortText
    tradeoff: ShortText


class DecisionSupportDraft(SupportModel):
    kind: ActionKind
    evidence_ids: list[UUID] = Field(max_length=10)
    perspectives: list[Perspective] = Field(min_length=2, max_length=3)
    references: list[PracticeApplication] = Field(
        max_length=3,
        description="Apply matching cards from best_practices, including to investigations without internal evidence. Empty only if no library principle applies.",
    )
    source_gap: ShortText | None = Field(
        default=None,
        description="External guidance library limitation only. Never describe missing internal evidence, telemetry, baseline or cost data here. Null when selected principles cover the approach.",
    )
    alternative: Alternative
    tradeoff: ShortText
    assumptions: list[ShortText] = Field(min_length=1, max_length=3)
    success_criteria: str = Field(min_length=1, max_length=600)
    estimate_basis: ShortText

    @model_validator(mode="after")
    def distinct_and_explicit(self):
        if len({p.lens for p in self.perspectives}) != len(self.perspectives):
            raise ValueError("Perspectives must use distinct lenses")
        if len({r.card_id for r in self.references}) != len(self.references):
            raise ValueError("Practice references must be distinct")
        if not self.references and not self.source_gap:
            raise ValueError("Missing references require an explicit source_gap")
        return self


class ActionEvidence(SupportModel):
    evidence_id: UUID
    statement: str
    source_tool: str


class PracticeReference(PracticeApplication):
    lens: Lens
    source_title: str
    url: str
    section: str
    principle: str
    applies_when: str
    limitations: str
    reviewed_on: str


class ActionDecisionSupport(SupportModel):
    library_version: str
    basis_recommendation: str
    basis_rationale: str
    kind: ActionKind
    evidence: list[ActionEvidence]
    perspectives: list[Perspective]
    references: list[PracticeReference]
    source_gap: str | None
    alternative: Alternative
    tradeoff: str
    assumptions: list[str]
    success_criteria: str
    estimate_basis: str
