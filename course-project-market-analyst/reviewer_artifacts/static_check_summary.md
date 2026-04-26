# Static Check Summary

Цей файл існує для перевіряючого як короткий журнал технічної валідації. Він не замінює live demo, але показує, які частини проєкту вже перевірені без ручного запуску повного agent workflow.

## Перевірки

| Команда | Статус | Висновок |
|---|---|---|
| `uv add fastapi>=0.115.0` | Passed | Backend dependency додано у root `pyproject.toml` і `uv.lock`. |
| `npm install` у `frontend/` | Passed | Node dependencies встановлені, `node_modules/` і `dist/` не комітяться. |
| `npm run build` у `frontend/` | Passed | React/Vite/TypeScript dashboard збирається у production build. |
| `uv run python -m compileall -q -x "frontend[\\/](node_modules|dist)" course-project-market-analyst` | Passed | Python files компілюються без syntax errors, без шуму від frontend dependencies. |
| `npm audit --omit=dev` у `frontend/` | Advisory noted | `mermaid` має transitive moderate advisory у `uuid`; автоматичний fix пропонує breaking downgrade, тому UI залишено на актуальному Mermaid і ввімкнено `securityLevel: "strict"`. |
| `uv run python ingest.py` | Passed | Створено 8 chunks і Qdrant collection `course_project_market_analyst_knowledge`. |
| Qdrant count smoke | Passed | Collection повернула `8` points. |
| Direct `knowledge_search` smoke | Passed | Local RAG повернув 4 chunks для запиту про MCP/Langfuse developer tooling. |
| Optional `SearchMCP` smoke | Passed | `list_tools` повернув `web_search`, `read_url`, `knowledge_search`; resource `resource://market-knowledge-stats` доступний. |
| `uv run python bootstrap_langfuse.py` | Passed | Course-project prompts створені/оновлені в Langfuse prompt management. |
| Direct OpenAI model smoke | Passed | `gpt-5.4-mini` відповів через `https://api.openai.com/v1`; course-project chat backend більше не наслідує LM Studio `OPENAI_BASE_URL`. |
| Backend E2E acceptance run | Passed | FastAPI + SearchMCP + Qdrant + HITL + Langfuse завершили run `115efb2ff808` зі статусом `completed`, trace id `bd023448dfe118eef534ff0e82bdd2b3`. |
| Current diagram contract smoke | Passed | `graph.py` now emits 5 research-result diagrams: market entry, payback, validation timeline, saturation map and critic score pie chart. |

## Що Потребує Runtime Оточення

- Qdrant має бути запущений локально перед ingestion.
- `uv run python ingest.py` створює collection `course_project_market_analyst_knowledge`.
- OpenAI API key потрібен для стабільного фінального demo.
- Langfuse keys потрібні для trace evidence, але core workflow має працювати і без них.
- Optional `SearchMCP` потрібен тільки для MCP smoke evidence; у режимі `mcp_auto` direct tools залишаються fallback.

## Очікуваний E2E Result

E2E run повинен показати події:

```text
Backend -> Research Analyst -> Critic Role Selector -> Human Criteria Gate
-> Expert Critic Panel -> Critic Aggregator -> Report Compiler
```

Фінальний результат:

- saved Markdown report у `output/`;
- `FinalReport.diagrams` з Mermaid blocks for research outcomes, not orchestrator internals;
- SSE history у SPA;
- Langfuse trace id у backend response або CLI output.

## Artifact Note

`generated_acceptance_report.md` є historical generated output з повного E2E acceptance run. Після цього diagram contract було уточнено: нові runtime reports повинні показувати market-entry/payback/timeline/saturation diagrams, а source-level architecture лишається в `uml_diagrams/`.
