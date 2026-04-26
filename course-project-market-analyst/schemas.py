from __future__ import annotations

from operator import add
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    title: str
    source: str = Field(description="URL or local source name")
    evidence: str = Field(description="Short reason this source matters")
    source_type: Literal["web", "knowledge_base", "manual_note"] = "web"


class MarketSegment(BaseModel):
    name: str
    description: str
    relevant_tools: list[str]
    adoption_signal: str


class ToolAssessment(BaseModel):
    name: str
    category: str
    strengths: list[str]
    limitations: list[str]
    fit_for_target_context: str
    sources: list[str] = Field(description="Source titles or URLs used for this assessment")


class DraftReport(BaseModel):
    title: str
    executive_summary: str
    market_segments: list[MarketSegment]
    tool_assessments: list[ToolAssessment]
    adoption_drivers: list[str]
    risks: list[str]
    opportunities: list[str]
    open_questions: list[str]
    sources: list[SourceRef]
    revision_notes: list[str] = Field(default_factory=list)


class CriticRole(BaseModel):
    role_id: str
    name: str
    focus: str
    criteria: list[str]


class CriteriaDecision(BaseModel):
    approved_roles: list[CriticRole]
    additional_criteria: list[str] = Field(default_factory=list)


class ExpertCritique(BaseModel):
    role_id: str
    role_name: str
    verdict: Literal["APPROVED", "NEEDS_REVISION"]
    score: float = Field(ge=0.0, le=1.0)
    strengths: list[str]
    issues: list[str]
    source_gaps: list[str]
    recommendations: list[str]


class AggregatedCritique(BaseModel):
    verdict: Literal["APPROVED", "NEEDS_REVISION"]
    score: float = Field(ge=0.0, le=1.0)
    summary: str
    revision_requests: list[str]
    expert_feedback: list[ExpertCritique]


class MermaidDiagram(BaseModel):
    title: str
    kind: Literal[
        "market_entry",
        "payback",
        "timeline",
        "saturation",
        "score_pie",
        "risk_flow",
        "roadmap",
        "matrix",
        "architecture",
    ]
    mermaid: str


class FinalReport(BaseModel):
    title: str
    markdown: str
    diagrams: list[MermaidDiagram]
    sources: list[SourceRef]
    saved_path: str | None = None


class RunEvent(BaseModel):
    type: str
    agent: str
    message: str
    payload: dict = Field(default_factory=dict)


class MarketState(TypedDict, total=False):
    run_id: str
    user_request: str
    revision_round: int
    draft: DraftReport
    selected_roles: list[dict[str, Any]]
    approved_roles: list[dict[str, Any]]
    additional_criteria: list[str]
    expert_critiques: list[ExpertCritique]
    aggregated_critique: AggregatedCritique
    final_report: FinalReport
    trace_id: str | None
    events: Annotated[list[dict], add]
