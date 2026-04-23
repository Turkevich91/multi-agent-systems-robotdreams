# Домашнє завдання 9: MCP + ACP для мультиагентної RAG-системи

ДЗ 9 розширює готову систему з `homework-lesson-8`: той самий цикл `Plan -> Research -> Critique -> Report`, але інструменти і агенти винесені за протокольні межі.

- **MCP**: інструменти і read-only resources.
- **ACP**: agent-to-agent delegation.
- **Supervisor**: локальний LangChain agent, який оркеструє ACP agents і захищає запис через HITL.

## Reviewer quick pass

Якщо перевіряючий не хоче запускати LM Studio, Docker/Qdrant і три сервери, основний evidence map зібрано тут:

- `SUBMISSION_NOTES.md` — коротка карта вимог, команди запуску, acceptance checklist і trace реального прогону.
- `uml_diagrams/MCP_ACP_MERMAID.md` — архітектура MCP/ACP, sequence flow, HITL і startup map.
- `supervisor.py` — локальний Supervisor з tools `delegate_to_planner`, `delegate_to_researcher`, `delegate_to_critic`, `save_report`.
- `acp_server.py` — один ACP server з агентами `planner`, `researcher`, `critic`.
- `mcp_servers/` — два MCP servers: `SearchMCP` і `ReportMCP`.

Після реальних прогонів у `output/` залишено малий reviewer artifact set: trace summary, основний RAG comparison report і два додаткові research-звіти, які демонструють web-first/current-news сценарії.

Файли для швидкого перегляду: `output/hw9_protocol_trace_summary.md`, `output/hw9_rag_comparison_report.md`, `output/dinosaurs_among_us_report.md`, `output/ai_model_claims_report.md`.

## Архітектура

```text
User (main.py REPL)
  |
  v
Local Supervisor Agent
  |
  +-- delegate_to_planner(...)    -> ACP 8903 -> Planner Agent    -> MCP 8901 SearchMCP
  +-- delegate_to_researcher(...) -> ACP 8903 -> Research Agent   -> MCP 8901 SearchMCP
  +-- delegate_to_critic(...)     -> ACP 8903 -> Critic Agent     -> MCP 8901 SearchMCP
  |
  +-- save_report(...)            -> HITL -> MCP 8902 ReportMCP -> output/*.md
```

## Endpoints

| Endpoint | Port | Role |
|---|---:|---|
| `SearchMCP` | `8901` | `web_search`, `read_url`, `knowledge_search`, `resource://knowledge-base-stats` |
| `ReportMCP` | `8902` | `save_report`, `resource://output-dir` |
| `ACP server` | `8903` | `planner`, `researcher`, `critic` |

## Environment

Використовується root `.env` з курсу. Chat model іде в LM Studio, embeddings — в OpenAI-compatible embeddings endpoint:

```env
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
MODEL_NAME=google/gemma-4-26b-a4b
TEMPERATURE=0.2
REQUEST_TIMEOUT=120
MAX_RETRIES=1
```

Якщо `OPENAI_BASE_URL` локальний, `config.py` автоматично використовує `https://api.openai.com/v1` для embeddings, якщо не задано `OPENAI_EMBEDDING_BASE_URL`.

## Запуск

### 1. Qdrant

```powershell
docker start qdrant

# або після чистої Windows:
docker run -d --name qdrant `
  -p 6333:6333 `
  -p 6334:6334 `
  -v qdrant_storage:/qdrant/storage `
  qdrant/qdrant:latest
```

### 2. Ingestion

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-9
uv run python ingest.py
```

Очікувана collection: `homework_lesson_9_knowledge`.

### 3. MCP + ACP servers

Окремими терміналами:

```powershell
uv run python mcp_servers/search_mcp.py
uv run python mcp_servers/report_mcp.py
uv run python acp_server.py
```

Або helper:

```powershell
.\scripts\start_hw9_servers.ps1
```

### 4. Supervisor REPL

```powershell
uv run python main.py
```

Приклад запиту:

```text
Compare naive RAG, sentence-window retrieval, and parent-child retrieval. Write a report.
```

## HITL

`save_report` — це локальний Supervisor tool, захищений `HumanInTheLoopMiddleware`. Сам запис після approve виконується через `ReportMCP`.

Підтримуються три дії:

- `approve` — виконати `save_report` через ReportMCP.
- `edit` — передати feedback Supervisor, переробити звіт і знову викликати `save_report`.
- `reject` — скасувати збереження.

Direct fallback-save не переноситься як основний workflow. Якщо локальна модель забула викликати `save_report`, `main.py` робить тільки reminder/retry через Supervisor, щоб canonical path лишався HITL + ReportMCP.

## Static Checks

```powershell
uv run python -m compileall .
uv run python -c "import fastmcp, acp_sdk; from schemas import ResearchPlan, CritiqueResult; print('ok')"
```

## Project Structure

```text
homework-lesson-9/
├── main.py
├── supervisor.py
├── acp_server.py
├── mcp_servers/
│   ├── search_mcp.py
│   └── report_mcp.py
├── agents/
│   ├── planner.py
│   ├── research.py
│   └── critic.py
├── shared_tools.py
├── mcp_utils.py
├── config.py
├── schemas.py
├── retriever.py
├── ingest.py
├── scripts/start_hw9_servers.ps1
├── SUBMISSION_NOTES.md
└── uml_diagrams/MCP_ACP_MERMAID.md
```
