from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from config import SYSTEM_PROMPT, settings
from tools import read_url, web_search, write_report


llm = ChatOpenAI(
    model=settings.model_name,
    base_url=settings.base_url,
    api_key=settings.api_key.get_secret_value(),
    temperature=settings.temperature,
    timeout=settings.request_timeout,
    max_retries=settings.max_retries,
    disabled_params={"parallel_tool_calls": None},
    use_responses_api=False,
)

tools = [web_search, read_url, write_report]

memory = InMemorySaver()

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=memory,
    middleware=[
        ToolCallLimitMiddleware(
            run_limit=settings.max_iterations,
            exit_behavior="continue",
        ),
        ModelCallLimitMiddleware(
            run_limit=settings.max_iterations + 2,
            exit_behavior="end",
        ),
    ],
)
