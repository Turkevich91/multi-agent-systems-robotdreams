import json
import re
from typing import Any

from fastmcp import Client

from config import settings
from mcp_utils import mcp_tools_to_langchain


def last_message_text(result: dict) -> str:
    messages = result.get("messages", [])
    if not messages:
        return ""
    content = getattr(messages[-1], "content", "")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(block))
        return "\n".join(part for part in parts if part)
    return str(content)


def json_from_text(text: str) -> dict[str, Any] | None:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)

    try:
        loaded = json.loads(clean)
        return loaded if isinstance(loaded, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
    if not match:
        return None

    try:
        loaded = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


async def load_search_tools(include: set[str] | None = None):
    client = Client(settings.search_mcp_url)
    await client.__aenter__()
    try:
        mcp_tools = await client.list_tools()
        if include:
            mcp_tools = [tool for tool in mcp_tools if tool.name in include]
        lc_tools = mcp_tools_to_langchain(mcp_tools, client)
        return client, lc_tools
    except Exception:
        await client.__aexit__(None, None, None)
        raise
