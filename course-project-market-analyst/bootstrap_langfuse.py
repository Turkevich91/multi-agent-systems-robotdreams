from __future__ import annotations

import json

from config import BASE_DIR, settings, sync_langfuse_environment


PROMPTS_FILE = BASE_DIR / "langfuse_prompts.json"


def bootstrap_prompts() -> None:
    sync_langfuse_environment()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        raise SystemExit("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required.")

    from langfuse import get_client

    client = get_client()
    prompts = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    for item in prompts:
        created = client.create_prompt(
            name=item["name"],
            type="text",
            prompt=item["prompt"],
            labels=list(item.get("labels") or [settings.langfuse_prompt_label]),
            tags=["course-project", "market-analyst", "prompt-management"],
            config={
                "course_project": "market-analyst",
                "runtime": "OpenAI + LangGraph + Qdrant RAG + optional MCP",
            },
        )
        print(f"Created/updated prompt {created.name} v{created.version}")

    client.flush()
    print("Langfuse prompt bootstrap complete.")


if __name__ == "__main__":
    bootstrap_prompts()
