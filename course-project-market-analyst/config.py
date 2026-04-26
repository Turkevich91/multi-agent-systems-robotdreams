from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")


class Settings(BaseSettings):
    api_key: SecretStr = Field(default=SecretStr(""), alias="OPENAI_API_KEY")
    base_url: str | None = Field(
        default="https://api.openai.com/v1",
        alias="COURSE_PROJECT_OPENAI_BASE_URL",
    )
    model_name: str = Field(
        default="gpt-5.4-mini",
        validation_alias=AliasChoices("COURSE_PROJECT_MODEL_NAME", "EVAL_MODEL"),
    )
    temperature: float = Field(default=0.2, alias="COURSE_PROJECT_TEMPERATURE")
    request_timeout: float = Field(default=120.0, alias="REQUEST_TIMEOUT")
    max_retries: int = Field(default=1, alias="MAX_RETRIES")
    max_output_tokens: int = Field(default=4096, alias="COURSE_PROJECT_MAX_OUTPUT_TOKENS")

    # Web and tool limits
    max_search_results: int = Field(default=5, alias="COURSE_PROJECT_MAX_SEARCH_RESULTS")
    max_url_content_length: int = Field(default=6000, alias="COURSE_PROJECT_MAX_URL_CONTENT_LENGTH")
    max_tool_result_length: int = Field(default=8000, alias="COURSE_PROJECT_MAX_TOOL_RESULT_LENGTH")

    # RAG
    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias=AliasChoices("OPENAI_EMBEDDING_MODEL", "EMBEDDING_MODEL"),
    )
    embedding_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_EMBEDDING_API_KEY", "EMBEDDING_API_KEY"),
    )
    embedding_base_url: str | None = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("OPENAI_EMBEDDING_BASE_URL", "EMBEDDING_BASE_URL"),
    )
    data_dir: str = Field(default="data", alias="COURSE_PROJECT_DATA_DIR")
    index_dir: str = Field(default="index", alias="COURSE_PROJECT_INDEX_DIR")
    chunk_size: int = Field(default=700, alias="COURSE_PROJECT_CHUNK_SIZE")
    chunk_overlap: int = Field(default=120, alias="COURSE_PROJECT_CHUNK_OVERLAP")
    retrieval_top_k: int = Field(default=10, alias="COURSE_PROJECT_RETRIEVAL_TOP_K")
    rerank_top_n: int = Field(default=4, alias="COURSE_PROJECT_RERANK_TOP_N")
    semantic_weight: float = Field(default=0.55, alias="COURSE_PROJECT_SEMANTIC_WEIGHT")
    bm25_weight: float = Field(default=0.45, alias="COURSE_PROJECT_BM25_WEIGHT")
    rrf_k: int = Field(default=60, alias="COURSE_PROJECT_RRF_K")
    enable_reranking: bool = Field(default=True, alias="COURSE_PROJECT_ENABLE_RERANKING")
    reranker_model: str = Field(default="BAAI/bge-reranker-base", alias="COURSE_PROJECT_RERANKER_MODEL")
    max_rag_chars_per_result: int = Field(default=1400, alias="COURSE_PROJECT_MAX_RAG_CHARS")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: SecretStr | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_collection: str = Field(
        default="course_project_market_analyst_knowledge",
        alias="COURSE_PROJECT_QDRANT_COLLECTION",
    )
    qdrant_recreate_collection: bool = Field(default=True, alias="QDRANT_RECREATE_COLLECTION")
    qdrant_batch_size: int = Field(default=64, alias="QDRANT_BATCH_SIZE")

    # Runtime
    output_dir: str = Field(default="output", alias="COURSE_PROJECT_OUTPUT_DIR")
    max_revision_rounds: int = Field(default=3, alias="COURSE_PROJECT_MAX_REVISION_ROUNDS")
    default_critic_role_ids: str = Field(
        default="financial,risk",
        alias="COURSE_PROJECT_DEFAULT_CRITIC_ROLES",
    )

    # Optional MCP
    tool_backend: str = Field(default="mcp_auto", alias="COURSE_PROJECT_TOOL_BACKEND")
    host: str = Field(default="127.0.0.1", alias="COURSE_PROJECT_HOST")
    search_mcp_port: int = Field(default=8911, alias="COURSE_PROJECT_SEARCH_MCP_PORT")
    search_mcp_url: str | None = Field(default=None, alias="COURSE_PROJECT_SEARCH_MCP_URL")

    # Backend
    api_host: str = Field(default="127.0.0.1", alias="COURSE_PROJECT_API_HOST")
    api_port: int = Field(default=8012, alias="COURSE_PROJECT_API_PORT")

    # Langfuse
    langfuse_public_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("CW_LANGFUSE_PUBLIC_KEY", "LANGFUSE_PUBLIC_KEY"),
    )
    langfuse_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("CW_LANGFUSE_SECRET_KEY", "LANGFUSE_SECRET_KEY"),
    )
    langfuse_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CW_LANGFUSE_BASE_URL", "LANGFUSE_BASE_URL", "LANGFUSE_HOST"),
    )
    langfuse_prompt_label: str = Field(default="production", alias="LANGFUSE_PROMPT_LABEL")
    langfuse_prompt_cache_ttl_seconds: int = Field(default=60, alias="LANGFUSE_PROMPT_CACHE_TTL_SECONDS")
    langfuse_trace_name: str = Field(
        default="course-project-market-analyst",
        alias="COURSE_PROJECT_LANGFUSE_TRACE_NAME",
    )
    langfuse_session_id: str = Field(
        default="course-project-final-session",
        alias="COURSE_PROJECT_LANGFUSE_SESSION_ID",
    )
    langfuse_user_id: str = Field(default="vetal", alias="LANGFUSE_USER_ID")
    langfuse_tags: str = Field(
        default="course-project,market-analyst,langgraph,rag,mcp,langfuse",
        alias="COURSE_PROJECT_LANGFUSE_TAGS",
    )

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR.parent / ".env", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def resolved_search_mcp_url(self) -> str:
        return self.search_mcp_url or f"http://{self.host}:{self.search_mcp_port}/mcp"

    @property
    def resolved_embedding_api_key(self) -> SecretStr:
        if self.embedding_api_key:
            return self.embedding_api_key
        return self.api_key

    @property
    def resolved_embedding_base_url(self) -> str | None:
        return self.embedding_base_url

    @property
    def default_critic_roles(self) -> list[str]:
        return [item.strip() for item in self.default_critic_role_ids.split(",") if item.strip()]

    @property
    def langfuse_tag_list(self) -> list[str]:
        return [tag.strip() for tag in self.langfuse_tags.split(",") if tag.strip()]


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


def sync_langfuse_environment() -> None:
    if settings.langfuse_public_key:
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key.get_secret_value()
    if settings.langfuse_secret_key:
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key.get_secret_value()
    if settings.langfuse_base_url:
        os.environ["LANGFUSE_BASE_URL"] = settings.langfuse_base_url
        os.environ["LANGFUSE_HOST"] = settings.langfuse_base_url
