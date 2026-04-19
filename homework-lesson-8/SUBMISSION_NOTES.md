# Homework Lesson 8: Multi-Agent Research System

## Summary

This implementation extends the lesson 5 Research Agent into a multi-agent system:

```text
User -> Supervisor -> Planner -> Researcher -> Critic -> save_report
                         ^          |          |
                         |          +----------+
                         |        revision loop
```

The system keeps the lesson 5 RAG stack: Qdrant semantic search, BM25 lexical search, and optional cross-encoder reranking. Lesson 8 adds structured Planner/Critic outputs, subagents-as-tools, and HITL approval before writing reports.

## Clean Windows Bootstrap

After a fresh Windows install, Docker Desktop must be running before Qdrant commands work.

```powershell
docker --version
docker ps
```

If Docker is running, create Qdrant:

```powershell
docker run -d --name qdrant `
  -p 6333:6333 `
  -p 6334:6334 `
  -v qdrant_storage:/qdrant/storage `
  qdrant/qdrant:latest
```

If the container already exists:

```powershell
docker start qdrant
```

Check health:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:6333/healthz
```

## Environment

The chat model can run through LM Studio:

```env
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
MODEL_NAME=google/gemma-4-26b-a4b
```

Embeddings need an embeddings-compatible endpoint. If the chat endpoint is local, the code defaults embeddings to `https://api.openai.com/v1` unless `OPENAI_EMBEDDING_BASE_URL` is set.

## Commands

Run ingestion:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-8
uv run python ingest.py
```

Check Qdrant count:

```powershell
uv run python -c "from qdrant_client import QdrantClient; from config import settings; c=QdrantClient(url=settings.qdrant_url); print(c.count(collection_name=settings.qdrant_collection, exact=True).count)"
```

Smoke-test RAG:

```powershell
uv run python -c "from tools import knowledge_search; print(knowledge_search.invoke({'query': 'retrieval augmented generation'})[:1000])"
```

Run the REPL:

```powershell
uv run python main.py
```

Example final query:

```text
Compare naive RAG, sentence-window retrieval, and parent-child retrieval. Write a report.
```

## Acceptance Checklist

- `schemas.py` defines `ResearchPlan` and `CritiqueResult`.
- Planner and Critic use `response_format=ToolStrategy(...)`.
- Supervisor always follows Plan -> Research -> Critique before `save_report`.
- Critic can request up to 2 research revisions.
- `save_report` is protected by `HumanInTheLoopMiddleware`.
- `approve` saves the report, `edit` sends feedback for a revised save attempt, and `reject` cancels saving.
