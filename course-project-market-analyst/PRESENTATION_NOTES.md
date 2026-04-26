# Presentation Notes

## Короткий Сценарій Демонстрації

Цей фінальний проєкт показує агентну систему, яка допомагає прийняти рішення щодо впровадження agentic AI developer tooling у невеликій AEC/manufacturing software team. Я не використовую приватні репозиторії, пошту або company secrets у корпусі знань чи outputs. Приватний контекст вплинув лише на вибір теми: система аналізує публічний ринок інструментів, які могли б бути корисними для реальної development команди.

Основний workflow побудовано на `LangGraph StateGraph`: `Research Analyst` збирає evidence, `Critic Role Selector` стартує з Financial і Risk critic roles, `Human Criteria Gate` дозволяє людині змінити критерії або додати ad-hoc чи AI-suggested critic role, `Expert Critic Panel` перевіряє draft з різних перспектив, `Critic Aggregator` вирішує approve/revise, а `Report Compiler` створює фінальний Markdown report з Mermaid decision diagrams.

## Live Demo Flow

1. Запустити Qdrant і ingestion, якщо collection ще не створена.
2. Запустити backend: `uv run python api.py`.
3. Запустити frontend: `npm run dev` у папці `frontend`.
4. Відкрити `http://127.0.0.1:5173`.
5. Запустити acceptance query про ринок agentic AI developer tools.
6. Показати SSE event stream: Analyst, CriticRoleSelector, Human Criteria Gate.
7. На HITL кроці змінити критерії, додати власного критика або згенерувати AI-suggested critic для конкретного research prompt.
8. Дочекатися Expert Critic Panel, Aggregator і Compiler.
9. Показати, що після готового report панель критиків зберігає саме ті ролі, через які проходила критика.
10. Показати фінальний report, Mermaid diagrams і saved output path.
11. Відкрити Langfuse trace, щоб показати trace tree, model/tool calls, metadata і session tags.

## Що Важливо Пояснити

- MCP доданий як optional read-only boundary. Це справжній `SearchMCP`, але у режимі `mcp_auto` система не падає, якщо MCP server не запущений.
- ACP навмисно не додано у фінальний проєкт, бо він уже був реалізований у HW9, а тут збільшив би runtime ризик без суттєвої користі для теми.
- SPA не містить model keys. Frontend працює тільки через FastAPI.
- Human-in-the-loop стоїть не в кінці, а перед критикою, щоб людина могла керувати тим, з яких професійних перспектив система буде оцінювати рішення. Approved critic roles зберігаються на час run/session, щоб було видно, які критики сформували final report.
- Mermaid не просто документація. Діаграми в output показують результати research: market entry flow, payback gate, validation timeline, saturation map і розподіл оцінок expert critics; архітектура оркестратора описана окремо в source/docs.

## Acceptance Prompt

```text
Analyze the market for agentic AI developer tools for a small AEC/manufacturing software team. Compare coding agents, IDE copilots, observability/evaluation platforms, and MCP-based integrations. Recommend an adoption roadmap.
```

## Fallback Demo

Якщо браузер або frontend не запускається, можна показати той самий core workflow через CLI:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\course-project-market-analyst
uv run python main.py
```
