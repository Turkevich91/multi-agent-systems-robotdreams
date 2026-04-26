from __future__ import annotations

import asyncio
import json
from typing import Any

from config import settings
from tool_impl import knowledge_search_impl, read_url_impl, web_search_impl


class MCPBackendUnavailable(RuntimeError):
    pass


def mcp_result_to_text(result: Any) -> str:
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False, indent=2)

    content = getattr(result, "content", None)
    if content:
        parts: list[str] = []
        for block in content:
            text = getattr(block, "text", None)
            parts.append(str(text if text is not None else block))
        return "\n".join(parts)

    return str(result)


async def _call_mcp_tool_async(name: str, arguments: dict[str, Any]) -> Any:
    from fastmcp import Client

    async with Client(settings.resolved_search_mcp_url) as client:
        return await client.call_tool(name, arguments)


def _call_mcp_tool(name: str, arguments: dict[str, Any]) -> Any:
    try:
        return asyncio.run(_call_mcp_tool_async(name, arguments))
    except RuntimeError as exc:
        raise MCPBackendUnavailable(str(exc)) from exc
    except Exception as exc:
        raise MCPBackendUnavailable(str(exc)) from exc


class SearchTools:
    """Read-only research tool facade with optional MCP transport."""

    def __init__(self, backend: str | None = None) -> None:
        self.backend = (backend or settings.tool_backend).strip().lower()
        if self.backend not in {"direct", "mcp_auto", "mcp_required"}:
            self.backend = "mcp_auto"

    def web_search(self, query: str) -> list[dict[str, str]]:
        if self.backend == "direct":
            return web_search_impl(query)

        try:
            result = _call_mcp_tool("web_search", {"query": query})
            structured = getattr(result, "structured_content", None)
            if isinstance(structured, list):
                return structured
            text = mcp_result_to_text(result)
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else [{"result": text}]
        except Exception as exc:
            if self.backend == "mcp_required":
                raise
            return [{"warning": f"SearchMCP unavailable, used direct web_search. Error: {exc}"}] + web_search_impl(query)

    def read_url(self, url: str) -> str:
        if self.backend == "direct":
            return read_url_impl(url)

        try:
            return mcp_result_to_text(_call_mcp_tool("read_url", {"url": url}))
        except Exception as exc:
            if self.backend == "mcp_required":
                raise
            return f"WARNING: SearchMCP unavailable, used direct read_url. Error: {exc}\n\n{read_url_impl(url)}"

    def knowledge_search(self, query: str) -> str:
        if self.backend == "direct":
            return knowledge_search_impl(query)

        try:
            return mcp_result_to_text(_call_mcp_tool("knowledge_search", {"query": query}))
        except Exception as exc:
            if self.backend == "mcp_required":
                raise
            return (
                "WARNING: SearchMCP unavailable, used direct knowledge_search. "
                f"Error: {exc}\n\n{knowledge_search_impl(query)}"
            )


search_tools = SearchTools()
