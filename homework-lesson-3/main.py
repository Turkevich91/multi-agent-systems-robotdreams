import sys
from uuid import uuid4

from agent import agent
from config import settings
from langgraph.errors import GraphRecursionError


def _configure_console_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def _shorten(value: object, limit: int = 500) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}... [truncated]"


def _stream_response(user_input: str, config: dict) -> None:
    final_response = ""

    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config=config,
        stream_mode="updates",
    ):
        for update in chunk.values():
            if not isinstance(update, dict):
                continue

            messages = update.get("messages", [])
            if not isinstance(messages, list):
                messages = [messages]

            for message in messages:
                if message is None:
                    continue

                message_type = getattr(message, "type", None)
                tool_calls = getattr(message, "tool_calls", None) or []

                if message_type == "ai" and tool_calls:
                    for call in tool_calls:
                        name = call.get("name", "unknown_tool")
                        args = call.get("args", {})
                        print(f"\nTool -> {name}: {_shorten(args, 300)}")
                elif message_type == "tool":
                    name = getattr(message, "name", "tool")
                    content = getattr(message, "content", "")
                    print(f"\nTool <- {name}: {_shorten(content, 500)}")
                elif message_type == "ai" and getattr(message, "content", None):
                    final_response = str(message.content)

    if final_response:
        print(f"\nAgent:\n{final_response}")


def main():
    _configure_console_encoding()
    print("Research Agent (type 'exit' to quit)")
    print("-" * 40)
    thread_id = str(uuid4())
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": settings.max_iterations * 4 + 5,
    }

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        try:
            _stream_response(user_input, config)
        except GraphRecursionError:
            print("\nAgent stopped: iteration limit reached.")
        except Exception as exc:
            print(f"\nAgent error: {exc}")


if __name__ == "__main__":
    main()
