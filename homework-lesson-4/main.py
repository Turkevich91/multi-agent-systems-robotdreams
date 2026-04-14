import sys

from agent import ResearchAgent


def _configure_console_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def main() -> None:
    _configure_console_encoding()
    agent = ResearchAgent(verbose=True)

    print("Research Agent - custom ReAct loop (type 'exit' to quit)")
    print("-" * 56)

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
            response = agent.ask(user_input)
        except Exception as exc:
            print(f"\nAgent error: {exc}")
            continue

        if response:
            print(f"\nAgent:\n{response}")


if __name__ == "__main__":
    main()
