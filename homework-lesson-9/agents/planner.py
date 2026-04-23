import json

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from agents.common import as_str_list, json_from_text, last_message_text, load_search_tools
from config import PLANNER_PROMPT, build_chat_model
from schemas import ResearchPlan


def _normalize_payload(payload: dict, request: str) -> ResearchPlan:
    queries = as_str_list(payload.get("search_queries"))
    if not queries:
        queries = [request, f"{request} sources", f"{request} comparison"]

    sources = as_str_list(payload.get("sources_to_check"))
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

    return ResearchPlan(
        goal=str(payload.get("goal") or request).strip(),
        search_queries=queries,
        sources_to_check=list(dict.fromkeys(normalized_sources)),
        output_format=str(
            payload.get("output_format")
            or "Markdown report with summary, analysis, trade-offs, limitations, and sources."
        ).strip(),
    )


def _serialize_plan(result: ResearchPlan) -> str:
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)


async def run_planner(request: str) -> str:
    client, tools = await load_search_tools({"web_search", "knowledge_search"})
    try:
        planner_agent = create_agent(
            model=build_chat_model(),
            tools=tools,
            system_prompt=PLANNER_PROMPT,
            response_format=ToolStrategy(ResearchPlan),
            name="planner_agent",
        )
        result = await planner_agent.ainvoke(
            {"messages": [{"role": "user", "content": request}]},
            config={"recursion_limit": 8},
        )
        structured = result.get("structured_response")
        if isinstance(structured, ResearchPlan):
            return _serialize_plan(structured)

        payload = json_from_text(last_message_text(result))
        if payload:
            return _serialize_plan(_normalize_payload(payload, request))

        fallback_agent = create_agent(
            model=build_chat_model(),
            tools=tools,
            system_prompt=(
                PLANNER_PROMPT
                + "\nReturn ONLY one JSON object with exactly these keys: "
                "goal, search_queries, sources_to_check, output_format. "
                "Do not wrap it in markdown fences."
            ),
            name="planner_fallback_agent",
        )
        fallback = await fallback_agent.ainvoke(
            {"messages": [{"role": "user", "content": request}]},
            config={"recursion_limit": 8},
        )
        fallback_payload = json_from_text(last_message_text(fallback))
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
    finally:
        await client.__aexit__(None, None, None)
