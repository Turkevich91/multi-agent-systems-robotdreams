from __future__ import annotations

import json
import sys
from uuid import uuid4

from langgraph.types import Command

from graph import market_graph
from observability import langfuse_observed_run
from schemas import CriteriaDecision, CriticRole


DEFAULT_REQUEST = (
    "Analyze the market for agentic AI developer tools for a small AEC/manufacturing software team. "
    "Compare coding agents, IDE copilots, observability/evaluation platforms, and MCP-based integrations. "
    "Recommend an adoption roadmap."
)


def _configure_console_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def _extract_interrupts(data) -> list:
    if isinstance(data, dict) and data.get("__interrupt__"):
        raw = data["__interrupt__"]
        return list(raw) if isinstance(raw, (list, tuple)) else [raw]
    return []


def _print_events(update: dict) -> None:
    for node_update in update.values():
        if not isinstance(node_update, dict):
            continue
        for event in node_update.get("events", []):
            print(f"[{event.get('agent')}] {event.get('message')}")


def _stream(payload, config: dict) -> list:
    interrupts = []
    for chunk in market_graph.stream(payload, config=config, stream_mode=["updates"], version="v2"):
        data = chunk.get("data") if isinstance(chunk, dict) and "data" in chunk else chunk
        interrupts.extend(_extract_interrupts(data))
        if isinstance(data, dict) and "__interrupt__" not in data:
            _print_events(data)
    return interrupts


def _criteria_from_user(interrupt_value: dict) -> CriteriaDecision:
    roles = [CriticRole.model_validate(item) for item in interrupt_value.get("selected_roles", [])]
    print("\nExpert critic roles selected:")
    for index, role in enumerate(roles, 1):
        print(f"{index}. {role.name}: {role.focus}")
        for criterion in role.criteria:
            print(f"   - {criterion}")

    answer = input("\nApprove roles? Type approve or add extra criteria: ").strip()
    extra: list[str] = []
    if answer and answer.lower() not in {"approve", "a", "yes", "y"}:
        extra = [item.strip() for item in answer.split(";") if item.strip()]

    return CriteriaDecision(approved_roles=roles, additional_criteria=extra)


def main() -> None:
    _configure_console_encoding()
    print("Course Project Market Analyst. Type a prompt or press Enter for the acceptance query.")
    user_request = input("\nRequest: ").strip() or DEFAULT_REQUEST
    run_id = f"cli-{uuid4().hex[:8]}"
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 80}

    with langfuse_observed_run(user_request, thread_id) as lf_run:
        runtime_config = lf_run.with_callbacks(config)
        interrupts = _stream(
            {"run_id": run_id, "user_request": user_request, "revision_round": 0, "events": []},
            runtime_config,
        )
        while interrupts:
            interrupt_value = getattr(interrupts[0], "value", {}) or {}
            decision = _criteria_from_user(interrupt_value)
            interrupts = _stream(Command(resume=decision.model_dump(mode="json")), runtime_config)

        final_state = market_graph.get_state(runtime_config).values
        final_report = final_state.get("final_report")
        lf_run.output = {
            "final_report": final_report.model_dump(mode="json") if final_report else None,
            "events": final_state.get("events", []),
        }
        if lf_run.trace_id:
            print(f"\nLangfuse trace_id: {lf_run.trace_id}")

    final_state = market_graph.get_state(config).values
    final_report = final_state.get("final_report")
    if final_report:
        print("\nFinal report saved:")
        print(final_report.saved_path)
        print("\nDiagrams:")
        print(json.dumps([item.model_dump(mode="json") for item in final_report.diagrams], indent=2))


if __name__ == "__main__":
    main()
