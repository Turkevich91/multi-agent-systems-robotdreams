import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph._internal._serde import build_serde_allowlist
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from config import build_chat_model, settings
from critic_registry import select_roles
from mcp_adapter import search_tools
from prompt_registry import load_system_prompt
from schemas import (
    AggregatedCritique,
    CriteriaDecision,
    CriticRole,
    DraftReport,
    ExpertCritique,
    FinalReport,
    MarketSegment,
    MarketState,
    MermaidDiagram,
    SourceRef,
    ToolAssessment,
)
from tool_impl import save_markdown_report, safe_markdown_filename, trim_text


_CHECKPOINT_ALLOWLIST = build_serde_allowlist(
    schemas=[
        SourceRef,
        MarketSegment,
        ToolAssessment,
        DraftReport,
        CriticRole,
        CriteriaDecision,
        ExpertCritique,
        AggregatedCritique,
        MermaidDiagram,
        FinalReport,
        MarketState,
    ]
)
checkpointer = InMemorySaver().with_allowlist(_CHECKPOINT_ALLOWLIST)


def _event(event_type: str, agent: str, message: str, payload: dict | None = None) -> dict:
    return {
        "type": event_type,
        "agent": agent,
        "message": message,
        "payload": payload or {},
    }


def _model_config(config: RunnableConfig | None) -> dict:
    return dict(config or {})


def _json_dump(value: Any) -> str:
    def to_jsonable(item: Any) -> Any:
        if hasattr(item, "model_dump"):
            return item.model_dump(mode="json")
        if isinstance(item, dict):
            return {key: to_jsonable(child) for key, child in item.items()}
        if isinstance(item, list):
            return [to_jsonable(child) for child in item]
        return item

    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2)
    return json.dumps(to_jsonable(value), ensure_ascii=False, indent=2)


def _role_id_from_name(name: str, index: int) -> str:
    role_id = "".join(char.lower() if char.isalnum() else "_" for char in name).strip("_")
    role_id = "_".join(part for part in role_id.split("_") if part)
    return role_id or f"custom_critic_{index + 1}"


def _coerce_critic_roles(raw_roles: list[Any] | None) -> list[CriticRole]:
    roles: list[CriticRole] = []
    for index, raw_role in enumerate(raw_roles or []):
        role = raw_role if isinstance(raw_role, CriticRole) else CriticRole.model_validate(raw_role)
        role_id = role.role_id.strip() or _role_id_from_name(role.name, index)
        name = role.name.strip() or f"Custom Critic {index + 1}"
        focus = role.focus.strip() or "Review the draft through the custom criteria supplied by the human reviewer."
        criteria = [criterion.strip() for criterion in role.criteria if criterion.strip()]
        if not criteria:
            criteria = ["Check the draft against the custom human-review focus."]
        roles.append(role.model_copy(update={"role_id": role_id, "name": name, "focus": focus, "criteria": criteria}))
    return roles


def _roles_for_state(raw_roles: list[Any] | None) -> list[dict[str, Any]]:
    return [role.model_dump(mode="json") for role in _coerce_critic_roles(raw_roles)]


def _with_human_criteria_role(roles: list[CriticRole], additional_criteria: list[str]) -> list[CriticRole]:
    clean_criteria = [criterion.strip() for criterion in additional_criteria if criterion.strip()]
    if not clean_criteria:
        return roles
    has_custom_role = any(role.role_id.startswith(("custom", "human_custom")) for role in roles)
    if has_custom_role:
        return roles
    human_role = CriticRole(
        role_id="human_custom_criteria",
        name="Human Criteria Critic",
        focus="Reviews the draft only through the extra criteria added by the human reviewer.",
        criteria=clean_criteria,
    )
    return [*roles, human_role]


def _market_evidence(user_request: str) -> str:
    request = user_request.strip()
    queries = [
        request,
        f"{request} market trends adoption demand 2026",
        f"{request} leading companies products comparison",
        f"{request} risks barriers opportunities",
    ]
    blocks: list[str] = []
    for query in queries:
        web_results = search_tools.web_search(query)
        blocks.append(f"WEB SEARCH: {query}\n{_json_dump(web_results[:3])}")

    kb_results = search_tools.knowledge_search(f"{request} market analysis adoption risks evaluation")
    blocks.append(f"LOCAL KNOWLEDGE SEARCH\n{kb_results}")
    return trim_text("\n\n".join(blocks), 18000)


def _fallback_title(user_request: str) -> str:
    clean = " ".join(user_request.split())
    if len(clean) > 96:
        clean = f"{clean[:93].rstrip()}..."
    return f"Market Analysis: {clean or 'User Requested Market'}"


def _fallback_draft(user_request: str, evidence: str, revision_notes: list[str] | None = None) -> DraftReport:
    requested_market = " ".join(user_request.split()) or "the requested market"
    sources = [
        SourceRef(
            title="Public web and local RAG evidence bundle",
            source="SearchMCP/direct tools",
            evidence="The analyst collected public snippets plus local course notes before drafting.",
            source_type="manual_note",
        )
    ]
    return DraftReport(
        title=_fallback_title(user_request),
        executive_summary=(
            f"This fallback draft keeps the analysis anchored to the user's requested market: "
            f"{requested_market}. The model could not produce a structured DraftReport, so the system "
            "summarizes the evidence bundle and marks the main areas that need market validation."
        ),
        market_segments=[
            MarketSegment(
                name="Core demand segment",
                description=f"Organizations or users actively searching for solutions related to {requested_market}.",
                relevant_tools=["Leading products should be extracted from public evidence"],
                adoption_signal="Use search volume, funding, product launches and customer case studies as demand signals.",
            ),
            MarketSegment(
                name="Emerging solution segment",
                description="Newer vendors, open-source tools or mobile-first products that may change category expectations.",
                relevant_tools=["Emerging tools found in current public sources"],
                adoption_signal="Watch for recent launches, developer activity, partnerships and distribution channels.",
            ),
            MarketSegment(
                name="Adjacent ecosystem segment",
                description="Supporting platforms, data providers, integration layers or services around the requested market.",
                relevant_tools=["Adjacent platforms and service providers"],
                adoption_signal="Strong fit when buyers need implementation support, integrations or compliance help.",
            ),
        ],
        tool_assessments=[
            ToolAssessment(
                name="Primary solution category",
                category="market-category",
                strengths=["Directly addresses the user-requested market need", "Can be benchmarked against public competitors"],
                limitations=["Requires current source validation", "May differ by geography, platform and buyer segment"],
                fit_for_target_context="Evaluate against the target audience and use case stated in the user's prompt.",
                sources=["Public web and local RAG evidence bundle"],
            ),
            ToolAssessment(
                name="Supporting ecosystem category",
                category="adjacent-category",
                strengths=["Can improve adoption through integrations, distribution or implementation support"],
                limitations=["Value depends on ecosystem maturity and switching costs"],
                fit_for_target_context="Useful when the requested market depends on workflows, integrations or data access.",
                sources=["Public web and local RAG evidence bundle"],
            ),
        ],
        adoption_drivers=[
            "Clear user pain or business demand in the requested market",
            "Improving technical capability and distribution channels",
            "Recent public signals such as funding, launches, regulation or customer adoption",
        ],
        risks=[
            "Evidence may be too thin or outdated for confident recommendations",
            "Market demand may be concentrated in a narrow segment",
            "Implementation cost, data quality or regulatory constraints may slow adoption",
        ],
        opportunities=[
            "Identify underserved niches inside the requested market",
            "Compare incumbents against emerging products",
            "Build a phased validation roadmap before committing budget",
        ],
        open_questions=[
            "Which buyer segment is most urgent and reachable?",
            "Which competitors or substitutes define the category?",
            "Which current sources best prove near-term demand?",
        ],
        sources=sources,
        revision_notes=revision_notes or [f"Evidence summary was trimmed to {len(evidence)} characters."],
    )


def analyst_node(state: MarketState, config: RunnableConfig | None = None) -> dict:
    user_request = state["user_request"]
    revision_round = int(state.get("revision_round", 0))
    previous_critique = state.get("aggregated_critique")
    if previous_critique and previous_critique.verdict == "NEEDS_REVISION":
        revision_round += 1

    evidence = _market_evidence(user_request)
    feedback = ""
    if previous_critique:
        feedback = (
            "\n\nCritic feedback to address:\n"
            f"{_json_dump(previous_critique)}"
        )

    prompt = (
        f"User request:\n{user_request}\n\n"
        f"Evidence bundle:\n{evidence}\n"
        f"{feedback}\n\n"
        "Create a source-backed DraftReport for the exact market and target context in the user request. "
        "Do not switch to the default course demo topic unless the user explicitly requested it. "
        "Keep private company names, personal data and secrets out of the report."
    )

    try:
        model = build_chat_model().with_structured_output(DraftReport)
        draft = model.invoke(
            [SystemMessage(content=load_system_prompt("analyst")), HumanMessage(content=prompt)],
            config=_model_config(config),
        )
        if not isinstance(draft, DraftReport):
            draft = DraftReport.model_validate(draft)
    except Exception:
        revision_notes = list(previous_critique.revision_requests) if previous_critique else []
        draft = _fallback_draft(user_request, evidence, revision_notes)

    return {
        "draft": draft,
        "revision_round": revision_round,
        "expert_critiques": [],
        "events": [
            _event(
                "agent_update",
                "Research Analyst",
                f"Draft report prepared (revision round {revision_round}).",
                {"title": draft.title, "sources": len(draft.sources)},
            )
        ],
    }


def route_after_analyst(state: MarketState) -> str:
    return "expert_critics" if state.get("approved_roles") else "select_critic_roles"


def select_critic_roles_node(state: MarketState) -> dict:
    roles = select_roles(state["user_request"], state["draft"], settings.default_critic_roles)
    return {
        "selected_roles": _roles_for_state(roles),
        "events": [
            _event(
                "agent_update",
                "Critic Role Selector",
                "Selected expert critic roles for human review.",
                {"roles": [role.model_dump(mode="json") for role in roles]},
            )
        ],
    }


def human_criteria_node(state: MarketState) -> dict:
    selected_roles = _coerce_critic_roles(state["selected_roles"])
    resume_payload = interrupt(
        {
            "type": "critic_criteria_review",
            "selected_roles": [role.model_dump(mode="json") for role in selected_roles],
            "instructions": (
                "Approve these critic roles or edit criteria before the expert panel reviews the draft."
            ),
        }
    )

    if not resume_payload:
        decision = CriteriaDecision(approved_roles=selected_roles)
    else:
        decision = CriteriaDecision.model_validate(resume_payload)
    approved_roles = _with_human_criteria_role(
        _coerce_critic_roles(decision.approved_roles),
        decision.additional_criteria,
    )

    return {
        "approved_roles": _roles_for_state(approved_roles),
        "additional_criteria": decision.additional_criteria,
        "events": [
            _event(
                "human_update",
                "Human Criteria Gate",
                "Critic roles and criteria approved.",
                {
                    "roles": [role.model_dump(mode="json") for role in approved_roles],
                    "additional_criteria": decision.additional_criteria,
                },
            )
        ],
    }


def _fallback_expert_critique(role: CriticRole, draft: DraftReport, additional_criteria: list[str]) -> ExpertCritique:
    issues = []
    if len(draft.sources) < 3:
        issues.append("The draft should include more concrete public sources.")
    if role.role_id in {"financial", "risk"}:
        issues.append(f"{role.name} requests sharper treatment of: {role.focus}")
    if additional_criteria:
        issues.append("Human-added criteria need explicit coverage: " + "; ".join(additional_criteria))

    verdict = "NEEDS_REVISION" if issues else "APPROVED"
    return ExpertCritique(
        role_id=role.role_id,
        role_name=role.name,
        verdict=verdict,
        score=0.72 if issues else 0.86,
        strengths=["The draft is aligned with the requested market-analysis topic."],
        issues=issues,
        source_gaps=["Add source-level evidence for the highest-impact recommendations."] if issues else [],
        recommendations=[
            "Make recommendations measurable and tie them to a phased adoption roadmap.",
            "Keep MCP optional and read-only in the first adoption phase.",
        ],
    )


def expert_critics_node(state: MarketState, config: RunnableConfig | None = None) -> dict:
    draft = state["draft"]
    roles = _coerce_critic_roles(state.get("approved_roles") or state.get("selected_roles") or [])
    additional_criteria = state.get("additional_criteria") or []
    critiques: list[ExpertCritique] = []

    for role in roles:
        prompt = (
            f"Critic role:\n{_json_dump(role)}\n\n"
            f"Additional human criteria:\n{_json_dump(additional_criteria)}\n\n"
            f"Draft report:\n{_json_dump(draft)}"
        )
        try:
            model = build_chat_model().with_structured_output(ExpertCritique)
            critique = model.invoke(
                [SystemMessage(content=load_system_prompt("critic")), HumanMessage(content=prompt)],
                config=_model_config(config),
            )
            if not isinstance(critique, ExpertCritique):
                critique = ExpertCritique.model_validate(critique)
        except Exception:
            critique = _fallback_expert_critique(role, draft, additional_criteria)

        critiques.append(critique)

    return {
        "expert_critiques": critiques,
        "events": [
            _event(
                "agent_update",
                "Expert Critic Panel",
                "Expert critiques completed.",
                {
                    "roles": [critique.role_name for critique in critiques],
                    "scores": [critique.score for critique in critiques],
                },
            )
        ],
    }


def critic_aggregator_node(state: MarketState) -> dict:
    critiques = state.get("expert_critiques") or []
    if not critiques:
        aggregate = AggregatedCritique(
            verdict="NEEDS_REVISION",
            score=0.0,
            summary="No expert critiques were produced.",
            revision_requests=["Run the expert critic panel before compiling the report."],
            expert_feedback=[],
        )
    else:
        score = sum(item.score for item in critiques) / len(critiques)
        revision_requests: list[str] = []
        for critique in critiques:
            revision_requests.extend(critique.issues)
            revision_requests.extend(critique.source_gaps)
            if critique.verdict == "NEEDS_REVISION":
                revision_requests.extend(critique.recommendations[:2])

        verdict = "APPROVED"
        if score < 0.78 or any(item.verdict == "NEEDS_REVISION" for item in critiques):
            verdict = "NEEDS_REVISION"

        if int(state.get("revision_round", 0)) >= settings.max_revision_rounds:
            verdict = "APPROVED"
            revision_requests.append("Revision limit reached; compiler should preserve known limitations.")

        aggregate = AggregatedCritique(
            verdict=verdict,
            score=max(0.0, min(1.0, score)),
            summary=(
                f"Expert panel average score {score:.2f}. "
                f"Verdict: {verdict}. Key requests: {len(revision_requests)}."
            ),
            revision_requests=list(dict.fromkeys(item for item in revision_requests if item.strip()))[:8],
            expert_feedback=critiques,
        )

    return {
        "aggregated_critique": aggregate,
        "events": [
            _event(
                "agent_update",
                "Critic Aggregator",
                aggregate.summary,
                {"verdict": aggregate.verdict, "score": aggregate.score},
            )
        ],
    }


def route_after_aggregate(state: MarketState) -> str:
    critique = state["aggregated_critique"]
    if critique.verdict == "NEEDS_REVISION" and int(state.get("revision_round", 0)) < settings.max_revision_rounds:
        return "analyst"
    return "compiler"


def _pie_label(value: str) -> str:
    return value.replace('"', "'").replace("\n", " ").strip()[:42] or "Critic"


def _diagram_label(value: str | None, fallback: str, limit: int = 58) -> str:
    cleaned = (value or fallback).replace('"', "'").replace("\n", " ").strip()
    for old, new in [("[", "("), ("]", ")"), ("{", "("), ("}", ")"), (":", " -")]:
        cleaned = cleaned.replace(old, new)
    if len(cleaned) > limit:
        cleaned = f"{cleaned[: limit - 3].rstrip()}..."
    return cleaned or fallback


def _critic_score_pie(state: MarketState | None) -> MermaidDiagram:
    critique = state.get("aggregated_critique") if state else None
    feedback = critique.expert_feedback if critique else []
    if feedback:
        lines = ["pie showData", "    title Expert Critic Score Share"]
        for expert in feedback:
            lines.append(f'    "{_pie_label(expert.role_name)}" : {max(1, round(expert.score * 100))}')
    else:
        lines = [
            "pie showData",
            "    title Expert Critic Score Share",
            '    "Financial fit" : 50',
            '    "Operational risk" : 50',
        ]
    return MermaidDiagram(
        title="Expert Critic Score Share",
        kind="score_pie",
        mermaid="\n".join(lines),
    )


def _default_diagrams(state: MarketState | None = None) -> list[MermaidDiagram]:
    draft = state.get("draft") if state else None
    segments = draft.market_segments if draft else []
    assessments = draft.tool_assessments if draft else []

    primary_segment = _diagram_label(segments[0].name if segments else None, "Primary beachhead segment", 48)
    secondary_segment = _diagram_label(segments[1].name if len(segments) > 1 else None, "Secondary segment", 48)
    top_tool = _diagram_label(assessments[0].name if assessments else None, "Shortlisted solution category", 48)
    opportunity = _diagram_label(draft.opportunities[0] if draft and draft.opportunities else None, "validated demand signal", 62)
    key_risk = _diagram_label(draft.risks[0] if draft and draft.risks else None, "main adoption risk", 62)

    saturation_basis = [item.name for item in segments[:4]] or [item.name for item in assessments[:4]]
    if not saturation_basis:
        saturation_basis = ["Primary segment", "Adjacent segment", "Crowded category", "Open niche"]
    saturation_points = [
        (0.76, 0.68),
        (0.62, 0.48),
        (0.42, 0.28),
        (0.34, 0.72),
    ]
    saturation_lines = [
        "quadrantChart",
        "    title Market Saturation Map",
        "    x-axis Low buyer pull --> High buyer pull",
        "    y-axis Crowded category --> Open whitespace",
        "    quadrant-1 High-pull whitespace",
        "    quadrant-2 Low-pull whitespace",
        "    quadrant-3 Low-pull crowded",
        "    quadrant-4 High-pull crowded",
    ]
    for index, name in enumerate(saturation_basis[:4]):
        x_value, y_value = saturation_points[index]
        saturation_lines.append(f'    "{_diagram_label(name, f"Segment {index + 1}", 36)}" : [{x_value}, {y_value}]')

    diagrams = [
        MermaidDiagram(
            title="Market Entry Decision Flow",
            kind="market_entry",
            mermaid=f"""flowchart TD
    Thesis["Market entry thesis"] --> Beachhead["Beachhead: {primary_segment}"]
    Beachhead --> Demand{{"Demand signal strong enough?"}}
    Demand -- "no" --> Narrow["Narrow positioning or gather more evidence"]
    Demand -- "yes" --> Offer["Package offer around: {top_tool}"]
    Offer --> Pilot["Pilot with buyers in: {primary_segment}"]
    Pilot --> Expand{{"Repeatable value proven?"}}
    Expand -- "yes" --> Adjacent["Expand to: {secondary_segment}"]
    Expand -- "no" --> Reprice["Rework pricing, scope or channel"]""",
        ),
        MermaidDiagram(
            title="Payback Decision Gate",
            kind="payback",
            mermaid=f"""flowchart LR
    Spend["Investment: seats, APIs, integration time"] --> Pilot["Measured pilot"]
    Upside["Main upside: {opportunity}"] --> Pilot
    Drag["Main risk: {key_risk}"] --> Pilot
    Pilot --> Metrics["Track savings, revenue lift and risk reduction"]
    Metrics --> Payback{{"Payback within target window?"}}
    Payback -- "yes" --> Scale["Scale budget and vendor commitment"]
    Payback -- "no" --> Adjust["Reduce scope, renegotiate or stop"]""",
        ),
        MermaidDiagram(
            title="Market Validation Timeline",
            kind="timeline",
            mermaid=f"""timeline
    title Market Validation Timeline
    0 to 30 days : Evidence scan
                 : Validate {primary_segment}
    31 to 60 days : Pilot package
                  : Test {opportunity}
    61 to 90 days : Payback gate
                  : Compare cost, demand and risk
    90 plus days : Scale or pause
                 : Mitigate {key_risk}""",
        ),
        MermaidDiagram(
            title="Market Saturation Map",
            kind="saturation",
            mermaid="\n".join(saturation_lines),
        ),
    ]
    diagrams.append(_critic_score_pie(state))
    return diagrams


def _remove_orchestrator_diagrams(markdown: str) -> str:
    unwanted_titles = [
        "Architecture Integration Map",
        "Orchestrator Architecture",
        "Agent Orchestration Flow",
        "Risk Decision Flow",
        "Adoption Roadmap",
    ]
    cleaned = markdown
    for title in unwanted_titles:
        cleaned = re.sub(
            rf"\n+### {re.escape(title)}\n```mermaid\n.*?\n```",
            "",
            cleaned,
            flags=re.DOTALL,
        )
    return cleaned.strip()


def _merge_required_diagrams(final_report: FinalReport, required: list[MermaidDiagram]) -> None:
    existing_titles = {diagram.title for diagram in final_report.diagrams}
    for diagram in required:
        if diagram.title not in existing_titles:
            final_report.diagrams.append(diagram)
            existing_titles.add(diagram.title)

    missing_markdown = [
        diagram for diagram in required if f"### {diagram.title}" not in final_report.markdown
    ]
    if missing_markdown:
        final_report.markdown = f"{final_report.markdown.rstrip()}\n\n" + "\n\n".join(
            f"### {diagram.title}\n```mermaid\n{diagram.mermaid}\n```" for diagram in missing_markdown
        )


def _markdown_from_state(state: MarketState, diagrams: list[MermaidDiagram]) -> str:
    draft = state["draft"]
    critique = state["aggregated_critique"]
    lines = [
        f"# {draft.title}",
        "",
        "## Executive Summary",
        draft.executive_summary,
        "",
        "## Market Segments",
    ]
    for segment in draft.market_segments:
        lines.append(f"- **{segment.name}:** {segment.description} Adoption signal: {segment.adoption_signal}")

    lines.extend(["", "## Tool Assessments"])
    for item in draft.tool_assessments:
        lines.extend(
            [
                f"### {item.name}",
                f"- Category: {item.category}",
                f"- Strengths: {'; '.join(item.strengths)}",
                f"- Limitations: {'; '.join(item.limitations)}",
                f"- Fit: {item.fit_for_target_context}",
            ]
        )

    lines.extend(["", "## Expert Critic Panel"])
    for expert in critique.expert_feedback:
        lines.append(f"- **{expert.role_name}:** {expert.verdict}, score {expert.score:.2f}. {'; '.join(expert.recommendations[:2])}")

    lines.extend(["", "## Adoption Recommendations"])
    for opportunity in draft.opportunities:
        lines.append(f"- {opportunity}")

    lines.extend(["", "## Risks And Controls"])
    for risk in draft.risks:
        lines.append(f"- {risk}")

    lines.extend(["", "## Mermaid Decision Diagrams"])
    for diagram in diagrams:
        lines.extend(["", f"### {diagram.title}", "```mermaid", diagram.mermaid, "```"])

    lines.extend(["", "## Sources"])
    for source in draft.sources:
        lines.append(f"- {source.title}: {source.source} - {source.evidence}")

    lines.extend(["", "## Methodology"])
    lines.append(
        "The system combined public web search, local RAG notes, expert critic routing, "
        "human-approved criteria, and a revision loop before compiling this decision package."
    )
    return "\n".join(lines)


def compiler_node(state: MarketState, config: RunnableConfig | None = None) -> dict:
    diagrams = _default_diagrams(state)
    fallback_report = FinalReport(
        title=state["draft"].title,
        markdown=_markdown_from_state(state, diagrams),
        diagrams=diagrams,
        sources=state["draft"].sources,
    )

    prompt = (
        f"Draft report:\n{_json_dump(state['draft'])}\n\n"
        f"Aggregated critique:\n{_json_dump(state['aggregated_critique'])}\n\n"
        f"Baseline Mermaid diagrams:\n{_json_dump(diagrams)}\n\n"
        "Return a final report with polished Markdown and Mermaid diagrams."
    )
    try:
        model = build_chat_model().with_structured_output(FinalReport)
        final_report = model.invoke(
            [SystemMessage(content=load_system_prompt("compiler")), HumanMessage(content=prompt)],
            config=_model_config(config),
        )
        if not isinstance(final_report, FinalReport):
            final_report = FinalReport.model_validate(final_report)
        final_report.diagrams = diagrams
        final_report.markdown = _remove_orchestrator_diagrams(final_report.markdown)
        _merge_required_diagrams(final_report, diagrams)
        if "```mermaid" not in final_report.markdown:
            final_report.markdown = f"{final_report.markdown.rstrip()}\n\n" + "\n\n".join(
                f"### {diagram.title}\n```mermaid\n{diagram.mermaid}\n```" for diagram in final_report.diagrams
            )
    except Exception:
        final_report = fallback_report

    filename = safe_markdown_filename(f"{state.get('run_id', 'market_analysis')}_{final_report.title}.md")
    saved_path = save_markdown_report(filename, final_report.markdown)
    final_report.saved_path = saved_path

    return {
        "final_report": final_report,
        "events": [
            _event(
                "completed",
                "Report Compiler",
                "Final report and Mermaid decision diagrams saved.",
                {"saved_path": saved_path, "diagrams": len(final_report.diagrams)},
            )
        ],
    }


def build_market_graph():
    graph = StateGraph(MarketState)
    graph.add_node("analyst", analyst_node)
    graph.add_node("select_critic_roles", select_critic_roles_node)
    graph.add_node("human_criteria", human_criteria_node)
    graph.add_node("expert_critics", expert_critics_node)
    graph.add_node("critic_aggregator", critic_aggregator_node)
    graph.add_node("compiler", compiler_node)

    graph.set_entry_point("analyst")
    graph.add_conditional_edges(
        "analyst",
        route_after_analyst,
        {
            "select_critic_roles": "select_critic_roles",
            "expert_critics": "expert_critics",
        },
    )
    graph.add_edge("select_critic_roles", "human_criteria")
    graph.add_edge("human_criteria", "expert_critics")
    graph.add_edge("expert_critics", "critic_aggregator")
    graph.add_conditional_edges(
        "critic_aggregator",
        route_after_aggregate,
        {
            "analyst": "analyst",
            "compiler": "compiler",
        },
    )
    graph.add_edge("compiler", END)
    return graph.compile(checkpointer=checkpointer)


market_graph = build_market_graph()
