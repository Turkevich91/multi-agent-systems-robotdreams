from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmcp import FastMCP

from config import settings
from tool_impl import knowledge_base_stats, knowledge_search_impl, read_url_impl, web_search_impl


mcp = FastMCP(name="CourseProjectSearchMCP")


@mcp.tool
def web_search(query: str) -> list[dict[str, str]]:
    """Search the web for market analysis sources."""
    return web_search_impl(query)


@mcp.tool
def read_url(url: str) -> str:
    """Read a public web page and extract article text."""
    return read_url_impl(url)


@mcp.tool
def knowledge_search(query: str) -> str:
    """Search the local Qdrant/BM25 market-analysis knowledge base."""
    return knowledge_search_impl(query)


@mcp.resource("resource://market-knowledge-stats")
def market_knowledge_stats_resource() -> str:
    """Knowledge base collection, index and Qdrant point statistics."""
    return json.dumps(knowledge_base_stats(), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print(f"CourseProjectSearchMCP running at {settings.resolved_search_mcp_url}")
    asyncio.run(
        mcp.run_async(
            transport="streamable-http",
            host=settings.host,
            port=settings.search_mcp_port,
        )
    )
