# Домашнє завдання 9: MCP + ACP поверх мультиагентної RAG-системи

## Короткий підсумок

Реалізовано протокольну версію ДЗ 8: той самий research workflow `Supervisor -> Planner -> Researcher -> Critic -> save_report`, але межі між компонентами винесено в стандартизовані протоколи з Лекції 9.

- **MCP / vertical integration:** `SearchMCP` (`8901`) надає `web_search`, `read_url`, `knowledge_search` і `resource://knowledge-base-stats`; `ReportMCP` (`8902`) надає `save_report` і `resource://output-dir`.
- **ACP / horizontal integration:** `ACP server` (`8903`) публікує агентів `planner`, `researcher`, `critic`.
- **Local Supervisor:** лишається локальним LangChain `create_agent`, але делегує спеціалістам через `acp_sdk.client.Client`.
- **HITL:** локальний `save_report` wrapper захищений `HumanInTheLoopMiddleware`; тільки після `approve` він викликає `ReportMCP.save_report`.
- **RAG:** Qdrant + BM25 + reranking з ДЗ 8 пере використано з окремою collection `homework_lesson_9_knowledge`.

Canonical save path для ДЗ 9: `Supervisor -> local save_report tool -> HITL approve/edit/reject -> ReportMCP -> output/*.md`. Direct fallback-save не є основним workflow і не використовується як canonical path.

## Для перевіряючого: що дивитися без запуску

### Рекомендований порядок перегляду

1. `README.md` — короткий опис задачі, запуску і протокольної архітектури.
2. `SUBMISSION_NOTES.md` → секція **Requirement -> Code map** — де саме в коді виконана кожна вимога.
3. `SUBMISSION_NOTES.md` → секція **Намір - Дія - Висновок** — покрокове пояснення, чому зроблено саме так і який результат отримано.
4. `uml_diagrams/MCP_ACP_MERMAID.md` — 7 Mermaid-діаграм: архітектура, MCP, ACP, sequence, HITL, startup, reviewer evidence map.
5. `output/hw9_protocol_trace_summary.md` — trace реальних smoke/e2e перевірок.
6. `output/hw9_rag_comparison_report.md` — фінальний звіт, збережений через `edit -> approve` у HITL.
7. `output/dinosaurs_among_us_report.md` — додатковий web-first research-звіт, де RAG використовується опційно як фон.
8. `output/ai_model_claims_report.md` — додатковий current-news research-звіт з перевіркою через зовнішні джерела.

### Requirement -> Code map

| Очікування ДЗ | Де видно | Що перевірити |
|---|---|---|
| 2 MCP servers | `mcp_servers/search_mcp.py:14-39`, `mcp_servers/report_mcp.py:14-27` | `FastMCP(name="SearchMCP")`, `FastMCP(name="ReportMCP")`, tools/resources, порти `8901/8902` |
| SearchMCP tools/resources | `mcp_servers/search_mcp.py:17-39`, `shared_tools.py:117-176` | `web_search`, `read_url`, `knowledge_search`, `resource://knowledge-base-stats` |
| ReportMCP save tool/resource | `mcp_servers/report_mcp.py:17-27`, `shared_tools.py:179-226` | `save_report(filename, content)`, safe filename/output handling, `resource://output-dir` |
| MCP tools -> LangChain tools | `mcp_utils.py:35-68` | `mcp_tools_to_langchain(...)` будує `StructuredTool` з MCP JSON schema |
| 1 ACP server з 3 agents | `acp_server.py:10-47` | `@server.agent(name="planner")`, `researcher`, `critic` |
| ACP agents використовують SearchMCP | `agents/common.py:59-67`, `agents/planner.py:45-55`, `agents/research.py:7-18`, `agents/critic.py:44-54` | кожен агент відкриває `fastmcp.Client(settings.search_mcp_url)` і працює через MCP tools |
| Planner structured output | `agents/planner.py:48-53`, `schemas.py` | `response_format=ToolStrategy(ResearchPlan)` |
| Critic structured output | `agents/critic.py:47-52`, `schemas.py` | `response_format=ToolStrategy(CritiqueResult)` |
| Researcher виконує план через read-only tools | `agents/research.py:7-24`, `config.py:154-169` | `web_search`, `read_url`, `knowledge_search`; без запису файлів |
| Supervisor делегує через ACP | `supervisor.py:39-75` | `ACPClient.run_sync(...)` у tools `delegate_to_planner/researcher/critic` |
| save_report проходить через ReportMCP | `supervisor.py:79-82` | локальний wrapper викликає `MCPClient(settings.report_mcp_url).call_tool("save_report", ...)` |
| HITL стоїть саме на локальному save_report | `supervisor.py:89-105` | `HumanInTheLoopMiddleware(interrupt_on={"save_report": True})` + `InMemorySaver()` |
| REPL підтримує approve/edit/reject | `main.py:189-234` | `approve` resume, `edit` як feedback-driven revise, `reject` як cancellation |
| Reject не запускає повторний save | `main.py:228-239` | `trace["save_cancelled"]` зупиняє `_ensure_report_saved(...)` |
| Окрема Qdrant collection для ДЗ 9 | `config.py:57-58`, `ingest.py:130-252`, `retriever.py:93-195` | `homework_lesson_9_knowledge`, 464 chunks після ingestion |
| Окремі protocol endpoints | `config.py:69-107` | `SearchMCP :8901`, `ReportMCP :8902`, `ACP :8903` |

## Намір - Дія - Висновок

| Намір | Дія | Висновок |
|---|---|---|
| Зрозуміти, що саме додає Лекція 9 | Переглянуто `lesson-9/lesson-9.ipynb`: MCP = агент до tools/data, ACP = агент до агента | Для ДЗ 9 треба не переписати RAG, а винести tools у MCP, а specialist agents у ACP |
| Пере використати робочий фундамент ДЗ 8 | Перенесено RAG-базу: `ingest.py`, `retriever.py`, `schemas.py`, `data/*.pdf` | Поведінка Plan -> Research -> Critique -> Report лишилася знайомою, змінилася тільки комунікаційна оболонка |
| Ізолювати дані ДЗ 9 від ДЗ 8 | У `config.py` задано collection `homework_lesson_9_knowledge` | Qdrant points не змішуються між домашками; після clean Windows ingestion відтворює стан локально |
| Не дублювати tool logic між MCP і LangChain | Створено `shared_tools.py` з plain implementations без `@tool` decorators | MCP servers можуть експортувати ті самі дії, а runtime не залежить від LangChain wrappers |
| Реалізувати MCP для пошуку й RAG | Створено `SearchMCP` з `web_search`, `read_url`, `knowledge_search` і `resource://knowledge-base-stats` | Усі read-only research tools доступні через MCP, як у лекційному ProjectTracker прикладі |
| Реалізувати MCP для запису звіту | Створено `ReportMCP` з `save_report` і `resource://output-dir` | Write-operation винесено в окремий MCP service, але доступ до нього контролює локальний HITL |
| Підключити MCP tools до LangChain agents | Додано `mcp_tools_to_langchain(...)`, який бере MCP schema і створює `StructuredTool` | ACP agents можуть використовувати MCP tools як звичайні LangChain tools без копіювання функцій |
| Реалізувати Planner як ACP agent | `planner` підключається до SearchMCP і повертає JSON `ResearchPlan` через `ToolStrategy` | Supervisor отримує структурований план через ACP, а не локальний function call |
| Реалізувати Researcher як ACP agent | `researcher` використовує SearchMCP tools для виконання плану й збору джерел | Дослідження виконується remote-agent стилем, але evidence лишається видимим |
| Реалізувати Critic як ACP agent | `critic` перевіряє findings через SearchMCP і повертає `CritiqueResult` | Збережено evaluator-optimizer loop: `APPROVE` або `REVISE` з конкретними revision requests |
| Захиститися від слабкого local structured-output | Для Planner/Critic лишено JSON-normalization fallback усередині agent runners | У нормальних умовах працює `ToolStrategy`; fallback лише стабілізує локальну LM Studio модель |
| Реалізувати ACP server discovery/delegation | `acp_server.py` публікує `planner`, `researcher`, `critic` через `@server.agent` | Supervisor може робити discovery/call agents як у лекції, але з нашими ролями ДЗ |
| Реалізувати локального Supervisor | `supervisor.py` створює `create_agent` з tools `delegate_to_*` і `save_report` | Оркестратор керує порядком `plan -> research -> critique -> save_report`, а не agent-to-agent логікою всередині себе |
| Зберегти HITL requirement | `HumanInTheLoopMiddleware(interrupt_on={"save_report": True})` стоїть на локальному tool | Жоден файл не пишеться без `approve`; `edit` запускає переписування, `reject` скасовує збереження |
| Зробити запуск відтворюваним | Додано entrypoints `search_mcp.py`, `report_mcp.py`, `acp_server.py`, `main.py` і helper `scripts/start_hw9_servers.ps1` | Перевіряючий може запускати вручну по README або підняти 3 сервери helper-ом |
| Підготувати reviewer evidence без запуску | Додано `output/hw9_protocol_trace_summary.md`, `output/hw9_rag_comparison_report.md`, `output/dinosaurs_among_us_report.md`, `output/ai_model_claims_report.md` як intentional artifacts | Reviewer бачить реальний trace, canonical RAG report і два додаткові сценарії, навіть якщо не запускає LM Studio/Qdrant |
| Перевірити повний interactive flow | Проведено e2e run із запитом про naive RAG / sentence-window / parent-child retrieval | `edit -> approve` зберіг фінальний report через ReportMCP; `reject` перевірено окремо і cancellation не пише файл |
| Виправити знайдений під час тестів edge case | Після live reject-run додано `save_cancelled` guard у `main.py` | `_ensure_report_saved(...)` більше не намагається повторно зберегти після явного `reject` |
| Пояснити архітектуру візуально | Оновлено `uml_diagrams/MCP_ACP_MERMAID.md` під фактичний workflow | Mermaid показує саме `Supervisor -> HITL -> ReportMCP`, а не прямий запис в обхід approval |

## Команди запуску

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-9

# 1. Qdrant
docker start qdrant

# 2. Ingestion
uv run python ingest.py

# 3. Servers
uv run python mcp_servers/search_mcp.py
uv run python mcp_servers/report_mcp.py
uv run python acp_server.py

# 4. Supervisor
uv run python main.py
```

Helper:

```powershell
.\scripts\start_hw9_servers.ps1
```

## Test Plan

### Static/import

```powershell
uv run python -m compileall .
uv run python -c "import fastmcp, acp_sdk; from schemas import ResearchPlan, CritiqueResult; print('ok')"
```

### Qdrant/RAG

```powershell
uv run python ingest.py
uv run python -c "from qdrant_client import QdrantClient; from config import settings; c=QdrantClient(url=settings.qdrant_url); print(c.count(collection_name=settings.qdrant_collection, exact=True).count)"
```

Очікується `464`.

### MCP

Після старту `SearchMCP` і `ReportMCP` перевірити через `fastmcp.Client`:

- `SearchMCP.list_tools()` -> `web_search`, `read_url`, `knowledge_search`.
- `SearchMCP.list_resources()` -> `resource://knowledge-base-stats`.
- `ReportMCP.list_tools()` -> `save_report`.
- `ReportMCP.list_resources()` -> `resource://output-dir`.

### ACP

Після старту `acp_server.py` перевірити через `acp_sdk.client.Client`:

- discovery повертає `planner`, `researcher`, `critic`;
- `planner` повертає валідний `ResearchPlan`;
- `researcher` повертає findings з джерелами;
- `critic` повертає валідний `CritiqueResult`.

### End-to-end real run

```text
Compare naive RAG, sentence-window retrieval, and parent-child retrieval. Write a report.
```

Очікуваний trace:

1. `delegate_to_planner(...)` -> ACP `planner` -> MCP `SearchMCP`.
2. `delegate_to_researcher(...)` -> ACP `researcher` -> MCP `SearchMCP`.
3. `delegate_to_critic(...)` -> ACP `critic` -> MCP `SearchMCP`.
4. Якщо `REVISE`, Supervisor робить не більше 2 revision rounds.
5. `save_report(...)` -> HITL interrupt.
6. `approve` -> `ReportMCP` writes `output/*.md`.
7. `edit` -> Supervisor revises and calls `save_report` again.
8. `reject` -> saving is cancelled.

## Reviewer Artifacts

| Файл | Що демонструє |
|---|---|
| `output/hw9_protocol_trace_summary.md` | фактичний trace smoke-перевірок, protocol discovery, ACP agent checks, e2e HITL scenarios |
| `output/hw9_rag_comparison_report.md` | реальний фінальний Markdown-звіт, збережений після `edit -> approve` через Supervisor/HITL/ReportMCP |
| `output/dinosaurs_among_us_report.md` | додатковий research-звіт, де система йде у web/read_url за науковим контекстом, а RAG лишається опційним джерелом |
| `output/ai_model_claims_report.md` | додатковий current-news звіт, де система перевіряє сучасні claims через зовнішні джерела |

Ці файли додані в Git вручну як виняток для ревʼю, без розширення `.gitignore` під кожен artifact. Нові локальні `output/*.md` після інших прогонів лишаються ignored.

## Verified So Far

- `uv run python -m compileall .` passed.
- `import fastmcp, acp_sdk; from schemas import ResearchPlan, CritiqueResult` passed.
- `from supervisor import supervisor` passed.
- Qdrant health: `healthz check passed`.
- `uv run python ingest.py`: 464 chunks, collection `homework_lesson_9_knowledge`.
- Qdrant count check: `464`.
- `knowledge_search_impl("retrieval augmented generation")`: returned local RAG chunks.
- Protocol smoke:
  - SearchMCP tools: `knowledge_search`, `read_url`, `web_search`.
  - SearchMCP resources: `resource://knowledge-base-stats`.
  - ReportMCP tools: `save_report`.
  - ReportMCP resources: `resource://output-dir`.
  - ACP agents: `planner`, `researcher`, `critic`.
- MCP -> LangChain converter smoke: converted all SearchMCP tools and invoked `web_search`.
- ACP agent smoke:
  - Planner returned valid `ResearchPlan` JSON.
  - Researcher returned RAG findings.
  - Critic returned valid `CritiqueResult` JSON via local-model fallback.
- Full interactive Supervisor run:
  - `edit` path: supervisor revised the report and called `save_report` again.
  - `approve` path: `hw9_rag_comparison_report.md` saved through ReportMCP.
  - `reject` path: cancellation confirmed without save.
- Additional reviewer runs:
  - `dinosaurs_among_us_report.md`: web-first research, RAG optional/background.
  - `ai_model_claims_report.md`: current-news research with external source verification.
- Bug found during live reject run and fixed:
  - `_ensure_report_saved(...)` no longer retries after explicit user reject.

## Acceptance Checklist

- 2 MCP servers реалізовано.
- MCP tools і resources присутні.
- 1 ACP server з 3 agents реалізовано.
- ACP agents підключаються до SearchMCP.
- MCP tools конвертуються в LangChain tools.
- Planner і Critic використовують `response_format=ToolStrategy(...)`.
- Supervisor делегує agents через ACP.
- Supervisor `save_report` іде через ReportMCP.
- HITL стоїть на локальному `save_report`.
- `approve`, `edit`, `reject` перевірені в interactive REPL.
- Qdrant collection окрема: `homework_lesson_9_knowledge`.
- Direct fallback-save не є canonical workflow.
- Reviewer artifacts додані вручну попри загальний ignore для нових `output/*.md`.
