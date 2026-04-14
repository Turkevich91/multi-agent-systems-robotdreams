import json
from typing import Any

import httpx

from config import SYSTEM_PROMPT, settings
from tools import TOOL_DEFINITIONS, TOOL_REGISTRY, ToolResult


Message = dict[str, Any]


class ResearchAgent:
    def __init__(self, *, verbose: bool = True) -> None:
        self.verbose = verbose
        self.messages: list[Message] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.current_task: str | None = None

    def ask(self, user_input: str) -> str:
        self.current_task = user_input
        turn_start = len(self.messages)
        self.messages.append({"role": "user", "content": user_input})

        for iteration in range(1, settings.max_iterations + 1):
            assistant_message = self._chat_completion(use_tools=True)
            self.messages.append(assistant_message)

            tool_calls = assistant_message.get("tool_calls") or []
            if not tool_calls:
                content = self._message_content(assistant_message).strip()
                if content:
                    if (
                        self._current_task_requires_report()
                        and not self._turn_called_tool(turn_start, "write_report")
                    ):
                        forced_response = self._force_write_report(
                            "Your previous answer claimed or implied that the report was complete, "
                            "but write_report was not called in the current task. Call write_report now "
                            "with the Markdown report for the current task. Do not just say it was saved."
                        )
                        if forced_response:
                            return forced_response

                    return content

                self.messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous assistant response was empty. Continue the current task: "
                            "if enough information was gathered, save the Markdown report with write_report "
                            "and provide a concise final answer with the saved path. If not enough information "
                            "was gathered, use the available tools or clearly explain the limitation."
                        ),
                    }
                )
                continue

            self._log(f"\n--- ReAct iteration {iteration} ---")
            for tool_call in tool_calls:
                tool_message = self._handle_tool_call(tool_call)
                self.messages.append(tool_message)

        return self._finalize_after_iteration_limit(turn_start)

    def _chat_completion(self, *, use_tools: bool, tool_choice: Any | None = None) -> Message:
        messages = self._messages_for_api()
        payload: dict[str, Any] = {
            "model": settings.model_name,
            "messages": messages,
            "temperature": settings.temperature,
        }
        if use_tools:
            payload["tools"] = TOOL_DEFINITIONS
            payload["tool_choice"] = tool_choice or "auto"

        last_error: Exception | None = None
        for attempt in range(settings.max_retries + 1):
            try:
                with httpx.Client(timeout=settings.request_timeout) as client:
                    response = client.post(
                        self._chat_completions_url(),
                        headers=self._headers(),
                        json=payload,
                    )
                response.raise_for_status()
                data = response.json()
                raw_message = data["choices"][0]["message"]
                return self._normalize_assistant_message(raw_message)
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                last_error = exc
                if attempt >= settings.max_retries:
                    break

        raise RuntimeError(f"LLM API request failed: {last_error}") from last_error

    def _handle_tool_call(self, tool_call: Message) -> Message:
        tool_call_id = str(tool_call.get("id") or "missing_tool_call_id")
        function_call = tool_call.get("function") or {}
        name = str(function_call.get("name") or "")

        arguments, parse_error = self._parse_arguments(function_call.get("arguments"))
        if parse_error:
            result: ToolResult = {"error": parse_error, "raw_arguments": function_call.get("arguments")}
        else:
            result = self._execute_tool(name, arguments)

        result_text = self._serialize_tool_result(result)
        self._log(f"Tool call: {name or 'unknown_tool'}({self._shorten(json.dumps(arguments, ensure_ascii=False), 400)})")
        self._log(f"Result: {self._shorten(result_text, 700)}")

        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name or "unknown_tool",
            "content": result_text,
        }

    def _execute_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = TOOL_REGISTRY.get(name)
        if tool is None:
            return {"error": f"Unknown tool: {name}", "available_tools": sorted(TOOL_REGISTRY)}

        try:
            return tool(**arguments)
        except TypeError as exc:
            return {"error": f"Invalid arguments for {name}: {exc}", "arguments": arguments}
        except Exception as exc:
            return {"error": f"Tool {name} failed: {exc}", "arguments": arguments}

    def _finalize_after_iteration_limit(self, turn_start: int) -> str:
        if not self._turn_called_tool(turn_start, "write_report"):
            forced_response = self._force_write_report(
                "The tool iteration limit is almost exhausted for the current task. "
                "Do not search or read more sources. Use the observations already collected "
                "and call write_report now with the best possible Markdown report for the current task."
            )
            if forced_response:
                return forced_response

        self.messages.append(
            {
                "role": "user",
                "content": (
                    "You reached the tool iteration limit. Stop calling tools and provide the best "
                    "final answer from the collected observations. If a report was not saved, say so."
                ),
            }
        )

        try:
            final_message = self._chat_completion(use_tools=False)
        except RuntimeError:
            return "Agent stopped: iteration limit reached, and final synthesis failed."

        self.messages.append(final_message)
        content = self._message_content(final_message)
        if content:
            return content
        return "Agent stopped: iteration limit reached without a final answer."

    def _force_write_report(self, instruction: str) -> str | None:
        self.messages.append({"role": "user", "content": instruction})

        try:
            report_message = self._chat_completion(
                use_tools=True,
                tool_choice={
                    "type": "function",
                    "function": {"name": "write_report"},
                },
            )
        except RuntimeError:
            return None

        self.messages.append(report_message)
        tool_calls = report_message.get("tool_calls") or []
        if not tool_calls:
            return None

        for tool_call in tool_calls:
            tool_message = self._handle_tool_call(tool_call)
            self.messages.append(tool_message)

        self.messages.append(
            {
                "role": "user",
                "content": "Now provide a concise final answer with the saved report path.",
            }
        )
        try:
            final_message = self._chat_completion(use_tools=False)
        except RuntimeError:
            return None

        self.messages.append(final_message)
        content = self._message_content(final_message).strip()
        return content or None

    def _turn_called_tool(self, turn_start: int, tool_name: str) -> bool:
        return any(
            message.get("role") == "tool" and message.get("name") == tool_name
            for message in self.messages[turn_start:]
        )

    def _current_task_requires_report(self) -> bool:
        task = (self.current_task or "").lower()
        return any(marker in task for marker in ("збереж", "звіт", "save", "report"))

    def _messages_for_api(self) -> list[Message]:
        if not self.current_task:
            return self.messages

        return [
            *self.messages,
            {
                "role": "system",
                "content": (
                    "Current active user request has highest priority. "
                    "Complete this request, choose tools for this request, and do not continue or overwrite "
                    f"reports from older topics unless explicitly asked. Current request: {self.current_task}"
                ),
            },
        ]

    def _parse_arguments(self, raw_arguments: Any) -> tuple[dict[str, Any], str | None]:
        if raw_arguments is None or raw_arguments == "":
            return {}, None

        if isinstance(raw_arguments, dict):
            return raw_arguments, None

        if not isinstance(raw_arguments, str):
            return {}, f"Tool arguments must be a JSON object or JSON string, got {type(raw_arguments).__name__}."

        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            return {}, f"Invalid JSON arguments: {exc}"

        if not isinstance(parsed, dict):
            return {}, f"Tool arguments must decode to a JSON object, got {type(parsed).__name__}."

        return parsed, None

    def _serialize_tool_result(self, result: ToolResult) -> str:
        if isinstance(result, str):
            text = result
        else:
            text = json.dumps(result, ensure_ascii=False, indent=2)

        return self._shorten(text, settings.max_tool_result_length)

    def _normalize_assistant_message(self, raw_message: Message) -> Message:
        message: Message = {
            "role": "assistant",
            "content": raw_message.get("content") or "",
        }
        tool_calls = raw_message.get("tool_calls")
        if tool_calls:
            message["tool_calls"] = tool_calls
        return message

    def _message_content(self, message: Message) -> str:
        content = message.get("content") or ""
        if isinstance(content, str):
            return (
                content.replace("<|channel>/thought", "")
                .replace("<|channel>", "")
                .strip()
            )
        return json.dumps(content, ensure_ascii=False)

    def _chat_completions_url(self) -> str:
        return f"{settings.base_url.rstrip('/')}/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

    def _shorten(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return f"{value[:limit].rstrip()}... [truncated]"

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)
