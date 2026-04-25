from __future__ import annotations

import json
from pathlib import Path

from config import BASE_DIR, settings, sync_langfuse_environment


PROMPTS_FILE = BASE_DIR / "langfuse_prompts.json"


def load_prompt_seed() -> list[dict]:
    return json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))


def bootstrap_prompts() -> None:
    sync_langfuse_environment()

    from langfuse import get_client

    client = get_client()
    prompts = load_prompt_seed()

    for item in prompts:
        created = client.create_prompt(
            name=item["name"],
            type="text",
            prompt=item["prompt"],
            labels=list(item.get("labels") or [settings.langfuse_prompt_label]),
            tags=["homework-12", "multi-agent", "prompt-management"],
            config={
                "homework": "lesson-12",
                "runtime": "LM Studio + LangChain create_agent + Qdrant RAG",
            },
        )
        print(
            f"Created/updated prompt {created.name} "
            f"v{created.version} labels={list(item.get('labels') or [])}"
        )

    client.flush()
    print("Langfuse prompt bootstrap complete.")


def main() -> None:
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        raise SystemExit("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required.")
    if not settings.langfuse_base_url:
        raise SystemExit("LANGFUSE_BASE_URL is required.")
    bootstrap_prompts()


if __name__ == "__main__":
    main()
