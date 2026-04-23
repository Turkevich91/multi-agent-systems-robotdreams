from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Server

from agents.critic import run_critic
from agents.planner import run_planner
from agents.research import run_research
from config import settings


server = Server()


def _input_text(input_messages: list[Message]) -> str:
    if not input_messages:
        return ""
    parts = input_messages[-1].parts
    if not parts:
        return ""
    return str(parts[0].content or "")


def _message(content: str) -> Message:
    return Message(role="agent", parts=[MessagePart(content=content)])


@server.agent(
    name="planner",
    description="Creates structured ResearchPlan objects using SearchMCP tools.",
)
async def planner_handler(input: list[Message]) -> Message:
    return _message(await run_planner(_input_text(input)))


@server.agent(
    name="researcher",
    description="Executes research plans using SearchMCP web and knowledge tools.",
)
async def researcher_handler(input: list[Message]) -> Message:
    return _message(await run_research(_input_text(input)))


@server.agent(
    name="critic",
    description="Verifies findings and returns structured CritiqueResult objects.",
)
async def critic_handler(input: list[Message]) -> Message:
    return _message(await run_critic(_input_text(input)))


if __name__ == "__main__":
    print(f"ACP server running at {settings.acp_base_url}")
    server.run(host=settings.host, port=settings.acp_port)
