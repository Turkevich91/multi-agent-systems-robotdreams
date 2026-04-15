import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura
from ddgs import DDGS
from langchain_core.tools import tool

from config import BASE_DIR, settings
from retriever import RetrievalResult, get_retriever


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


def _format_source(metadata: dict) -> str:
    source = str(metadata.get("source") or Path(str(metadata.get("path", ""))).name or "unknown")
    page = metadata.get("page")
    if page:
        return f"{source}, page {page}"
    return source


def _format_knowledge_results(query: str, results: list[RetrievalResult], rerank_error: str | None) -> str:
    if not results:
        return f"No local knowledge results found for query: {query!r}"

    lines = [f"Found {len(results)} local knowledge chunks for query: {query!r}"]
    if rerank_error:
        lines.append(
            "Note: cross-encoder reranking was unavailable, so results use hybrid BM25+semantic score. "
            f"Reranker error: {_trim_text(rerank_error, 300)}"
        )

    for index, result in enumerate(results, 1):
        score_parts = [f"hybrid={result.hybrid_score:.4f}"]
        if result.rerank_score is not None:
            score_parts.append(f"rerank={result.rerank_score:.4f}")
        if result.semantic_rank is not None:
            score_parts.append(f"semantic_rank={result.semantic_rank}")
        if result.bm25_rank is not None:
            score_parts.append(f"bm25_rank={result.bm25_rank}")

        excerpt = _trim_text(result.content.strip(), settings.max_rag_chars_per_result)
        lines.extend(
            [
                "",
                f"[{index}] Source: {_format_source(result.metadata)}",
                f"Scores: {', '.join(score_parts)}",
                f"Content:\n{excerpt}",
            ]
        )

    return _trim_text("\n".join(lines), settings.max_tool_result_length)


@tool
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


@tool
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


@tool
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


@tool
def knowledge_search(query: str) -> str:
    """Search the local knowledge base using hybrid retrieval + reranking."""
    clean_query = query.strip()
    if not clean_query:
        return "ERROR: empty knowledge base query."

    try:
        retriever = get_retriever()
        results = retriever.search(clean_query)
    except Exception as exc:
        return f"ERROR: local knowledge search failed: {exc}"

    return _format_knowledge_results(clean_query, results, retriever.rerank_error)
