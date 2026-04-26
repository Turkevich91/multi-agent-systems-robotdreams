from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command
from pydantic import BaseModel, Field

from config import BASE_DIR, CURRENT_DATE, build_chat_model
from graph import market_graph
from observability import langfuse_observed_run
from schemas import CriteriaDecision, CriticRole


DEFAULT_REQUEST = (
    "Analyze the market for agentic AI developer tools for a small AEC/manufacturing software team. "
    "Compare coding agents, IDE copilots, observability/evaluation platforms, and MCP-based integrations. "
    "Recommend an adoption roadmap."
)


class CreateRunRequest(BaseModel):
    prompt: str | None = None


class CreateRunResponse(BaseModel):
    run_id: str
    status: str


class ResearchPromptSuggestion(BaseModel):
    prompt: str = Field(description="A ready-to-run market research prompt")
    rationale: str = Field(description="Why this topic is worth analyzing now")
    tags: list[str] = Field(default_factory=list)


class CriticSuggestionRequest(BaseModel):
    existing_roles: list[CriticRole] = Field(default_factory=list)


class CriticRoleSuggestion(BaseModel):
    role: CriticRole
    rationale: str = Field(description="Why this critic is useful for the original research prompt")
    tags: list[str] = Field(default_factory=list)


@dataclass
class RunRecord:
    run_id: str
    thread_id: str
    prompt: str
    config: dict
    queue: asyncio.Queue
    loop: asyncio.AbstractEventLoop
    status: str = "created"
    history: list[dict] = field(default_factory=list)
    pending_interrupt: dict | None = None
    approved_roles: list[dict] = field(default_factory=list)
    additional_criteria: list[str] = field(default_factory=list)
    trace_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def heartbeat(self) -> dict:
        return {
            "type": "heartbeat",
            "agent": "Backend",
            "message": f"Run status: {self.status}.",
            "payload": {
                "run_id": self.run_id,
                "status": self.status,
                "events": len(self.history),
                "updated_at": self.updated_at,
                "trace_id": self.trace_id,
            },
        }


RUNS: dict[str, RunRecord] = {}

PROMPT_GENERATOR_DOMAINS = [
    "mobile computer vision apps",
    "AI agents for back-office automation",
    "robotics software for small manufacturers",
    "construction-tech and AEC workflow automation",
    "privacy-preserving health AI tools",
    "cybersecurity tools for AI-enabled teams",
    "spatial computing and AR field-service apps",
    "industrial IoT analytics for factories",
    "vertical SaaS tools for compliance-heavy teams",
    "edge AI apps for smartphones and wearables",
]

PROMPT_GENERATOR_SYSTEM = """You generate one strong market-research prompt for a multi-agent Market Analyst.

Current date: {current_date}

The generated prompt will be pasted into a dashboard and executed immediately.
Choose a specific, timely market topic. The topic should feel current, commercially relevant and researchable from public sources.
Do not reuse the default course demo topic about agentic AI developer tooling unless the random seed explicitly asks for it.

Return a prompt that:
- asks for market analysis, not a generic essay
- names a concrete market or product category
- asks to compare solution categories, leading players or substitutes
- asks for adoption signals, risks, opportunities and a practical roadmap
- avoids private data and secrets
- is 1-2 sentences, direct and ready to run
"""

PROMPT_GENERATOR_FALLBACKS = [
    ResearchPromptSuggestion(
        prompt=(
            "Analyze the market for mobile computer-vision applications in 2026. Compare consumer, industrial, "
            "health, retail and creator-tool use cases, then recommend which themes look most demanded now."
        ),
        rationale="Mobile vision is broad enough for market analysis but specific enough for useful segmentation.",
        tags=["mobile", "computer-vision", "market-map"],
    ),
    ResearchPromptSuggestion(
        prompt=(
            "Analyze the market for edge AI applications on smartphones and wearables. Compare privacy, latency, "
            "battery, developer-platform and monetization tradeoffs, then recommend a practical adoption roadmap."
        ),
        rationale="Edge AI is timely because on-device models are changing app architecture and privacy positioning.",
        tags=["edge-ai", "mobile", "wearables"],
    ),
    ResearchPromptSuggestion(
        prompt=(
            "Analyze the market for AI-powered quality inspection tools for small manufacturing teams. Compare "
            "camera-based inspection, anomaly detection, robotics integration and no-code deployment platforms."
        ),
        rationale="Manufacturing AI is a strong fit for risk, ROI and implementation-readiness critique.",
        tags=["manufacturing", "computer-vision", "quality-inspection"],
    ),
]

CRITIC_GENERATOR_SYSTEM = """You suggest one additional expert critic role for a multi-agent market research workflow.

Current date: {current_date}

The critic must be based on the original user research prompt and must add a useful perspective that is not already covered by the existing critics.
Return one practical critic role with:
- a short role_id in snake_case
- a human-readable name ending with "Critic" when natural
- a focused one-sentence focus description
- 2-4 concrete criteria phrased as questions

Prefer critic perspectives that improve decision quality: market timing, buyer adoption, pricing/ROI, data quality, regulation, distribution, procurement, ecosystem risk, implementation feasibility, or defensibility.
Avoid generic grammar/style critics. Avoid duplicating existing roles.
"""

app = FastAPI(title="Course Project Market Analyst")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _emit(record: RunRecord, event: dict) -> None:
    event = dict(event)
    event.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
    record.history.append(event)
    record.updated_at = event["timestamp"]
    record.loop.call_soon_threadsafe(record.queue.put_nowait, event)


def _extract_interrupt_value(data: Any) -> dict | None:
    if not isinstance(data, dict) or "__interrupt__" not in data:
        return None
    raw = data.get("__interrupt__")
    interrupt_obj = raw[0] if isinstance(raw, (list, tuple)) and raw else raw
    return dict(getattr(interrupt_obj, "value", {}) or {})


def _fallback_prompt_suggestion() -> ResearchPromptSuggestion:
    return random.choice(PROMPT_GENERATOR_FALLBACKS)


def _slug(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
    return "_".join(part for part in slug.split("_") if part)


def _normalize_critic_suggestion(
    suggestion: CriticRoleSuggestion,
    existing_roles: list[CriticRole],
) -> CriticRoleSuggestion:
    existing_ids = {role.role_id for role in existing_roles}
    role = suggestion.role
    role_id = _slug(role.role_id or role.name) or "ai_suggested_critic"
    if role_id in existing_ids:
        role_id = f"ai_{role_id}"
    criteria = [criterion.strip() for criterion in role.criteria if criterion.strip()]
    if len(criteria) < 2:
        criteria.extend(
            [
                "Does the report cover the most decision-relevant uncertainty for this market?",
                "Does the recommendation explain how to validate this market assumption before scaling?",
            ]
        )
    normalized_role = CriticRole(
        role_id=role_id,
        name=role.name.strip() or "AI Suggested Critic",
        focus=role.focus.strip() or "Reviews the draft through the market uncertainty most relevant to the original prompt.",
        criteria=criteria[:4],
    )
    return CriticRoleSuggestion(
        role=normalized_role,
        rationale=suggestion.rationale.strip() or "This critic adds an extra perspective tailored to the original research prompt.",
        tags=[tag.strip() for tag in suggestion.tags if tag.strip()][:8],
    )


def _fallback_critic_suggestion(
    user_request: str,
    existing_roles: list[CriticRole],
) -> CriticRoleSuggestion:
    request = user_request.lower()
    if any(term in request for term in ["mobile", "vision", "computer vision", "camera", "edge"]):
        role = CriticRole(
            role_id="data_quality_device_constraints",
            name="Data Quality And Device Constraints Critic",
            focus="Checks whether market recommendations account for camera quality, model latency, edge inference and dataset constraints.",
            criteria=[
                "Does the report separate demand for mobile UX from demand for reliable model accuracy?",
                "Are camera quality, latency, battery and on-device privacy constraints considered?",
                "Does the report explain what data advantage or dataset access would make products defensible?",
            ],
        )
        rationale = "Computer-vision and mobile markets often fail on data quality, device constraints and reliability, not just demand."
        tags = ["computer-vision", "mobile", "data-quality"]
    elif any(term in request for term in ["health", "medical", "patient", "clinical"]):
        role = CriticRole(
            role_id="regulatory_clinical_adoption",
            name="Regulatory And Clinical Adoption Critic",
            focus="Checks whether the report accounts for compliance, clinical validation and workflow adoption risk.",
            criteria=[
                "Does the report distinguish wellness, clinical decision support and regulated medical-device use cases?",
                "Are validation, liability, procurement and clinician workflow barriers covered?",
                "Does the roadmap avoid scaling before regulatory and evidence requirements are clear?",
            ],
        )
        rationale = "Health-related markets need a critic that catches regulatory and clinical adoption assumptions."
        tags = ["health", "regulatory", "adoption"]
    elif any(term in request for term in ["enterprise", "procurement", "construction", "manufacturing", "industrial"]):
        role = CriticRole(
            role_id="procurement_change_management",
            name="Procurement And Change Management Critic",
            focus="Checks whether the recommendation fits enterprise buying cycles, implementation burden and stakeholder adoption.",
            criteria=[
                "Does the report identify who buys, who uses and who blocks adoption?",
                "Are implementation services, training and switching costs included in the recommendation?",
                "Does the roadmap match realistic procurement and rollout timelines?",
            ],
        )
        rationale = "Enterprise and industrial markets are often constrained by procurement and adoption friction more than product capability."
        tags = ["enterprise", "procurement", "change-management"]
    else:
        role = CriticRole(
            role_id="market_timing",
            name="Market Timing Critic",
            focus="Checks whether the report distinguishes durable demand from temporary hype or weak signals.",
            criteria=[
                "Does the report use current adoption signals rather than broad trend claims?",
                "Are leading indicators separated from speculative demand?",
                "Does the roadmap include a low-cost way to validate timing before committing budget?",
            ],
        )
        rationale = "A market timing critic is broadly useful when the requested market may be moving quickly or hype-driven."
        tags = ["market-timing", "adoption-signals", "validation"]

    return _normalize_critic_suggestion(CriticRoleSuggestion(role=role, rationale=rationale, tags=tags), existing_roles)


def _generate_critic_suggestion(user_request: str, existing_roles: list[CriticRole]) -> CriticRoleSuggestion:
    existing_roles_json = json.dumps([role.model_dump(mode="json") for role in existing_roles], ensure_ascii=False, indent=2)
    human_prompt = (
        f"Original user research prompt:\n{user_request}\n\n"
        f"Existing critics:\n{existing_roles_json}\n\n"
        "Suggest one additional expert critic that would materially improve this market analysis."
    )
    try:
        model = build_chat_model().with_structured_output(CriticRoleSuggestion)
        suggestion = model.invoke(
            [
                SystemMessage(content=CRITIC_GENERATOR_SYSTEM.format(current_date=CURRENT_DATE)),
                HumanMessage(content=human_prompt),
            ]
        )
        if not isinstance(suggestion, CriticRoleSuggestion):
            suggestion = CriticRoleSuggestion.model_validate(suggestion)
        return _normalize_critic_suggestion(suggestion, existing_roles)
    except Exception:
        return _fallback_critic_suggestion(user_request, existing_roles)


def _generate_prompt_suggestion() -> ResearchPromptSuggestion:
    domain = random.choice(PROMPT_GENERATOR_DOMAINS)
    angle = random.choice(
        [
            "fast-growing demand",
            "new AI capability becoming productized",
            "budget pressure and ROI scrutiny",
            "regulatory or privacy pressure",
            "mobile-first distribution",
            "enterprise adoption barriers",
            "small-team implementation readiness",
        ]
    )
    human_prompt = (
        f"Random seed domain: {domain}\n"
        f"Random seed angle: {angle}\n\n"
        "Generate one market-research prompt and a short rationale. "
        "Return structured output only."
    )
    try:
        model = build_chat_model().with_structured_output(ResearchPromptSuggestion)
        suggestion = model.invoke(
            [
                SystemMessage(content=PROMPT_GENERATOR_SYSTEM.format(current_date=CURRENT_DATE)),
                HumanMessage(content=human_prompt),
            ]
        )
        if not isinstance(suggestion, ResearchPromptSuggestion):
            suggestion = ResearchPromptSuggestion.model_validate(suggestion)
        if len(suggestion.prompt.strip()) < 24:
            raise ValueError("Generated prompt is too short.")
        return suggestion
    except Exception:
        return _fallback_prompt_suggestion()


def _run_graph_sync(record: RunRecord, payload: Any) -> None:
    record.status = "running"
    try:
        with langfuse_observed_run(record.prompt, record.thread_id) as lf_run:
            runtime_config = lf_run.with_callbacks(record.config)
            record.trace_id = lf_run.trace_id
            _emit(
                record,
                {
                    "type": "run_started",
                    "agent": "Backend",
                    "message": "Run started.",
                    "payload": {"trace_id": record.trace_id},
                },
            )

            for chunk in market_graph.stream(payload, config=runtime_config, stream_mode=["updates"], version="v2"):
                data = chunk.get("data") if isinstance(chunk, dict) and "data" in chunk else chunk
                interrupt_value = _extract_interrupt_value(data)
                if interrupt_value:
                    record.status = "awaiting_criteria"
                    record.pending_interrupt = interrupt_value
                    lf_run.output = {"status": "awaiting_criteria", "pending_interrupt": interrupt_value}
                    _emit(
                        record,
                        {
                            "type": "hitl_required",
                            "agent": "Human Criteria Gate",
                            "message": "Approve or edit expert critic roles before critique.",
                            "payload": interrupt_value,
                        },
                    )
                    return

                if not isinstance(data, dict):
                    continue
                for node_update in data.values():
                    if not isinstance(node_update, dict):
                        continue
                    for event in node_update.get("events", []):
                        _emit(record, _jsonable(event))

            record.status = "completed"
            final_state = market_graph.get_state(runtime_config).values
            lf_run.output = {
                "status": "completed",
                "final_report": _jsonable(final_state.get("final_report")),
                "events": _jsonable(final_state.get("events", [])),
            }
            _emit(
                record,
                {
                    "type": "run_completed",
                    "agent": "Backend",
                    "message": "Run completed.",
                    "payload": {
                        "trace_id": record.trace_id,
                        "final_report": _jsonable(final_state.get("final_report")),
                    },
                },
            )
    except Exception as exc:
        record.status = "failed"
        _emit(
            record,
            {
                "type": "run_failed",
                "agent": "Backend",
                "message": str(exc),
                "payload": {"error": repr(exc)},
            },
        )


def _start_graph_task(record: RunRecord, payload: Any) -> None:
    asyncio.create_task(asyncio.to_thread(_run_graph_sync, record, payload))


@app.post("/api/runs", response_model=CreateRunResponse)
async def create_run(request: CreateRunRequest) -> CreateRunResponse:
    prompt = (request.prompt or DEFAULT_REQUEST).strip() or DEFAULT_REQUEST
    run_id = uuid4().hex[:12]
    thread_id = str(uuid4())
    loop = asyncio.get_running_loop()
    record = RunRecord(
        run_id=run_id,
        thread_id=thread_id,
        prompt=prompt,
        config={"configurable": {"thread_id": thread_id}, "recursion_limit": 80},
        queue=asyncio.Queue(),
        loop=loop,
    )
    record.status = "running"
    RUNS[run_id] = record
    _start_graph_task(record, {"run_id": run_id, "user_request": prompt, "revision_round": 0, "events": []})
    return CreateRunResponse(run_id=run_id, status=record.status)


@app.get("/api/research-prompts/random", response_model=ResearchPromptSuggestion)
async def random_research_prompt() -> ResearchPromptSuggestion:
    return await asyncio.to_thread(_generate_prompt_suggestion)


@app.post("/api/runs/{run_id}/critic-roles/suggest", response_model=CriticRoleSuggestion)
async def suggest_critic_role(run_id: str, request: CriticSuggestionRequest) -> CriticRoleSuggestion:
    record = RUNS.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return await asyncio.to_thread(_generate_critic_suggestion, record.prompt, request.existing_roles)


@app.post("/api/runs/{run_id}/critic-criteria")
async def submit_critic_criteria(run_id: str, decision: CriteriaDecision) -> dict:
    record = RUNS.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if record.status not in {"awaiting_criteria", "completed"}:
        raise HTTPException(status_code=409, detail=f"Run cannot accept criteria; status={record.status}")

    is_regeneration = record.status == "completed"
    decision_payload = decision.model_dump(mode="json")
    record.pending_interrupt = None
    record.approved_roles = decision_payload["approved_roles"]
    record.additional_criteria = decision.additional_criteria
    record.status = "running"
    _emit(
        record,
        {
            "type": "hitl_submitted",
            "agent": "Human Criteria Gate",
            "message": (
                "Human criteria submitted for report regeneration."
                if is_regeneration
                else "Human criteria submitted."
            ),
            "payload": decision_payload,
        },
    )

    if is_regeneration:
        record.thread_id = str(uuid4())
        record.config = {"configurable": {"thread_id": record.thread_id}, "recursion_limit": 80}
        payload = {
            "run_id": run_id,
            "user_request": record.prompt,
            "revision_round": 0,
            "events": [],
            "approved_roles": decision_payload["approved_roles"],
            "additional_criteria": decision.additional_criteria,
        }
    else:
        payload = Command(resume=decision_payload)

    _start_graph_task(record, payload)
    return {"run_id": run_id, "status": "running"}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    record = RUNS.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    state = market_graph.get_state(record.config).values
    state_roles = _jsonable(state.get("approved_roles") or state.get("selected_roles") or [])
    critic_roles = (
        _jsonable(record.pending_interrupt.get("selected_roles", []))
        if record.pending_interrupt
        else state_roles or record.approved_roles
    )
    return {
        "run_id": run_id,
        "status": record.status,
        "prompt": record.prompt,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "pending_interrupt": record.pending_interrupt,
        "critic_roles": critic_roles,
        "approved_roles": record.approved_roles,
        "additional_criteria": record.additional_criteria,
        "trace_id": record.trace_id,
        "history": record.history,
        "state": _jsonable(state),
        "final_report": _jsonable(state.get("final_report")),
    }


def _sse(event: dict) -> str:
    event_type = str(event.get("type") or "message")
    return f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str) -> StreamingResponse:
    record = RUNS.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_stream():
        history_snapshot = list(record.history)
        if record.status == "running":
            history_snapshot = [
                item
                for item in history_snapshot
                if item.get("type") not in {"run_completed", "run_failed", "hitl_required"}
            ]
        elif record.status == "awaiting_criteria":
            history_snapshot = [
                item for item in history_snapshot if item.get("type") not in {"run_completed", "run_failed"}
            ]
        for index, item in enumerate(history_snapshot):
            yield _sse(item)
            is_latest = index == len(history_snapshot) - 1
            if item.get("type") in {"run_completed", "run_failed"} and is_latest and record.status in {"completed", "failed"}:
                return
        while True:
            try:
                item = await asyncio.wait_for(record.queue.get(), timeout=10.0)
            except asyncio.TimeoutError:
                yield _sse(record.heartbeat())
                continue
            yield _sse(item)
            if item.get("type") in {"run_completed", "run_failed"}:
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


frontend_dist = BASE_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    from config import settings

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
