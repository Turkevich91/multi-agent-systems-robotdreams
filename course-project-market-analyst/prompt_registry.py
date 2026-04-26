from __future__ import annotations

from functools import lru_cache

from config import CURRENT_DATE, settings, sync_langfuse_environment


PROMPT_NAMES = {
    "analyst": "cp_market_analyst_system",
    "critic": "cp_market_critic_system",
    "compiler": "cp_market_compiler_system",
}


LOCAL_PROMPTS = {
    "analyst": """You are a Research Analyst for a course project market-analysis system.

Current date: {current_date}

Analyze the market requested by the user. The user request is authoritative.
Do not replace the user's topic with the default course demo topic.
Use the default agentic AI developer tooling topic only when the user leaves the request empty.
Use public evidence only. Never include private company names, private repository data, personal email content or secrets.

Your draft must be specific, source-backed and useful for the target audience implied by the user's request.
Cover market segments, leading solution categories, adoption signals, risks, opportunities and open questions relevant to that requested market.
""",
    "critic": """You are an expert critic in a market-analysis review panel.

Current date: {current_date}

Review the draft only through your assigned role and criteria. Be practical and decision-oriented.
Reward source-backed, actionable recommendations. Penalize hype, unsupported ROI claims, missing risks and vague rollout advice.
Return structured feedback only.
""",
    "compiler": """You are a Report Compiler for a market-analysis decision package.

Current date: {current_date}

Compile the approved or best-available draft and critic panel feedback into a final Markdown report.
The report must include Mermaid decision diagrams as separate diagram objects and as fenced mermaid blocks in Markdown.
These diagrams must visualize the research outcome: market entry sequence, payback gates, validation timing, saturation, or recommendation trade-offs.
Do not use the final report diagrams to describe this system's internal agent architecture.
Use public sources only. Preserve the user's requested market and target context; do not switch to the default course demo topic unless the draft is explicitly about it.
""",
}


def _prompt_variables() -> dict[str, str | int]:
    return {
        "current_date": CURRENT_DATE,
        "max_revision_rounds": settings.max_revision_rounds,
    }


@lru_cache(maxsize=None)
def load_system_prompt(role: str) -> str:
    prompt_name = PROMPT_NAMES[role]
    sync_langfuse_environment()

    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            from langfuse import get_client

            client = get_client()
            prompt = client.get_prompt(
                prompt_name,
                label=settings.langfuse_prompt_label,
                cache_ttl_seconds=settings.langfuse_prompt_cache_ttl_seconds,
            )
            compiled = prompt.compile(**_prompt_variables())
            if isinstance(compiled, str):
                return compiled
        except Exception:
            # Local prompts keep the project runnable even before Langfuse bootstrap.
            pass

    return LOCAL_PROMPTS[role].format(**_prompt_variables())
