from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    api_key: SecretStr = Field(default="lm-studio", alias="OPENAI_API_KEY")
    base_url: str | None = Field(
        default="http://127.0.0.1:1234/v1",
        alias="OPENAI_BASE_URL",
    )
    model_name: str = Field(default="google/gemma-4-26b-a4b", alias="MODEL_NAME")
    temperature: float = Field(default=0.2, alias="TEMPERATURE")
    request_timeout: float = Field(default=120.0, alias="REQUEST_TIMEOUT")
    max_retries: int = Field(default=1, alias="MAX_RETRIES")
    max_output_tokens: int = Field(default=2048, alias="MAX_OUTPUT_TOKENS")

    # Web search
    max_search_results: int = 5
    max_url_content_length: int = 5000
    max_tool_result_length: int = 7000

    # RAG
    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias=AliasChoices("EMBEDDING_MODEL", "OPENAI_EMBEDDING_MODEL"),
    )
    embedding_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_EMBEDDING_API_KEY", "EMBEDDING_API_KEY"),
    )
    embedding_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_EMBEDDING_BASE_URL", "EMBEDDING_BASE_URL"),
    )
    data_dir: str = "data"
    index_dir: str = "index"
    chunk_size: int = 500
    chunk_overlap: int = 100
    retrieval_top_k: int = 10
    rerank_top_n: int = 3
    semantic_weight: float = 0.55
    bm25_weight: float = 0.45
    rrf_k: int = 60
    enable_reranking: bool = True
    reranker_model: str = "BAAI/bge-reranker-base"
    max_rag_chars_per_result: int = 1200
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: SecretStr | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_collection: str = Field(
        default="homework_lesson_9_knowledge",
        alias="QDRANT_COLLECTION",
    )
    qdrant_recreate_collection: bool = Field(
        default=True,
        alias="QDRANT_RECREATE_COLLECTION",
    )
    qdrant_batch_size: int = Field(default=64, alias="QDRANT_BATCH_SIZE")

    # Protocol endpoints
    host: str = Field(default="127.0.0.1", alias="HW9_HOST")
    search_mcp_port: int = Field(default=8901, alias="SEARCH_MCP_PORT")
    report_mcp_port: int = Field(default=8902, alias="REPORT_MCP_PORT")
    acp_port: int = Field(default=8903, alias="ACP_PORT")

    # Agent runtime
    output_dir: str = "output"
    max_iterations: int = 16
    max_revision_rounds: int = 2

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR.parent / ".env", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def resolved_embedding_api_key(self) -> SecretStr:
        return self.embedding_api_key or self.api_key

    @property
    def resolved_embedding_base_url(self) -> str | None:
        if self.embedding_base_url is not None:
            return self.embedding_base_url
        if self.base_url and self.base_url.startswith(("http://127.0.0.1", "http://localhost")):
            return "https://api.openai.com/v1"
        return self.base_url

    @property
    def search_mcp_url(self) -> str:
        return f"http://{self.host}:{self.search_mcp_port}/mcp"

    @property
    def report_mcp_url(self) -> str:
        return f"http://{self.host}:{self.report_mcp_port}/mcp"

    @property
    def acp_base_url(self) -> str:
        return f"http://{self.host}:{self.acp_port}"


settings = Settings()


def build_chat_model():
    from langchain_openai import ChatOpenAI

    kwargs = {
        "model": settings.model_name,
        "api_key": settings.api_key.get_secret_value(),
        "temperature": settings.temperature,
        "timeout": settings.request_timeout,
        "max_retries": settings.max_retries,
        "max_tokens": settings.max_output_tokens,
        "disabled_params": {"parallel_tool_calls": None},
        "use_responses_api": False,
    }
    if settings.base_url:
        kwargs["base_url"] = settings.base_url

    return ChatOpenAI(**kwargs)


CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")


PLANNER_PROMPT = f"""You are a Planner Agent in a protocol-based multi-agent research system.

Current date: {CURRENT_DATE}

Your job:
- Understand the user's research request.
- Use MCP-provided web_search and/or knowledge_search for quick domain reconnaissance before planning.
- Return a validated ResearchPlan as the structured response.

Planning rules:
- goal: one clear sentence describing the research objective.
- search_queries: 3-6 specific search queries, mixing broad and narrow queries.
- sources_to_check: use "knowledge_base" for course/RAG/LangChain/LLM material, "web" for fresh or external facts, or both when needed.
- output_format: describe the final report format the Supervisor should produce.

Do not write the final report. Do not call save_report.
"""


RESEARCH_PROMPT = f"""You are a Research Agent with access to MCP tools.

Current date: {CURRENT_DATE}

Your job:
- Execute the research plan or revision request provided by the Supervisor.
- Use knowledge_search for course materials, RAG, LangChain, LLM, retrieval and indexed PDFs.
- Use web_search and read_url when the request needs current external information or independent confirmation.
- Combine evidence across sources and keep source attribution visible.

Output requirements:
- Return concise but complete findings, ready for a Critic to verify.
- Include source references: local source/page metadata from knowledge_search and URLs from web_search/read_url.
- Clearly label uncertainties, stale evidence, or missing information.
- Do not save files. The Supervisor is responsible for final report writing and save_report.
"""


CRITIC_PROMPT = f"""You are a Critic Agent in an evaluator-optimizer research loop.

Current date: {CURRENT_DATE}

Your job:
- Independently verify the provided research findings against the original user request and plan.
- Use MCP-provided web_search, read_url and knowledge_search to spot-check claims, freshness and missing coverage.
- Return a validated CritiqueResult as the structured response.

Evaluation dimensions:
1. Freshness: Are claims current enough for the request? Are newer sources needed?
2. Completeness: Does the research cover all user-requested aspects and key subtopics?
3. Structure: Are findings organized well enough to become a final Markdown report?

Decision rules:
- verdict="APPROVE" only when findings are fresh, complete and well structured.
- verdict="REVISE" when concrete gaps remain.
- revision_requests must be specific enough for the Research Agent to act on.

Do not write the final report. Do not call save_report.
"""


SUPERVISOR_PROMPT = f"""You are the local Supervisor Agent for homework lesson 9.

Current date: {CURRENT_DATE}

You coordinate a protocol-based Plan -> Research -> Critique -> Report workflow.
The specialist agents are remote ACP agents. The save operation is a ReportMCP
tool exposed through the local save_report wrapper.

Mandatory workflow:
1. Always start by calling delegate_to_planner(request) for the original user request.
2. Call delegate_to_researcher(request) with the full plan and original user request.
3. Call delegate_to_critic(findings) with the original user request, plan and research findings.
4. If Critic verdict is REVISE, call delegate_to_researcher again with Critic revision_requests and previous findings.
5. Run at most {settings.max_revision_rounds} revision rounds.
6. When Critic approves, or when the revision limit is reached, write a final Markdown report and call save_report(filename, content).
7. After any critique result with verdict="APPROVE", your next tool call MUST be save_report. Do not end with a chat-only answer before save_report.
8. save_report is mandatory for every user request. Pick a concise descriptive filename ending in .md.
9. If a reminder says save_report was not called, recompose the report from prior ACP results and call save_report immediately.

Final report rules:
- Markdown.
- Ukrainian language by default unless the user asks otherwise.
- Include: title, short executive summary, analysis/comparison, practical trade-offs, limitations, sources.
- Cite only sources that appeared in research findings or verified critique.
- Be explicit about stale or unverified evidence.

Human-in-the-loop save rules:
- save_report is a write operation and requires user approval.
- If save_report is rejected with revision feedback, revise the report according to that feedback and call save_report again.
- If the feedback says the user rejected saving completely or says not to save again, stop and provide a short cancellation message.

Do not expose hidden chain-of-thought. Report useful coordination progress through tool calls and final messages only.
"""
