from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")


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
        default="homework_lesson_12_knowledge",
        alias="QDRANT_COLLECTION",
    )
    qdrant_recreate_collection: bool = Field(
        default=True,
        alias="QDRANT_RECREATE_COLLECTION",
    )
    qdrant_batch_size: int = Field(default=64, alias="QDRANT_BATCH_SIZE")

    # Agent runtime
    output_dir: str = "output"
    max_iterations: int = 14
    max_revision_rounds: int = 2

    # Langfuse
    langfuse_public_key: SecretStr | None = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: SecretStr | None = Field(default=None, alias="LANGFUSE_SECRET_KEY")
    langfuse_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_BASE_URL", "LANGFUSE_HOST"),
    )
    langfuse_prompt_label: str = Field(default="production", alias="LANGFUSE_PROMPT_LABEL")
    langfuse_prompt_cache_ttl_seconds: int = Field(
        default=60,
        alias="LANGFUSE_PROMPT_CACHE_TTL_SECONDS",
    )
    langfuse_trace_name: str = Field(
        default="homework-12-multi-agent-research",
        alias="LANGFUSE_TRACE_NAME",
    )
    langfuse_session_id: str = Field(
        default="homework-12-review-session",
        alias="LANGFUSE_SESSION_ID",
    )
    langfuse_user_id: str = Field(default="vetal", alias="LANGFUSE_USER_ID")
    langfuse_tags: str = Field(
        default="homework-12,multi-agent,langfuse,rag",
        alias="LANGFUSE_TAGS",
    )

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
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key.get_secret_value())
    if settings.langfuse_secret_key:
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key.get_secret_value())
    if settings.langfuse_base_url:
        os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_base_url)
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_base_url)
