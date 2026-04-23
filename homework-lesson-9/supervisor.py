import asyncio
from typing import Any

from acp_sdk.client import Client as ACPClient
from acp_sdk.models import Message, MessagePart
from fastmcp import Client as MCPClient
from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from config import SUPERVISOR_PROMPT, build_chat_model, settings
from mcp_utils import mcp_result_to_text


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("Synchronous supervisor tools cannot run inside an active event loop.")


def _run_output_text(run: Any) -> str:
    output = getattr(run, "output", []) or []
    if not output:
        return ""
    parts = getattr(output[-1], "parts", []) or []
    if not parts:
        return ""
    return str(parts[0].content or "")


async def _call_acp(agent_name: str, content: str) -> str:
    async with ACPClient(
        base_url=settings.acp_base_url,
        headers={"Content-Type": "application/json"},
        timeout=settings.request_timeout,
    ) as client:
        run = await client.run_sync(
            agent=agent_name,
            input=[Message(role="user", parts=[MessagePart(content=content)])],
        )
    return _run_output_text(run)


async def _call_report_mcp(filename: str, content: str) -> str:
    async with MCPClient(settings.report_mcp_url) as client:
        result = await client.call_tool(
            "save_report",
            {"filename": filename, "content": content},
        )
    return mcp_result_to_text(result)


@tool
def delegate_to_planner(request: str) -> str:
    """Delegate the original user request to the Planner ACP agent."""
    return _run_async(_call_acp("planner", request))


@tool
def delegate_to_researcher(request: str) -> str:
    """Delegate a plan or revision request to the Researcher ACP agent."""
    return _run_async(_call_acp("researcher", request))


@tool
def delegate_to_critic(findings: str) -> str:
    """Delegate research findings to the Critic ACP agent."""
    return _run_async(_call_acp("critic", findings))


@tool
def save_report(filename: str, content: str) -> str:
    """Save the final Markdown report through ReportMCP."""
    return _run_async(_call_report_mcp(filename, content))


memory = InMemorySaver()


supervisor = create_agent(
    model=build_chat_model(),
    tools=[delegate_to_planner, delegate_to_researcher, delegate_to_critic, save_report],
    system_prompt=SUPERVISOR_PROMPT,
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={"save_report": True},
            description_prefix="ReportMCP save pending approval",
        ),
        ToolCallLimitMiddleware(
            run_limit=settings.max_iterations,
            exit_behavior="continue",
        ),
        ModelCallLimitMiddleware(
            run_limit=settings.max_iterations + 4,
            exit_behavior="end",
        ),
    ],
    checkpointer=memory,
    name="protocol_supervisor",
)
