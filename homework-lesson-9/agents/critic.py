import json

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from agents.common import as_str_list, json_from_text, last_message_text, load_search_tools
from config import CRITIC_PROMPT, build_chat_model
from schemas import CritiqueResult


def _normalize_payload(payload: dict, raw_text: str) -> CritiqueResult:
    verdict = str(payload.get("verdict") or "REVISE").upper()
    if verdict not in {"APPROVE", "REVISE"}:
        verdict = "REVISE"

    default_bool = verdict == "APPROVE"
    strengths = as_str_list(payload.get("strengths"))
    gaps = as_str_list(payload.get("gaps"))
    revision_requests = as_str_list(payload.get("revision_requests"))

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


async def run_critic(findings: str) -> str:
    client, tools = await load_search_tools({"web_search", "read_url", "knowledge_search"})
    try:
        critic_agent = create_agent(
            model=build_chat_model(),
            tools=tools,
            system_prompt=CRITIC_PROMPT,
            response_format=ToolStrategy(CritiqueResult),
            name="critic_agent",
        )
        result = await critic_agent.ainvoke(
            {"messages": [{"role": "user", "content": findings}]},
            config={"recursion_limit": 10},
        )
        structured = result.get("structured_response")
        if isinstance(structured, CritiqueResult):
            return _serialize_critique(structured)

        raw_response = last_message_text(result)
        payload = json_from_text(raw_response)
        if payload:
            return _serialize_critique(_normalize_payload(payload, raw_response))

        fallback_agent = create_agent(
            model=build_chat_model(),
            tools=tools,
            system_prompt=(
                CRITIC_PROMPT
                + "\nReturn ONLY one JSON object with exactly these keys: "
                "verdict, is_fresh, is_complete, is_well_structured, strengths, gaps, revision_requests. "
                "Do not wrap it in markdown fences."
            ),
            name="critic_fallback_agent",
        )
        fallback = await fallback_agent.ainvoke(
            {"messages": [{"role": "user", "content": findings}]},
            config={"recursion_limit": 10},
        )
        fallback_text = last_message_text(fallback)
        fallback_payload = json_from_text(fallback_text)
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
                    f"Raw critic response: {raw_response or '[empty]'}",
                ],
                revision_requests=[
                    "Re-run research with clearer source attribution and a more explicit structure."
                ],
            )
        )
    finally:
        await client.__aexit__(None, None, None)
