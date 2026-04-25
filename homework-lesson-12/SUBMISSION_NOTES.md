# Пояснювальні Нотатки: Домашнє Завдання 12

## Підсумок

У ДЗ 12 до існуючої multi-agent RAG системи з уроку 10 було додано Langfuse observability. Основний pipeline залишився тим самим: `Supervisor -> Planner -> Researcher -> Critic -> save_report`. Новий шар відповідає за trace tree, session/user tracking, Prompt Management та online LLM-as-a-Judge evaluation.

Секрети не комітяться. Langfuse keys залишаються тільки у root `.env`.

## Карта Доказів

| Намір | Що Зроблено | Висновок Для Перевірки |
|---|---|---|
| Показати спадковість від попередньої MAS | Перенесено ядро HW10: `agents/`, `tools.py`, `retriever.py`, `ingest.py`, `schemas.py`, `supervisor.py`, `main.py` | Це не окрема demo system, а продовження попередньої RAG + evaluator-optimizer архітектури. |
| Додати tracing кожного запуску | `main.py` відкриває `langfuse_observed_run(...)`; `observability.py` додає `CallbackHandler` у runtime config | Supervisor, tool calls і вкладені sub-agent calls потрапляють в одне Langfuse trace tree. |
| Додати session/user tracking | `propagate_attributes(...)` прокидує `session_id`, `user_id`, `tags`, metadata | У Langfuse UI видно session `homework-12-review-session` і user `vetal`. |
| Винести system prompts з Python | `prompt_registry.py` завантажує prompts через `get_prompt(...).compile(...)`; `langfuse_prompts.json` використовується як bootstrap seed | Runtime prompts приходять з Langfuse Prompt Management з label `production`, а не з hardcoded Python constants. |
| Зробити Prompt Management відтворюваним | `bootstrap_langfuse.py` читає `langfuse_prompts.json` і створює/оновлює prompts у Langfuse | У репозиторії видно, які саме prompts були завантажені в Langfuse UI. |
| Додати online LLM-as-a-Judge | У Langfuse UI створено два evaluators: `hw12_relevance_score` і `hw12_groundedness_pass` | Нові traces автоматично отримують numeric та boolean scores. |
| Підготувати screenshot evidence | У `screenshots/` додано чотири UI screenshots, а `screenshots/README.md` пояснює їх призначення | Перевіряючий бачить trace tree, session grouping, evaluator scores і prompt management без ручного запуску. |
| Не змішувати runtime output з git | `homework-lesson-*/output/` ігнорується через root `.gitignore` | Generated reports залишаються локальними runtime artifacts і не засмічують submission. |

## Маршрут Для Перевіряючого

Для швидкої перевірки підготовлено такі точки входу:

| Файл Або Папка | Що Показує |
|---|---|
| `ASSIGNMENT.md` | Оригінальне формулювання ДЗ. |
| `README.md` | Фактичний спосіб запуску і локальний runtime stack. |
| `langfuse_prompts.json` | Усі agent system prompts, які bootstrap відправляє в Langfuse. |
| `prompt_registry.py` | Runtime завантаження prompts з Langfuse, а не з локальних constants. |
| `observability.py` | Langfuse `CallbackHandler`, trace metadata і `propagate_attributes`. |
| `uml_diagrams/HW12_LANGFUSE_MERMAID.md` | Архітектура trace/session/evaluator flow у вигляді Mermaid diagrams. |
| `screenshots/` | UI evidence після реальних прогонів у Langfuse. |

## UI Evidence У Langfuse

| Screenshot | Що Доводить |
|---|---|
| `01_trace_tree.png` | Один MAS request розгортається у Supervisor, Planner, Researcher, Critic, tool calls і `save_report` spans. |
| `02_session_grouping.png` | Кілька traces згруповані під `homework-12-review-session` і мають user `vetal`. |
| `03_evaluator_scores.png` | Нові traces отримали автоматичні LLM-as-a-Judge scores. |
| `04_prompt_management.png` | Усі `hw12_*_system` prompts існують з label `production`. |

## Evidence Реальних Прогонів

Trace ids реальних запусків записані в `reviewer_artifacts/hw12_real_run_trace_summary.md`.

| Trace ID | Що Було Перевірено |
|---|---|
| `3cd857bb52795e497b04441cc7d5df37` | Smoke E2E: Langfuse trace, HITL save і збереження report. |
| `511ba698fe49808b44662f20495bed96` | Fresh evaluator-era запуск після активації evaluators: порівняння RAG архітектур. |
| `86103007c4203c31c116d8bf0fcf6534` | Fresh evaluator-era запуск після активації evaluators: вибір між local RAG і web search. |

## Контрольні Запити

Для перевірки поведінки системи використовувався набір запитів, який покриває RAG comparison, Langfuse debugging, source selection і evaluation feedback loop:

```text
Compare naive RAG, sentence-window retrieval, and parent-child retrieval. Write a report.
```

```text
Explain how Langfuse tracing helps debug a multi-agent RAG workflow.
```

```text
When should a research agent use local RAG instead of web search?
```

```text
Compare prompt caching and semantic caching for multi-agent systems.
```

```text
How can evaluator scores and user feedback create a data flywheel for this MAS?
```

## Перевірки

Нижче залишені команди, які використовувалися для локальної перевірки і дозволяють відтворити результат.

Static:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams
uv run python -m compileall homework-lesson-12
```

Prompt bootstrap:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-12
uv run python bootstrap_langfuse.py
```

RAG:

```powershell
uv run python ingest.py
uv run python -c "from tools import knowledge_search; print(knowledge_search.invoke({'query': 'retrieval augmented generation'})[:1000])"
```

End-to-end:

```powershell
uv run python main.py
```

Під час E2E перевірки HITL `save_report` request був підтверджений через `approve`, після чого результат відобразився у Langfuse Tracing, Sessions, Prompts та Evaluator Scores.

## Нотатки

- Canonical save path залишився HITL-gated: `Supervisor -> save_report -> approve/edit/reject`.
- Emergency local-model fallback з попередньої домашньої роботи залишений тільки як прагматична страховка для нестабільної локальної моделі. Це не normal workflow.
- Evaluators налаштовані в Langfuse UI, бо ДЗ прямо просить Langfuse LLM-as-a-Judge setup і screenshots.
