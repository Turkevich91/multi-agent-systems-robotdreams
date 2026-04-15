from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from config import SYSTEM_PROMPT, settings
from tools import knowledge_search, read_url, web_search, write_report


llm_kwargs = {
    "model": settings.model_name,
    "api_key": settings.api_key.get_secret_value(),
    "temperature": settings.temperature,
    "timeout": settings.request_timeout,
    "max_retries": settings.max_retries,
    "disabled_params": {"parallel_tool_calls": None},
    "use_responses_api": False,
}
if settings.base_url:
    llm_kwargs["base_url"] = settings.base_url

llm = ChatOpenAI(**llm_kwargs)

tools = [knowledge_search, web_search, read_url, write_report]

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
