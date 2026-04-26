"""
Hybrid retrieval module.

Combines semantic search (Qdrant) + BM25 (lexical) + cross-encoder reranking.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import BASE_DIR, settings


CHUNKS_FILENAME = "chunks.json"


@dataclass
class RetrievalResult:
    content: str
    metadata: dict[str, Any]
    hybrid_score: float
    semantic_rank: int | None = None
    bm25_rank: int | None = None
    rerank_score: float | None = None


def _resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def _tokenize(text: str) -> list[str]:
    return re.findall(r"(?u)\b\w+\b", text.lower())


def _doc_key(doc) -> str:
    metadata = getattr(doc, "metadata", {}) or {}
    chunk_id = metadata.get("chunk_id")
    if chunk_id:
        return str(chunk_id)

    source = metadata.get("source", "unknown")
    page = metadata.get("page", "na")
    content = getattr(doc, "page_content", "")
    return f"{source}:{page}:{hash(content)}"


def _build_embeddings():
    from langchain_openai import OpenAIEmbeddings

    kwargs = {
        "model": settings.embedding_model,
        "api_key": settings.resolved_embedding_api_key.get_secret_value(),
        "timeout": settings.request_timeout,
        "max_retries": settings.max_retries,
    }
    if settings.resolved_embedding_base_url:
        kwargs["base_url"] = settings.resolved_embedding_base_url

    return OpenAIEmbeddings(**kwargs)


def _build_qdrant_client():
    from qdrant_client import QdrantClient

    kwargs = {"url": settings.qdrant_url}
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key.get_secret_value()

    return QdrantClient(**kwargs)


class HybridRerankRetriever:
    def __init__(self) -> None:
        self.index_dir = _resolve_project_path(settings.index_dir)
        chunks_path = self.index_dir / CHUNKS_FILENAME

        if not self.index_dir.exists() or not chunks_path.exists():
            raise FileNotFoundError(
                "Knowledge index is missing. Run `python ingest.py` inside "
                f"{BASE_DIR} before using knowledge_search."
            )

        self.client = _build_qdrant_client()
        try:
            collection_exists = self.client.collection_exists(settings.qdrant_collection)
        except Exception as exc:
            raise RuntimeError(
                f"Qdrant is not reachable at {settings.qdrant_url}. "
                "Start Docker Desktop and the qdrant container before using knowledge_search."
            ) from exc

        if not collection_exists:
            raise FileNotFoundError(
                f"Qdrant collection {settings.qdrant_collection!r} is missing. "
                f"Run `python ingest.py` inside {BASE_DIR} first."
            )

        self.embeddings = _build_embeddings()
        self.chunks = self._load_chunks(chunks_path)
        self.bm25 = self._build_bm25(self.chunks)
        self.reranker = None
        self.rerank_error: str | None = None

    def search(self, query: str, *, top_n: int | None = None) -> list[RetrievalResult]:
        clean_query = query.strip()
        if not clean_query:
            return []

        candidates = self._hybrid_candidates(clean_query)
        if not candidates:
            return []

        reranked = self._rerank(clean_query, candidates)
        limit = top_n or settings.rerank_top_n
        return reranked[:limit]

    def invoke(self, query: str) -> list[RetrievalResult]:
        return self.search(query)

    def _load_chunks(self, chunks_path: Path):
        from langchain_core.documents import Document

        raw_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        return [
            Document(
                page_content=item["page_content"],
                metadata=dict(item.get("metadata") or {}),
            )
            for item in raw_chunks
        ]

    def _build_bm25(self, chunks):
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as exc:
            raise RuntimeError(
                "rank_bm25 is required for lexical BM25 search. "
                "Install dependencies from requirements.txt or run `uv sync`."
            ) from exc

        tokenized_chunks = [_tokenize(chunk.page_content) for chunk in chunks]
        return BM25Okapi(tokenized_chunks)

    def _hybrid_candidates(self, query: str) -> list[RetrievalResult]:
        semantic_ranked = self._semantic_search(query)
        bm25_ranked = self._bm25_search(query)

        candidates: dict[str, RetrievalResult] = {}

        for rank, doc in semantic_ranked:
            key = _doc_key(doc)
            result = candidates.setdefault(
                key,
                RetrievalResult(
                    content=doc.page_content,
                    metadata=dict(doc.metadata),
                    hybrid_score=0.0,
                ),
            )
            result.semantic_rank = rank
            result.hybrid_score += settings.semantic_weight * self._rrf(rank)

        for rank, doc in bm25_ranked:
            key = _doc_key(doc)
            result = candidates.setdefault(
                key,
                RetrievalResult(
                    content=doc.page_content,
                    metadata=dict(doc.metadata),
                    hybrid_score=0.0,
                ),
            )
            result.bm25_rank = rank
            result.hybrid_score += settings.bm25_weight * self._rrf(rank)

        return sorted(
            candidates.values(),
            key=lambda item: item.hybrid_score,
            reverse=True,
        )

    def _semantic_search(self, query: str):
        from langchain_core.documents import Document

        query_vector = self.embeddings.embed_query(query)
        response = self.client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            limit=settings.retrieval_top_k,
            with_payload=True,
            with_vectors=False,
        )

        ranked = []
        for rank, point in enumerate(response.points, 1):
            payload = point.payload or {}
            content = str(payload.get("page_content") or "")
            metadata = dict(payload.get("metadata") or {})
            ranked.append((rank, Document(page_content=content, metadata=metadata)))
        return ranked

    def _bm25_search(self, query: str):
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)
        ranked_indexes = sorted(
            range(len(scores)),
            key=lambda index: float(scores[index]),
            reverse=True,
        )

        results = []
        for rank, index in enumerate(ranked_indexes[: settings.retrieval_top_k], 1):
            if float(scores[index]) <= 0:
                continue
            results.append((rank, self.chunks[index]))
        return results

    def _rerank(self, query: str, candidates: list[RetrievalResult]) -> list[RetrievalResult]:
        self.rerank_error = None
        if not settings.enable_reranking:
            return candidates

        try:
            reranker = self._get_reranker()
            pairs = [(query, candidate.content) for candidate in candidates]
            scores = reranker.predict(pairs)
        except Exception as exc:
            self.rerank_error = str(exc)
            return candidates

        for candidate, score in zip(candidates, scores, strict=False):
            candidate.rerank_score = float(score)

        return sorted(
            candidates,
            key=lambda item: (
                item.rerank_score if item.rerank_score is not None else float("-inf"),
                item.hybrid_score,
            ),
            reverse=True,
        )

    def _get_reranker(self):
        if self.reranker is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for cross-encoder reranking. "
                    "Install dependencies from requirements.txt or run `uv sync`."
                ) from exc

            self.reranker = CrossEncoder(settings.reranker_model)

        return self.reranker

    def _rrf(self, rank: int) -> float:
        return 1.0 / (settings.rrf_k + rank)


def get_retriever():
    return _get_cached_retriever()


@lru_cache(maxsize=1)
def _get_cached_retriever() -> HybridRerankRetriever:
    return HybridRerankRetriever()
