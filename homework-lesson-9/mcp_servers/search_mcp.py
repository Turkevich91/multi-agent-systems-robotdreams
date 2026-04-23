import asyncio
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastmcp import FastMCP

from config import settings
from shared_tools import knowledge_base_stats, knowledge_search_impl, read_url_impl, web_search_impl


mcp = FastMCP(name="SearchMCP")


@mcp.tool
def web_search(query: str) -> list[dict[str, str]]:
    """Search the web for pages relevant to a research question."""
    return web_search_impl(query)


@mcp.tool
def read_url(url: str) -> str:
    """Fetch and extract readable text from a web page URL."""
    return read_url_impl(url)


@mcp.tool
def knowledge_search(query: str) -> str:
    """Search the local Qdrant/BM25 knowledge base with reranking."""
    return knowledge_search_impl(query)


@mcp.resource("resource://knowledge-base-stats")
def knowledge_base_stats_resource() -> str:
    """Knowledge base collection, index and Qdrant point statistics."""
    return json.dumps(knowledge_base_stats(), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print(f"SearchMCP running at {settings.search_mcp_url}")
    asyncio.run(
        mcp.run_async(
            transport="streamable-http",
            host=settings.host,
            port=settings.search_mcp_port,
        )
    )
