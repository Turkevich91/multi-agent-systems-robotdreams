from __future__ import annotations

from functools import lru_cache

from config import CURRENT_DATE, settings, sync_langfuse_environment


PROMPT_NAMES = {
    "planner": "hw12_planner_system",
    "planner_fallback": "hw12_planner_fallback_system",
    "researcher": "hw12_researcher_system",
    "critic": "hw12_critic_system",
    "critic_fallback": "hw12_critic_fallback_system",
    "supervisor": "hw12_supervisor_system",
}


class PromptLoadError(RuntimeError):
    pass


def _prompt_variables() -> dict[str, str | int]:
    return {
        "current_date": CURRENT_DATE,
        "max_revision_rounds": settings.max_revision_rounds,
    }


@lru_cache(maxsize=None)
def load_system_prompt(role: str) -> str:
    prompt_name = PROMPT_NAMES[role]
    sync_langfuse_environment()

    try:
        from langfuse import get_client

        client = get_client()
        prompt = client.get_prompt(
            prompt_name,
            label=settings.langfuse_prompt_label,
            cache_ttl_seconds=settings.langfuse_prompt_cache_ttl_seconds,
        )
        compiled = prompt.compile(**_prompt_variables())
    except Exception as exc:
        raise PromptLoadError(
            f"Could not load Langfuse prompt {prompt_name!r} with label "
            f"{settings.langfuse_prompt_label!r}. Run `uv run python bootstrap_langfuse.py` "
            "inside homework-lesson-12 and verify LANGFUSE_* values in the root .env."
        ) from exc

    if isinstance(compiled, str):
        return compiled

    raise PromptLoadError(
        f"Langfuse prompt {prompt_name!r} did not compile to text. "
        "This homework expects text prompts for create_agent system_prompt."
    )
