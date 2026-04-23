import json
import sys
from typing import Any
from uuid import uuid4

from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from config import settings
from supervisor import supervisor


def _configure_console_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def _shorten(value: object, limit: int = 700) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}... [truncated]"


def _message_content_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(block))
        return "\n".join(part for part in parts if part)
    return str(content)


def _normalize_messages(messages: Any) -> list[Any]:
    if messages is None:
        return []
    if isinstance(messages, list):
        return messages
    return [messages]


def _print_update(update: Any, final_response: list[str], trace: dict[str, Any] | None = None) -> None:
    if not isinstance(update, dict):
        return

    messages = _normalize_messages(update.get("messages"))
    for message in messages:
        if message is None:
            continue

        message_type = getattr(message, "type", None)
        tool_calls = getattr(message, "tool_calls", None) or []

        if message_type == "ai" and tool_calls:
            for call in tool_calls:
                name = call.get("name", "unknown_tool")
                args = call.get("args", {}) or {}
                print(f"\nTool -> {name}: {_shorten(args, 500)}")
                if trace is not None and name == "save_report":
                    trace["save_report_called"] = True
                    filename = args.get("filename")
                    if filename:
                        trace["proposed_filename"] = str(filename)
                    content = args.get("content")
                    if content:
                        trace["proposed_content"] = str(content)
        elif message_type == "tool":
            name = getattr(message, "name", "tool")
            content = getattr(message, "content", "")
            print(f"\nTool <- {name}: {_shorten(content, 700)}")
            if trace is not None and name == "save_report":
                text = str(content or "")
                if "Report saved to:" in text:
                    trace["save_report_succeeded"] = True
                    trace["save_report_message"] = text
        elif message_type == "ai":
            text = _message_content_text(message)
            if text:
                final_response[0] = text
                if trace is not None:
                    trace["final_ai_text"] = text


def _extract_interrupts(data: Any) -> list[Any]:
    interrupts: list[Any] = []
    if not isinstance(data, dict):
        return interrupts

    raw_interrupts = data.get("__interrupt__")
    if raw_interrupts:
        if isinstance(raw_interrupts, (list, tuple)):
            interrupts.extend(raw_interrupts)
        else:
            interrupts.append(raw_interrupts)
        return interrupts

    for update in data.values():
        if isinstance(update, tuple) and update:
            maybe_interrupt = update[0]
            if hasattr(maybe_interrupt, "value"):
                interrupts.append(maybe_interrupt)

    return interrupts


def _iter_stream_updates(chunk: Any) -> tuple[dict[str, Any] | None, list[Any]]:
    if isinstance(chunk, dict) and "type" in chunk and "data" in chunk:
        data = chunk["data"]
    else:
        data = chunk

    interrupts = _extract_interrupts(data)
    if not isinstance(data, dict):
        return None, interrupts

    return data, interrupts


def _run_stream(payload: Any, config: dict, trace: dict[str, Any] | None = None) -> list[Any]:
    final_response = [""]
    interrupts: list[Any] = []

    for chunk in supervisor.stream(
        payload,
        config=config,
        stream_mode=["updates"],
        version="v2",
    ):
        data, found_interrupts = _iter_stream_updates(chunk)
        interrupts.extend(found_interrupts)
        if data is None:
            continue

        if "__interrupt__" in data:
            continue

        for update in data.values():
            _print_update(update, final_response, trace)

    if final_response[0]:
        print(f"\nAgent:\n{final_response[0]}")

    return interrupts


def _interrupt_action_requests(interrupt: Any) -> list[dict[str, Any]]:
    value = getattr(interrupt, "value", {}) or {}
    requests = value.get("action_requests", [])
    return list(requests) if isinstance(requests, list) else []


def _request_name(request: dict[str, Any]) -> str:
    return str(request.get("name") or request.get("action") or "unknown_tool")


def _request_args(request: dict[str, Any]) -> dict[str, Any]:
    args = request.get("arguments")
    if args is None:
        args = request.get("args")
    return dict(args or {})


def _print_interrupt(interrupt: Any) -> None:
    print(f"\n{'=' * 60}")
    print("ACTION REQUIRES APPROVAL")
    print(f"{'=' * 60}")

    for request in _interrupt_action_requests(interrupt):
        args = _request_args(request)
        print(f"Tool: {_request_name(request)}")
        print(f"Args: {json.dumps(args, indent=2, ensure_ascii=False)}")

        filename = args.get("filename")
        content = args.get("content")
        if filename:
            print(f"\nFilename: {filename}")
        if content:
            print("\nReport preview:")
            print(_shorten(content, 1500))
        print()


def _decision_from_user() -> dict[str, Any]:
    while True:
        decision = input("approve / edit / reject: ").strip().lower()
        if decision in {"approve", "a"}:
            return {"type": "approve"}

        if decision in {"edit", "e"}:
            feedback = input("What should change in the report? ").strip()
            if not feedback:
                feedback = "Revise the report according to the user's requested changes."
            return {
                "type": "reject",
                "message": (
                    "The user wants revisions before saving. "
                    f"Revise the report with this feedback and call save_report again: {feedback}"
                ),
            }

        if decision in {"reject", "r"}:
            return {
                "type": "reject",
                "message": (
                    "The user rejected saving the report completely. "
                    "Do not call save_report again. End with a short cancellation message."
                ),
            }

        print("Please type approve, edit, or reject.")


def _resume_after_interrupt(interrupts: list[Any], config: dict, trace: dict[str, Any] | None = None) -> list[Any]:
    if not interrupts:
        return []

    decisions: list[dict[str, Any]] = []
    for interrupt in interrupts:
        _print_interrupt(interrupt)
        action_count = max(1, len(_interrupt_action_requests(interrupt)))
        decision = _decision_from_user()
        if trace is not None and decision.get("type") == "reject":
            message = str(decision.get("message") or "")
            if "rejected saving the report completely" in message or "Do not call save_report again" in message:
                trace["save_cancelled"] = True
        decisions.extend([decision] * action_count)

    return _run_stream(Command(resume={"decisions": decisions}), config, trace)


def _ensure_report_saved(config: dict, trace: dict[str, Any]) -> None:
    """Retry through Supervisor only; no direct ReportMCP fallback bypass."""
    if trace.get("save_report_succeeded") or trace.get("save_cancelled"):
        return

    print("\nSupervisor did not persist a report. Sending an explicit reminder...")
    reminder = (
        "You have not called save_report yet. Recompose the final Markdown report "
        "from prior ACP results and call save_report(filename, content) exactly once now. "
        "Do not ask for permission; HumanInTheLoopMiddleware will handle approval."
    )
    try:
        interrupts = _run_stream(
            {"messages": [{"role": "user", "content": reminder}]},
            config,
            trace,
        )
        while interrupts:
            interrupts = _resume_after_interrupt(interrupts, config, trace)
    except GraphRecursionError:
        print("Reminder stream stopped: recursion limit reached.")
    except Exception as exc:
        print(f"Reminder stream error: {exc}")

    if not trace.get("save_report_succeeded"):
        print("Report was not saved. Re-run with a stronger model or a simpler query.")


def main() -> None:
    _configure_console_encoding()
    print("Protocol-based Multi-Agent Research System (lesson 9). Type 'exit' to quit.")
    print(f"SearchMCP: {settings.search_mcp_url}")
    print(f"ReportMCP: {settings.report_mcp_url}")
    print(f"ACP: {settings.acp_base_url}")
    print("-" * 60)

    thread_id = str(uuid4())
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": settings.max_iterations * 6 + 10,
    }

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        try:
            trace: dict[str, Any] = {
                "save_report_called": False,
                "save_report_succeeded": False,
                "save_cancelled": False,
                "final_ai_text": "",
                "proposed_filename": None,
                "proposed_content": None,
            }
            interrupts = _run_stream(
                {"messages": [{"role": "user", "content": user_input}]},
                config,
                trace,
            )
            while interrupts:
                interrupts = _resume_after_interrupt(interrupts, config, trace)

            _ensure_report_saved(config, trace)
        except GraphRecursionError:
            print("\nSupervisor stopped: recursion limit reached.")
        except Exception as exc:
            print(f"\nSupervisor error: {exc}")


if __name__ == "__main__":
    main()
