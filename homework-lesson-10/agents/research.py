from langchain.agents import create_agent
from langchain_core.tools import tool

from config import RESEARCH_PROMPT, build_chat_model
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
    system_prompt=RESEARCH_PROMPT,
    name="research_agent",
)


@tool
def research(request: str) -> str:
    """Execute research using web search, URL reading and local knowledge search."""
    result = research_agent.invoke({"messages": [{"role": "user", "content": request}]})
    return _last_message_text(result)
