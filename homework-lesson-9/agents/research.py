from langchain.agents import create_agent

from agents.common import last_message_text, load_search_tools
from config import RESEARCH_PROMPT, build_chat_model


async def run_research(request: str) -> str:
    client, tools = await load_search_tools({"web_search", "read_url", "knowledge_search"})
    try:
        research_agent = create_agent(
            model=build_chat_model(),
            tools=tools,
            system_prompt=RESEARCH_PROMPT,
            name="research_agent",
        )
        result = await research_agent.ainvoke(
            {"messages": [{"role": "user", "content": request}]},
            config={"recursion_limit": 12},
        )
        return last_message_text(result)
    finally:
        await client.__aexit__(None, None, None)
