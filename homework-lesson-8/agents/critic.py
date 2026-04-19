import json
import re
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from config import CRITIC_PROMPT, build_chat_model, settings
from schemas import CritiqueResult
from tools import knowledge_search, read_url, web_search


def _last_message_text(result: dict) -> str:
    messages = result.get("messages", [])
    if not messages:
        return ""
    content = getattr(messages[-1], "content", "")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(block))
        return "\n".join(part for part in parts if part)
    return str(content)


critic_agent = create_agent(
    model=build_chat_model(),
    tools=[web_search, read_url, knowledge_search],
    system_prompt=CRITIC_PROMPT,
    response_format=ToolStrategy(CritiqueResult),
    name="critic_agent",
)


critic_fallback_agent = create_agent(
    model=build_chat_model(),
    tools=[web_search, read_url, knowledge_search],
    system_prompt=(
        CRITIC_PROMPT
        + "\nReturn ONLY one JSON object with exactly these keys: "
        "verdict, is_fresh, is_complete, is_well_structured, strengths, gaps, revision_requests. "
        "Do not wrap it in markdown fences."
    ),
    name="critic_fallback_agent",
)


def _json_from_text(text: str) -> dict[str, Any] | None:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)

    try:
        loaded = json.loads(clean)
        return loaded if isinstance(loaded, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
    if not match:
        return None

    try:
        loaded = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _normalize_payload(payload: dict[str, Any], raw_text: str) -> CritiqueResult:
    verdict = str(payload.get("verdict") or "REVISE").upper()
    if verdict not in {"APPROVE", "REVISE"}:
        verdict = "REVISE"

    default_bool = verdict == "APPROVE"
    strengths = _as_list(payload.get("strengths"))
    gaps = _as_list(payload.get("gaps"))
    revision_requests = _as_list(payload.get("revision_requests"))

    critique_text = payload.get("critique") or payload.get("reasoning") or payload.get("summary")
    if critique_text and not strengths and verdict == "APPROVE":
        strengths = [str(critique_text)]
    if critique_text and not gaps and verdict == "REVISE":
        gaps = [str(critique_text)]

    if verdict == "REVISE" and not revision_requests:
        revision_requests = ["Address the listed gaps and provide stronger source-backed findings."]

    return CritiqueResult(
        verdict=verdict,
        is_fresh=bool(payload.get("is_fresh", default_bool)),
        is_complete=bool(payload.get("is_complete", default_bool)),
        is_well_structured=bool(payload.get("is_well_structured", default_bool)),
        strengths=strengths,
        gaps=gaps,
        revision_requests=revision_requests,
    )


def _serialize_critique(result: CritiqueResult) -> str:
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)


def _prior_critique_count(runtime: ToolRuntime | None) -> int:
    if runtime is None:
        return 0

    state = getattr(runtime, "state", {}) or {}
    messages = state.get("messages", []) if isinstance(state, dict) else []
    return sum(
        1
        for message in messages
        if getattr(message, "type", None) == "tool" and getattr(message, "name", None) == "critique"
    )


@tool
def critique(findings: str, runtime: ToolRuntime = None) -> str:
    """Verify research findings and return a structured critique result."""
    prior_count = _prior_critique_count(runtime)
    if prior_count >= settings.max_revision_rounds:
        return _serialize_critique(
            CritiqueResult(
                verdict="APPROVE",
                is_fresh=True,
                is_complete=True,
                is_well_structured=True,
                strengths=[
                    "Revision limit reached. The best available findings are approved for final report writing."
                ],
                gaps=[],
                revision_requests=[],
            )
        )

    result = critic_agent.invoke(
        {"messages": [{"role": "user", "content": findings}]},
        config={"recursion_limit": 8},
    )
    structured = result.get("structured_response")
    if isinstance(structured, CritiqueResult):
        return _serialize_critique(structured)

    raw_response = _last_message_text(result)
    payload = _json_from_text(raw_response)
    if payload:
        return _serialize_critique(_normalize_payload(payload, raw_response))

    fallback = critic_fallback_agent.invoke(
        {"messages": [{"role": "user", "content": findings}]},
        config={"recursion_limit": 8},
    )
    fallback_text = _last_message_text(fallback)
    fallback_payload = _json_from_text(fallback_text)
    if fallback_payload:
        return _serialize_critique(_normalize_payload(fallback_payload, fallback_text))

    return _serialize_critique(
        CritiqueResult(
            verdict="REVISE",
            is_fresh=False,
            is_complete=False,
            is_well_structured=False,
            strengths=[],
            gaps=[
                "The Critic could not produce a validated structured review from the local model output.",
                f"Raw critic response: {raw_response or fallback_text or '[empty]'}",
            ],
            revision_requests=[
                "Re-run research with clearer source attribution and a more explicit structure."
            ],
        )
    )
