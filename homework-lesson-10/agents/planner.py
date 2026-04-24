import json
import re
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import tool

from config import PLANNER_PROMPT, build_chat_model
from schemas import ResearchPlan
from tools import knowledge_search, web_search


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


planner_agent = create_agent(
    model=build_chat_model(),
    tools=[web_search, knowledge_search],
    system_prompt=PLANNER_PROMPT,
    response_format=ToolStrategy(ResearchPlan),
    name="planner_agent",
)


planner_fallback_agent = create_agent(
    model=build_chat_model(),
    tools=[web_search, knowledge_search],
    system_prompt=(
        PLANNER_PROMPT
        + "\nReturn ONLY one JSON object with exactly these keys: "
        "goal, search_queries, sources_to_check, output_format. "
        "sources_to_check must contain knowledge_base, web, or both values. "
        "Do not wrap it in markdown fences."
    ),
    name="planner_fallback_agent",
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


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _normalize_payload(payload: dict[str, Any], request: str) -> ResearchPlan:
    queries = _as_str_list(payload.get("search_queries"))
    if not queries:
        queries = [request, f"{request} sources", f"{request} comparison"]

    sources = _as_str_list(payload.get("sources_to_check"))
    normalized_sources: list[str] = []
    for source in sources:
        lowered = source.lower()
        if "both" in lowered:
            normalized_sources.extend(["knowledge_base", "web"])
        elif "knowledge" in lowered:
            normalized_sources.append("knowledge_base")
        elif "web" in lowered:
            normalized_sources.append("web")

    if not normalized_sources:
        normalized_sources = ["knowledge_base", "web"]

    deduped_sources = list(dict.fromkeys(normalized_sources))

    return ResearchPlan(
        goal=str(payload.get("goal") or request).strip(),
        search_queries=queries,
        sources_to_check=deduped_sources,
        output_format=str(
            payload.get("output_format")
            or "Markdown report with summary, analysis, trade-offs, limitations, and sources."
        ).strip(),
    )


def _serialize_plan(result: ResearchPlan) -> str:
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)


@tool
def plan(request: str) -> str:
    """Create a structured research plan for the user's request."""
    result = planner_agent.invoke(
        {"messages": [{"role": "user", "content": request}]},
        config={"recursion_limit": 8},
    )
    structured = result.get("structured_response")
    if isinstance(structured, ResearchPlan):
        return _serialize_plan(structured)

    raw_response = _last_message_text(result)
    payload = _json_from_text(raw_response)
    if payload:
        return _serialize_plan(_normalize_payload(payload, request))

    fallback = planner_fallback_agent.invoke(
        {"messages": [{"role": "user", "content": request}]},
        config={"recursion_limit": 8},
    )
    fallback_text = _last_message_text(fallback)
    fallback_payload = _json_from_text(fallback_text)
    if fallback_payload:
        return _serialize_plan(_normalize_payload(fallback_payload, request))

    return _serialize_plan(
        ResearchPlan(
            goal=request,
            search_queries=[request, f"{request} sources", f"{request} comparison"],
            sources_to_check=["knowledge_base", "web"],
            output_format="Markdown report with summary, analysis, trade-offs, limitations, and sources.",
        )
    )
