# Course Project: Market Analyst For Agentic AI Developer Tooling

У цьому фінальному проєкті реалізовано мультиагентну систему для аналізу ринку agentic AI developer tools. Система готує decision package для невеликої анонімної AEC/manufacturing software team: sourced market report, expert critic panel feedback, Mermaid decision diagrams і live dashboard.

Проєкт підсумовує технічний стек попередніх домашніх робіт:

- `LangGraph StateGraph` для workflow.
- Qdrant + BM25 + reranking для local RAG.
- Optional read-only `SearchMCP` для web/RAG tools.
- Langfuse tracing, prompt management і evaluator-ready traces.
- FastAPI + SSE backend.
- React/Vite SPA для streaming agent history, HITL critic criteria і Mermaid rendering.
- Mermaid outputs show research results: market entry flow, payback gate, validation timeline, saturation map and expert critic score share.

## Architecture

Основний runtime:

```text
User / SPA / CLI
  -> LangGraph StateGraph
  -> Research Analyst
  -> Critic Role Selector
  -> Human Criteria Gate
  -> Expert Critic Panel
  -> Critic Aggregator
  -> Analyst revision loop
  -> Report Compiler
  -> output/*.md + Mermaid diagrams
```

MCP не є single point of failure. За замовчуванням `COURSE_PROJECT_TOOL_BACKEND=mcp_auto`: система пробує `SearchMCP`, але якщо server не запущений, переходить на direct tools.

## Environment

Root `.env` використовується спільно з попередніми ДЗ.

Рекомендовані значення:

```env
OPENAI_API_KEY=...
COURSE_PROJECT_MODEL_NAME=gpt-5.4-mini
COURSE_PROJECT_OPENAI_BASE_URL=https://api.openai.com/v1

OPENAI_EMBEDDING_API_KEY=...
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

CW_LANGFUSE_PUBLIC_KEY=...
CW_LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com

COURSE_PROJECT_TOOL_BACKEND=mcp_auto
```

`CW_LANGFUSE_*` використовується спеціально для course project, щоб не змішувати traces/prompts/evaluators з домашніми роботами. Якщо ці змінні не задані, код fallback-иться на стандартні `LANGFUSE_PUBLIC_KEY` і `LANGFUSE_SECRET_KEY`.

LM Studio можна використати як fallback через env, але фінальний demo path розрахований на OpenAI API для стабільного structured output.

## Setup

З root репозиторію:

```powershell
uv sync
```

Frontend:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\course-project-market-analyst\frontend
npm install
npm run build
```

## RAG Ingestion

Qdrant має бути запущений локально:

```powershell
docker start qdrant
```

Побудувати collection:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\course-project-market-analyst
uv run python ingest.py
```

Очікувана collection:

```text
course_project_market_analyst_knowledge
```

## Optional SearchMCP

MCP server запускається окремо:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\course-project-market-analyst
uv run python mcp_servers/search_mcp.py
```

Endpoint:

```text
http://127.0.0.1:8911/mcp
```

MCP tools:

- `web_search`
- `read_url`
- `knowledge_search`

MCP resource:

- `resource://market-knowledge-stats`

## CLI Demo

CLI лишений як fallback, щоб проєкт можна було перевірити без UI.

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\course-project-market-analyst
uv run python main.py
```

## SPA Demo

Backend:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\course-project-market-analyst
uv run python api.py
```

Frontend dev server:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\course-project-market-analyst\frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Acceptance Query

```text
Analyze the market for agentic AI developer tools for a small AEC/manufacturing software team. Compare coding agents, IDE copilots, observability/evaluation platforms, and MCP-based integrations. Recommend an adoption roadmap.
```

Expected flow:

1. Analyst prepares sourced draft.
2. Critic Role Selector starts with Financial and Risk roles.
3. UI shows Human Criteria Gate.
4. User approves criteria, edits them, adds a custom critic, or asks AI to suggest an extra critic.
5. Expert Critic Panel runs role-specific critique.
6. Backend persists the approved critic roles for the current run/session.
7. Aggregator decides approve/revise.
8. Compiler saves final report and research-result Mermaid diagrams.

## Evidence

Reviewer-facing files:

- `SUBMISSION_NOTES.md`
- `uml_diagrams/COURSE_PROJECT_MARKET_ANALYST_MERMAID.md`
- `PRESENTATION_NOTES.md`
- `reviewer_artifacts/generated_acceptance_report.md`
- `reviewer_artifacts/e2e_acceptance_trace_summary.md`
- `reviewer_artifacts/sample_market_analysis_report.md`
- `reviewer_artifacts/static_check_summary.md`

Generated runtime output is written to `output/` and ignored by git. The committed generated acceptance report is historical evidence from the full E2E run; current sample/report contract is documented in `reviewer_artifacts/sample_market_analysis_report.md`.
