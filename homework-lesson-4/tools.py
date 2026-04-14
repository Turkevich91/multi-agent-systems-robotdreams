import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import trafilatura
from ddgs import DDGS

from config import BASE_DIR, settings


ToolResult = str | list[dict[str, str]] | dict[str, Any]


def _trim_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text

    suffix = "\n\n[TRUNCATED]"
    if limit <= len(suffix):
        return text[:limit]

    return f"{text[: limit - len(suffix)].rstrip()}{suffix}"


def _safe_report_filename(filename: str) -> str:
    raw_name = Path(filename).name.strip()
    if not raw_name:
        raw_name = "research_report.md"

    safe_name = re.sub(r"[^A-Za-z0-9._ -]+", "_", raw_name).strip(" .")
    if not safe_name:
        safe_name = "research_report.md"

    path = Path(safe_name)
    if path.suffix.lower() != ".md":
        stem = path.stem or "research_report"
        safe_name = f"{stem}.md"

    return safe_name


def _download_url(url: str) -> str | None:
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        return downloaded

    try:
        return _download_url_with_httpx(url, verify=True)
    except httpx.HTTPError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise

        return _download_url_with_httpx(url, verify=False)


def _download_url_with_httpx(url: str, verify: bool) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    with httpx.Client(
        follow_redirects=True,
        timeout=settings.request_timeout,
        headers=headers,
        verify=verify,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def write_report(filename: str, content: str) -> str:
    """Save the final Markdown research report into the local output directory."""
    try:
        output_dir = BASE_DIR / settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        target_path = output_dir / _safe_report_filename(filename)
        target_path.write_text(content, encoding="utf-8")
        return f"Report saved to: {target_path.resolve()}"
    except OSError as exc:
        return f"ERROR: failed to write report: {exc}"


def web_search(query: str) -> list[dict[str, str]]:
    """Search the web for pages relevant to a research question."""
    clean_query = query.strip()
    if not clean_query:
        return [{"error": "Empty search query."}]

    try:
        with DDGS() as ddgs:
            raw_results = list(
                ddgs.text(clean_query, max_results=settings.max_search_results)
            )
    except Exception as exc:
        return [{"error": f"Search failed: {exc}", "query": clean_query}]

    results: list[dict[str, str]] = []
    for item in raw_results[: settings.max_search_results]:
        results.append(
            {
                "title": _trim_text(str(item.get("title", "")).strip(), 200),
                "url": str(item.get("href") or item.get("url") or "").strip(),
                "snippet": _trim_text(str(item.get("body", "")).strip(), 700),
            }
        )

    if not results:
        return [{"error": "No search results found.", "query": clean_query}]

    return results


def read_url(url: str) -> str:
    """Fetch and extract readable text from a web page URL."""
    clean_url = url.strip()
    parsed = urlparse(clean_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return f"ERROR: invalid URL: {url!r}. Use a full http:// or https:// URL."

    try:
        downloaded = _download_url(clean_url)
        if not downloaded:
            return f"ERROR: could not download URL: {clean_url}"

        text = trafilatura.extract(downloaded)
    except Exception as exc:
        return f"ERROR: failed to read URL {clean_url}: {exc}"

    if not text or not text.strip():
        return f"ERROR: no readable article text extracted from URL: {clean_url}"

    return _trim_text(f"URL: {clean_url}\n\n{text.strip()}", settings.max_url_content_length)


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for pages relevant to a research question. "
                "Returns a short list of title/url/snippet objects."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to send to the web search engine.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": (
                "Fetch and extract readable article text from a full http:// or https:// URL. "
                "Use after web_search when a result looks relevant."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL of the page to read.",
                    }
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_report",
            "description": "Save the final Markdown research report into the local output directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Safe Markdown filename, for example rag_comparison.md.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete Markdown report content.",
                    },
                },
                "required": ["filename", "content"],
                "additionalProperties": False,
            },
        },
    },
]


TOOL_REGISTRY = {
    "web_search": web_search,
    "read_url": read_url,
    "write_report": write_report,
}
