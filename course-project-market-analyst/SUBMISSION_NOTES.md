# Пояснювальні Нотатки: Course Project

## Підсумок

Фінальний проєкт реалізовано як Market Analyst для agentic AI developer tooling. Система аналізує публічний ринок coding agents, IDE copilots, observability/evaluation platforms і MCP-style integrations для анонімної AEC/manufacturing software team.

Проєкт не використовує приватні GitHub repositories, приватні email або company secrets у RAG corpus, outputs чи документації.

## Карта Доказів

| Намір | Що Зроблено | Висновок Для Перевірки |
|---|---|---|
| Показати course-project варіант Market Analyst | Реалізовано workflow `Research Analyst -> Critic Panel -> Compiler` | Проєкт відповідає `course-project/project_market_analyst.md`, але адаптований під реальний tech-stack студента. |
| Залишити архітектуру надійною | Core побудовано на `LangGraph StateGraph`, без обов'язкових зовнішніх agent servers | Demo не залежить від ACP або декількох protocol services. |
| Додати MCP без ризику для дедлайну | Реалізовано optional read-only `SearchMCP` з режимом `mcp_auto` | MCP є реальною технологічною частиною, але не блокує фінальний run. |
| Додати експертну критику | `CriticRoleSelector` стартує з двох стандартних ролей: Financial і Risk; `ExpertCritic` запускається по кожній підтвердженій ролі | Критика не універсальна, а керована: базові finance/risk ролі можна доповнити custom або AI-suggested critic під конкретний ринок. |
| Додати Human-in-the-loop | Перед критикою graph зупиняється через `interrupt`, а UI/CLI дозволяє змінити criteria або додати ad-hoc critic role | Людина може додати власного критика, наприклад актуальності чи compliance, навіть якщо такої ролі немає у базовому registry. |
| Зробити Mermaid частиною продукту | Compiler повертає `MermaidDiagram` objects і fenced Mermaid blocks у Markdown: market entry, payback, timeline, saturation і pie chart для critic scores | Діаграми показують висновки research, а архітектура оркестратора лишається в документації та source code. |
| Додати SPA interface | React/Vite dashboard показує prompt, run history, SSE events, HITL criteria form, report і Mermaid rendering | Перевіряючий бачить agent workflow як інтерактивний продукт. |
| Залишити fallback для перевірки | `main.py` дає CLI demo без frontend | Якщо UI або browser не запускаються, core workflow все одно перевіряється. |
| Додати observability | `observability.py` інтегрує Langfuse callback metadata, trace/session/user/tags | Runs готові до Langfuse trace tree і evaluator evidence. |

## Основні Компоненти

| Компонент | Призначення |
|---|---|
| `graph.py` | StateGraph, HITL interrupt, expert critic panel, revision loop, compiler. |
| `schemas.py` | Pydantic contracts: DraftReport, CriticRole, ExpertCritique, FinalReport, MermaidDiagram. |
| `critic_registry.py` | Базовий набір expert critic roles; HITL може додати ad-hoc role перед critique step. |
| `api.py` | FastAPI backend з SSE streaming, HITL endpoint і session-level persistence для approved critic roles. |
| `mcp_adapter.py` | `direct`, `mcp_auto`, `mcp_required` tool backend modes. |
| `mcp_servers/search_mcp.py` | Optional FastMCP server для read-only tools/resources. |
| `frontend/` | Decision Dashboard на React/Vite/TypeScript. |
| `data/public_agentic_dev_tools_notes.md` | Public-only seed notes для RAG. |
| `reviewer_artifacts/generated_acceptance_report.md` | Реальний generated report з E2E acceptance run, скопійований без ручного редагування. |
| `reviewer_artifacts/e2e_acceptance_trace_summary.md` | Trace summary реального E2E run з run id, Langfuse trace id і event timeline. |

## Runtime Flow

1. Користувач запускає analysis через SPA або CLI.
2. Analyst збирає public evidence через web/RAG tools.
3. Role Selector обирає default expert critics: Financial і Risk.
4. HITL gate показує ролі й criteria.
5. Людина підтверджує, редагує, додає custom critic або просить AI suggested critic.
6. Backend зберігає approved critic roles на час run/session, щоб після report було видно, які критики вплинули на результат.
7. Expert Critic Panel виконує role-specific reviews.
8. Aggregator формує verdict.
9. Якщо потрібна доробка, Analyst робить revision.
10. Compiler генерує Markdown report і Mermaid diagrams з research outcome: market entry, payback, timeline, saturation, critic score share.
11. Report зберігається в `output/`.

## Реальний Acceptance Run

Acceptance query було прогнано через FastAPI backend з активним optional `SearchMCP`, Qdrant RAG, Langfuse tracing і HITL criteria submit.

- Status: `completed`
- Run ID: `115efb2ff808`
- Langfuse trace id: `bd023448dfe118eef534ff0e82bdd2b3`
- Revision loop: draft + 3 revisions
- Final diagrams: `3` in the original acceptance artifact.
- Current compiler version generates research-result diagrams: market entry flow, payback gate, validation timeline, saturation map and critic score pie chart.
- Generated report artifact: `reviewer_artifacts/generated_acceptance_report.md`
- Trace artifact: `reviewer_artifacts/e2e_acceptance_trace_summary.md`

Примітка: `generated_acceptance_report.md` залишено як historical generated output з повного E2E run. Після останньої refinement-правки актуальний diagram contract показано у `graph.py` і `reviewer_artifacts/sample_market_analysis_report.md`.

## Semantic POV Review

| POV | Що Перевірено | Висновок |
|---|---|---|
| Reviewer / Evaluator | Чи можна зрозуміти архітектуру, runtime flow і evidence без запуску | README, SUBMISSION_NOTES, UML і reviewer artifacts пояснюють code path, demo path і historical acceptance artifact. |
| Product Decision Maker | Чи показують diagrams результат research, а не внутрішню кухню agents | Runtime report diagrams тепер описують market entry, payback, validation timeline, saturation і critic score share. |
| Demo Operator | Чи збігається live demo story з UI behavior | Presentation notes описують HITL, AI-suggested/custom critics, session-level critic persistence і final report view. |
| Backend Maintainer | Чи відповідають docs актуальній state/SSE логіці | UML sequence показує `RunRecord`, persisted `approved_roles`, SSE events і `GET /api/runs/{run_id}` snapshot. |
| Privacy / Safety Reviewer | Чи не змішується приватний контекст з outputs | Docs фіксують public-only research, no private repo/email/company secrets, no model keys in frontend, ignored `output/` і local indexes. |

## Перевірки

Static Python:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams
uv run python -m compileall -q -x "frontend[\\/](node_modules|dist)" course-project-market-analyst
```

Frontend:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\course-project-market-analyst\frontend
npm install
npm run build
```

RAG:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\course-project-market-analyst
uv run python ingest.py
```

MCP:

```powershell
uv run python mcp_servers/search_mcp.py
```

Backend:

```powershell
uv run python api.py
```

SPA:

```powershell
cd frontend
npm run dev
```

## Нотатки Для Перевіряючого

- MCP навмисно optional, бо фінальний проєкт має бути стабільним у стислі строки.
- ACP не додано у фінальний проєкт, бо він уже був реалізований у HW9, а тут підвищував би ризик без потреби.
- Write path не винесено в MCP: compiler локально зберігає report, а MCP лишається read-only research boundary.
- SPA є демонстраційним інтерфейсом, але CLI лишається fallback для технічної перевірки.
- Усі private context signals використані тільки як мотивація; у проєкті вони анонімізовані.
