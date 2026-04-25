from langchain.agents import create_agent
from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from config import build_chat_model
from prompt_registry import load_system_prompt
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


research_agent = create_agent(
    model=build_chat_model(),
    tools=[web_search, read_url, knowledge_search],
    system_prompt=load_system_prompt("researcher"),
    name="research_agent",
)


def _runtime_config(runtime: ToolRuntime | None) -> dict | None:
    config = getattr(runtime, "config", None)
    return dict(config) if isinstance(config, dict) else None


@tool
def research(request: str, runtime: ToolRuntime = None) -> str:
    """Execute research using web search, URL reading and local knowledge search."""
    result = research_agent.invoke(
        {"messages": [{"role": "user", "content": request}]},
        config=_runtime_config(runtime),
    )
    return _last_message_text(result)
