from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langgraph.checkpoint.memory import InMemorySaver

from agents.critic import critique
from agents.planner import plan
from agents.research import research
from config import SUPERVISOR_PROMPT, build_chat_model, settings
from tools import save_report


memory = InMemorySaver()


supervisor = create_agent(
    model=build_chat_model(),
    tools=[plan, research, critique, save_report],
    system_prompt=SUPERVISOR_PROMPT,
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={"save_report": True},
            description_prefix="Report save pending approval",
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
    name="supervisor",
)
