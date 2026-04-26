from __future__ import annotations

from schemas import CriticRole, DraftReport


CRITIC_REGISTRY: dict[str, CriticRole] = {
    "financial": CriticRole(
        role_id="financial",
        name="Financial Critic",
        focus="Cost, ROI, licensing, seat expansion, vendor lock-in and budget predictability.",
        criteria=[
            "Does the recommendation distinguish paid seats, API usage, observability cost and hidden integration time?",
            "Are ROI claims tied to plausible developer workflow improvements rather than hype?",
            "Does the report avoid locking the team into one vendor without an exit path?",
        ],
    ),
    "risk": CriticRole(
        role_id="risk",
        name="Risk Manager",
        focus="Adoption risks, governance, data leakage, process disruption and failure modes.",
        criteria=[
            "Does the report identify operational risks before recommending automation?",
            "Are human approval gates proposed for write actions and sensitive repositories?",
            "Does the adoption roadmap include rollback and monitoring?",
        ],
    ),
    "security": CriticRole(
        role_id="security",
        name="Security Critic",
        focus="Secrets, repository access, private data exposure, permissions and tool scope.",
        criteria=[
            "Does the report separate public market research from private company data?",
            "Are API keys, source code and customer data protected from prompts and logs?",
            "Are agent tools scoped read-only unless a human approves write operations?",
        ],
    ),
    "architecture": CriticRole(
        role_id="architecture",
        name="Technical Architecture Critic",
        focus="Integration complexity, maintainability, protocol boundaries and developer experience.",
        criteria=[
            "Does the recommendation fit a small team without excessive platform overhead?",
            "Are MCP, RAG, observability and IDE agents placed where they add clear value?",
            "Does the proposed architecture have clear ownership and low debugging friction?",
        ],
    ),
    "change": CriticRole(
        role_id="change",
        name="Change Management Critic",
        focus="Team adoption, training, workflow fit and rollout sequencing.",
        criteria=[
            "Does the roadmap start with low-risk pilot workflows?",
            "Are team habits, review culture and trust calibration addressed?",
            "Does the report define when to expand, pause or reverse adoption?",
        ],
    ),
}


def default_roles(role_ids: list[str]) -> list[CriticRole]:
    roles = [CRITIC_REGISTRY[item] for item in role_ids if item in CRITIC_REGISTRY]
    return roles[:2] or [
        CRITIC_REGISTRY["financial"],
        CRITIC_REGISTRY["risk"],
    ]


def select_roles(user_request: str, draft: DraftReport, configured_defaults: list[str]) -> list[CriticRole]:
    selected_ids: list[str] = []
    for role_id in configured_defaults:
        if role_id in CRITIC_REGISTRY and role_id not in selected_ids:
            selected_ids.append(role_id)

    return default_roles(selected_ids)
