from __future__ import annotations

from langchain_core.tools import tool

from tool_impl import knowledge_search_impl, read_url_impl, web_search_impl


@tool
def web_search(query: str) -> list[dict[str, str]]:
    """Search the web for pages relevant to a market analysis question."""
    return web_search_impl(query)


@tool
def read_url(url: str) -> str:
    """Fetch and extract readable text from a web page URL."""
    return read_url_impl(url)


@tool
def knowledge_search(query: str) -> str:
    """Search the local market-analysis knowledge base."""
    return knowledge_search_impl(query)
