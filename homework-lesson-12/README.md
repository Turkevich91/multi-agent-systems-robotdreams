# Домашнє завдання 12: Langfuse Observability

У цій роботі мультиагентну RAG систему з уроку 10 розширено Langfuse tracing, session/user tracking, Prompt Management та online оцінюванням через LLM-as-a-Judge.

Runtime stack навмисно залишений близьким до попередніх ДЗ:

- chat model: LM Studio через `OPENAI_BASE_URL`
- embeddings: OpenAI-compatible embeddings endpoint з root `.env`
- vector store: локальна Qdrant collection `homework_lesson_12_knowledge`
- workflow: `Supervisor -> Planner -> Researcher -> Critic -> save_report`
- observability: Langfuse Cloud project через `LANGFUSE_*` env vars

Оригінальне формулювання завдання збережене в `ASSIGNMENT.md`.

## Покриття Вимог

| Вимога | Реалізація |
|---|---|
| Trace кожного MAS запуску | `observability.py` обгортає кожен user request у Langfuse trace і передає `CallbackHandler` у LangChain/LangGraph runtime config. |
| Повне дерево agent/tool викликів | Supervisor tool calls та вкладені sub-agent invocations отримують той самий Langfuse callback config. |
| Session/user tracking | `LANGFUSE_SESSION_ID`, `LANGFUSE_USER_ID` та tags прокидаються через `propagate_attributes`. |
| Prompt Management | Agent system prompts завантажуються з Langfuse через `prompt_registry.py`; у Python файлах немає hardcoded system prompts. |
| LLM-as-a-Judge | Налаштування evaluators задокументоване в `reviewer_artifacts/hw12_langfuse_evaluator_setup.md`. |
| Screenshots | `screenshots/README.md` описує чотири обов'язкові evidence screenshots. |

## Налаштування

З root репозиторію:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams
uv sync
```

Root `.env` має містити:

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
MODEL_NAME=google/gemma-4-26b-a4b

OPENAI_EMBEDDING_API_KEY=...
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

LANGFUSE_PUBLIC_KEY=<your-langfuse-public-key>
LANGFUSE_SECRET_KEY=<your-langfuse-secret-key>
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
```

## Bootstrap Prompts У Langfuse

Тексти system prompts лежать у `langfuse_prompts.json` як seed artifact. Команда нижче завантажує їх у Langfuse Prompt Management:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-12
uv run python bootstrap_langfuse.py
```

Після bootstrap у Langfuse UI з'являються prompts з label `production`:

- `hw12_supervisor_system`
- `hw12_planner_system`
- `hw12_planner_fallback_system`
- `hw12_researcher_system`
- `hw12_critic_system`
- `hw12_critic_fallback_system`

## Побудова RAG Index

Qdrant має бути запущений локально, як у попередніх домашніх роботах.

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-12
uv run python ingest.py
```

Опційна перевірка collection:

```powershell
uv run python -c "from qdrant_client import QdrantClient; from config import settings; c=QdrantClient(url=settings.qdrant_url); print(c.count(collection_name=settings.qdrant_collection, exact=True).count)"
```

## Запуск MAS З Langfuse Tracing

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-12
uv run python main.py
```

Приклади запитів, використаних для прогонів:

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

Після завершення кожного запуску `main.py` друкує Langfuse `trace_id`. У Langfuse UI зручно фільтрувати за tag `homework-12` або session `homework-12-review-session`.

## Evaluators

У Langfuse створено два LLM-as-a-Judge evaluators за конфігурацією з:

```text
reviewer_artifacts/hw12_langfuse_evaluator_setup.md
```

Пара evaluators:

- numeric `hw12_relevance_score`
- boolean `hw12_groundedness_pass`

Після створення evaluators були виконані нові запуски, щоб Langfuse асинхронно проставив scores.

## Докази

Фінальна здача містить:

- `screenshots/01_trace_tree.png`
- `screenshots/02_session_grouping.png`
- `screenshots/03_evaluator_scores.png`
- `screenshots/04_prompt_management.png`
- `SUBMISSION_NOTES.md`
- `uml_diagrams/HW12_LANGFUSE_MERMAID.md`
