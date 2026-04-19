"""
Knowledge ingestion pipeline.

Loads documents from data/, splits them into chunks, generates embeddings,
stores vectors in Qdrant, and saves local chunks for BM25.
"""

from __future__ import annotations

import json
from pathlib import Path

from config import BASE_DIR, settings


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}
CHUNKS_FILENAME = "chunks.json"
MANIFEST_FILENAME = "manifest.json"


def _resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def _load_documents(data_dir: Path):
    from langchain_community.document_loaders import PyPDFLoader, TextLoader

    documents = []
    files = sorted(
        path
        for path in data_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    for path in files:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            loader = PyPDFLoader(str(path))
            loaded = loader.load()
        else:
            loader = TextLoader(str(path), encoding="utf-8", autodetect_encoding=True)
            loaded = loader.load()

        for doc in loaded:
            metadata = dict(doc.metadata)
            metadata["source"] = path.name
            metadata["path"] = str(path.resolve())
            if "page" in metadata:
                metadata["page"] = int(metadata["page"]) + 1
            doc.metadata = metadata

        documents.extend(loaded)

    return documents, files


def _split_documents(documents):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    for index, chunk in enumerate(chunks):
        chunk.metadata = dict(chunk.metadata)
        chunk.metadata["chunk_id"] = f"chunk-{index:06d}"
        chunk.metadata["chunk_index"] = index

    return chunks


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


def _save_chunks(chunks, index_dir: Path) -> None:
    payload = [
        {
            "page_content": chunk.page_content,
            "metadata": dict(chunk.metadata),
        }
        for chunk in chunks
    ]
    (index_dir / CHUNKS_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_qdrant_client():
    from qdrant_client import QdrantClient

    kwargs = {"url": settings.qdrant_url}
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key.get_secret_value()

    return QdrantClient(**kwargs)


def _embed_chunks(chunks, embeddings) -> list[list[float]]:
    vectors: list[list[float]] = []
    total = len(chunks)

    for start in range(0, total, settings.qdrant_batch_size):
        end = min(start + settings.qdrant_batch_size, total)
        texts = [chunk.page_content for chunk in chunks[start:end]]
        vectors.extend(embeddings.embed_documents(texts))
        print(f"Embedded chunks {start + 1}-{end}/{total}")

    return vectors


def _prepare_qdrant_collection(client, vector_size: int) -> None:
    from qdrant_client.models import Distance, VectorParams

    collection = settings.qdrant_collection

    if settings.qdrant_recreate_collection and client.collection_exists(collection):
        client.delete_collection(collection_name=collection)

    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def _upsert_qdrant_points(client, chunks, vectors: list[list[float]]) -> None:
    from qdrant_client.models import PointStruct

    total = len(chunks)
    for start in range(0, total, settings.qdrant_batch_size):
        end = min(start + settings.qdrant_batch_size, total)
        points = [
            PointStruct(
                id=index,
                vector=vectors[index],
                payload={
                    "page_content": chunks[index].page_content,
                    "metadata": dict(chunks[index].metadata),
                },
            )
            for index in range(start, end)
        ]
        client.upsert(
            collection_name=settings.qdrant_collection,
            points=points,
            wait=True,
        )
        print(f"Upserted Qdrant points {start + 1}-{end}/{total}")


def _save_manifest(files: list[Path], chunks_count: int, vector_size: int, index_dir: Path) -> None:
    payload = {
        "vector_store": "qdrant",
        "qdrant_url": settings.qdrant_url,
        "qdrant_collection": settings.qdrant_collection,
        "embedding_model": settings.embedding_model,
        "embedding_base_url": settings.resolved_embedding_base_url,
        "vector_size": vector_size,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "documents": [
            {
                "name": path.name,
                "path": str(path.resolve()),
                "size_bytes": path.stat().st_size,
            }
            for path in files
        ],
        "chunks_count": chunks_count,
    }
    (index_dir / MANIFEST_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def ingest():
    data_dir = _resolve_project_path(settings.data_dir)
    index_dir = _resolve_project_path(settings.index_dir)

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    print(f"Loading documents from: {data_dir}")
    documents, files = _load_documents(data_dir)
    if not documents:
        extensions = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise RuntimeError(f"No supported documents found in {data_dir} ({extensions})")

    print(f"Loaded {len(documents)} document pages/files from {len(files)} source files")

    chunks = _split_documents(documents)
    if not chunks:
        raise RuntimeError("No chunks were produced from the loaded documents")

    print(
        f"Created {len(chunks)} chunks "
        f"(chunk_size={settings.chunk_size}, overlap={settings.chunk_overlap})"
    )

    embeddings = _build_embeddings()
    try:
        vectors = _embed_chunks(chunks, embeddings)
    except Exception as exc:
        raise RuntimeError(
            "Failed to build embeddings for the Qdrant index. Check "
            "OPENAI_EMBEDDING_API_KEY, OPENAI_EMBEDDING_BASE_URL and EMBEDDING_MODEL. "
            "The chat model can stay on LM Studio, but embeddings need an embeddings API."
        ) from exc

    if not vectors:
        raise RuntimeError("Embedding provider returned no vectors")

    vector_size = len(vectors[0])
    print(f"Embedding vector size: {vector_size}")

    client = _build_qdrant_client()
    try:
        _prepare_qdrant_collection(client, vector_size)
        _upsert_qdrant_points(client, chunks, vectors)
    except Exception as exc:
        raise RuntimeError(
            "Failed to write vectors into Qdrant. Start Docker Desktop, then run or start "
            f"the qdrant container reachable at {settings.qdrant_url}."
        ) from exc

    index_dir.mkdir(parents=True, exist_ok=True)
    _save_chunks(chunks, index_dir)
    _save_manifest(files, len(chunks), vector_size, index_dir)

    print(
        f"Saved {len(chunks)} chunks to Qdrant collection "
        f"{settings.qdrant_collection!r} and BM25 chunks to: {index_dir.resolve()}"
    )


def main() -> None:
    try:
        ingest()
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
