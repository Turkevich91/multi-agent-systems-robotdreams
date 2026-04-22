# Домашнє завдання 8: мультиагентна дослідницька система

## Короткий підсумок

Розширено Research Agent з `homework-lesson-5` до мультиагентної системи **Supervisor + 3 суб-агенти** за патерном **Plan → Research → Critique → Report** (evaluator-optimizer з Лекції 7).

- **Planner Agent** робить розвідку домену і повертає структурований `ResearchPlan`.
- **Research Agent** виконує план, використовуючи RAG (Qdrant + BM25 + cross-encoder) та веб-інструменти з hw5.
- **Critic Agent** незалежно верифікує знахідки і повертає структурований `CritiqueResult` з вердиктом `APPROVE` або `REVISE`.
- **Supervisor Agent** оркеструє цикл, робить до 2 раундів доопрацювання і складає фінальний Markdown-звіт.
- **HITL** (`HumanInTheLoopMiddleware`) перехоплює виклик `save_report` і чекає на `approve` / `edit` / `reject` від користувача у REPL.

RAG-пайплайн (Qdrant, BM25, reranking, embeddings через OpenAI, chat через LM Studio) перевикористовується без змін з hw5. Нове в hw8 — мультиагентна координація, структуровані Pydantic-виводи через `ToolStrategy`, ітеративний revision-loop і HITL на запис.

## Намір - Дія - Висновок

| Намір | Дія | Висновок |
|---|---|---|
| Зрозуміти, що саме змінюється порівняно з hw5 | Переглянуто `README.md` hw8 і матеріали Лекції 7 (evaluator-optimizer, agent-as-tool, HITL) | Потрібні Supervisor + 3 суб-агенти з структурованими виводами, ітеративний Plan→Research→Critique→Report і HITL на `save_report` |
| Перевикористати RAG з hw5 | Скопійовано `retriever.py`, `ingest.py`, `tools.py` (`web_search`, `read_url`, `knowledge_search`) | Qdrant collection `homework_lesson_8_knowledge` з 464 points, hybrid (Qdrant + BM25) + cross-encoder reranking працюють як у hw5 |
| Винести структуровані схеми у власний модуль | У `schemas.py` створено Pydantic-моделі `ResearchPlan` і `CritiqueResult` | Supervisor, Planner та Critic працюють з однаковими моделями, вивід валідований Pydantic |
| Реалізувати Planner Agent | У `agents/planner.py` створено `planner_agent = create_agent(..., response_format=ToolStrategy(ResearchPlan))` з tools `web_search`, `knowledge_search` | Planner робить коротку розвідку і повертає структурований план з 3-6 пошуковими запитами |
| Захиститися від невдалого structured-output | Додано `planner_fallback_agent` + ручний JSON-парсер `_json_from_text` у `agents/planner.py` | Якщо локальна модель ігнорує `ToolStrategy`, вивід усе одно нормалізується до валідного `ResearchPlan` |
| Реалізувати Research Agent як субагент | У `agents/research.py` створено `research_agent` з тими ж tools, що і в hw5 (`web_search`, `read_url`, `knowledge_search`), обгорнуто в `@tool research(request)` | Supervisor викликає Researcher як звичайний tool, а Researcher всередині сам вирішує, коли йти у web, а коли в knowledge base |
| Реалізувати Critic Agent | У `agents/critic.py` створено `critic_agent` з `response_format=ToolStrategy(CritiqueResult)` і тими ж tools, що і Researcher | Critic незалежно верифікує freshness / completeness / structure і повертає `APPROVE` або `REVISE` з конкретним `revision_requests` |
| Обмежити нескінченні доопрацювання | У `critique(...)` додано підрахунок попередніх викликів із `ToolRuntime.state.messages`; після `max_revision_rounds=2` автоматично повертається `APPROVE` | Supervisor не ходить по колу, навіть якщо Critic щоразу знаходить нові gaps |
| Реалізувати Supervisor | У `supervisor.py` створено `supervisor = create_agent(model, tools=[plan, research, critique, save_report], middleware=[HumanInTheLoopMiddleware, ToolCallLimit, ModelCallLimit], checkpointer=InMemorySaver())` | Supervisor має фіксований workflow у system prompt: plan → research → critique → (REVISE loop) → save_report |
| Додати HITL на запис | Увімкнено `HumanInTheLoopMiddleware(interrupt_on={"save_report": True})` | Виклик `save_report` ставиться на паузу; стрім віддає `__interrupt__` з `action_requests` |
| Реалізувати REPL з resume-логікою | У `main.py` обробляється `__interrupt__`, показується filename + preview, збирається decision від користувача і надсилається `Command(resume={"decisions": [...]})` | Користувач може ввести `approve`, `edit` (з фідбеком) або `reject` — Supervisor відповідно зберігає, переробляє або скасовує |
| Зрозуміти, як LangChain інтерпретує `edit` | На практиці `edit` = `type=reject` з повідомленням-фідбеком, яке модель має прочитати і відповісти revised-викликом `save_report` | В `main.py` обидві гілки `edit` і `reject` відправляють `type=reject`, але з різними `message`; supervisor-prompt описує, як обробляти кожен випадок |
| Винести промпти і налаштування | `PLANNER_PROMPT`, `RESEARCH_PROMPT`, `CRITIC_PROMPT`, `SUPERVISOR_PROMPT` + `Settings` у `config.py`, `.env` читається з кореня курсу | Усі промпти і параметри редагуються в одному місці, API-ключі та model name беруться з `.env` |
| Запустити end-to-end smoke-тест | Запит `"Briefly compare naive RAG and sentence-window retrieval. Write a short Markdown report..."` з `MODEL_NAME=google/gemma-4-26b-a4b` | Supervisor викликав `plan → research → critique (APPROVE) → save_report`; HITL перехопив; після `edit`-фідбеку Supervisor додав TL;DR і повторно викликав `save_report`; після `approve` файл збережено як `output/rag_compare_smoke.md` (3260 байт) |
| Діагностувати проблеми на великих локальних моделях | На `google/gemma-4-31b` один раз впало в `openai.APITimeoutError` (120 с) і один раз модель видала degenerate `<unused49>` токени | Рекомендовано `google/gemma-4-26b-a4b` (MoE) і `REQUEST_TIMEOUT=600`; додано секцію Troubleshooting нижче |
| Гарантувати збереження звіту навіть при «забудькуватій» локальній моделі | У `main.py` додано `_ensure_report_saved(...)`: після кожного турну перевіряється, чи Supervisor реально отримав `Report saved to...`; якщо ні — надсилається явне нагадування і повторний HITL-прогін; якщо й це не допомогло — пряме збереження останнього AI-тексту через `save_report.invoke(...)` з обходом HITL і попередженням | Звіт точно потрапляє у `output/` навіть якщо модель «забула» викликати інструмент; supervisor-prompt додатково посилено пунктами 8-9 про обовʼязковість `save_report` |
| Навести архітектурні діаграми | Створено `uml_diagrams/MULTI_AGENT_MERMAID.md` з 6 Mermaid-діаграмами: загальна архітектура, evaluator-optimizer state diagram, sequence для одного запиту, class diagram agent-as-tool, HITL flow, gitignore map | Перевіряючий бачить архітектуру без потреби читати весь код |
| Привести `.gitignore` у відповідність до hw8 | У корені курсу вже діють правила `homework-lesson-*/index/`, `homework-lesson-*/output/`, `resources`, `.env`, `__pycache__/`, `.venv/` | У Git потрапляє тільки код + документація + `data/*.pdf` + `requirements.txt`; згенеровані артефакти та лекційні ресурси лишаються локально |

## UML / Mermaid Diagrams

Усі архітектурні діаграми — у `uml_diagrams/MULTI_AGENT_MERMAID.md`:

1. Загальна архітектура (Supervisor + 3 subagents + RAG tools + HITL)
2. Evaluator–optimizer state machine (research ↔ critic)
3. Sequence diagram одного запиту end-to-end
4. Class diagram agent-as-tool композиції (+ `ResearchPlan` / `CritiqueResult`)
5. HITL decision flow (approve / edit / reject)
6. Що потрапляє / не потрапляє в Git

## Clean Windows Bootstrap

Після чистої Windows спочатку Docker Desktop, потім Qdrant:

```powershell
docker --version
docker ps

docker run -d --name qdrant `
  -p 6333:6333 `
  -p 6334:6334 `
  -v qdrant_storage:/qdrant/storage `
  qdrant/qdrant:latest

# або, якщо контейнер існує:
docker start qdrant

Invoke-WebRequest -UseBasicParsing http://localhost:6333/healthz
```

## Environment

Приклад `.env` у корені курсу:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
MODEL_NAME=google/gemma-4-26b-a4b
TEMPERATURE=0.2
REQUEST_TIMEOUT=600
MAX_RETRIES=1
```

Якщо chat endpoint локальний, код автоматично ставить embeddings на `https://api.openai.com/v1`, якщо не задано `OPENAI_EMBEDDING_BASE_URL`.

## Команди для відтворення

### 1. Ingestion

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-8
uv run python ingest.py
```

### 2. Перевірка Qdrant

```powershell
uv run python -c "from qdrant_client import QdrantClient; from config import settings; c=QdrantClient(url=settings.qdrant_url); print(c.count(collection_name=settings.qdrant_collection, exact=True).count)"
```

Очікується `464`.

### 3. Smoke-test RAG

```powershell
uv run python -c "from tools import knowledge_search; print(knowledge_search.invoke({'query': 'retrieval augmented generation'})[:1000])"
```

### 4. REPL Supervisor

```powershell
uv run python main.py
```

Приклад запиту:

```text
Compare naive RAG, sentence-window retrieval, and parent-child retrieval. Write a report.
```

## Verified End-to-End Run

Smoke-тест (2026-04-22, `MODEL_NAME=google/gemma-4-26b-a4b`):

Запит:

```text
Briefly compare naive RAG and sentence-window retrieval. Write a short
Markdown report (save it as rag_compare_smoke.md). Keep it under 500 words.
```

Trace (`supervisor.stream(..., stream_mode=["updates"])`):

1. `plan(request)` → `ResearchPlan` JSON з 4 пошуковими запитами.
2. `research(plan)` → findings із секціями architectural differences, pros/cons.
3. `critique(findings)` → `verdict=APPROVE`, усі три прапорці `true`.
4. `save_report(...)` → HITL interrupt #1, `filename='rag_compare_smoke.md'`, 3058 байт.
5. Resume з `edit` + фідбек `"Add a one-line TL;DR at the top."`.
6. Supervisor переробив звіт (3260 байт) і викликав `save_report` знову.
7. HITL interrupt #2 → resume з `approve`.
8. Звіт записано у `output/rag_compare_smoke.md`.

Це підтверджує:

- Plan → Research → Critique → Report loop ✅
- Структуровані виводи (`ResearchPlan`, `CritiqueResult`) ✅
- HITL interrupt на `save_report` ✅
- `edit`-гілка: Supervisor читає фідбек і повторно викликає `save_report` з новим чернеткою ✅
- `approve`-гілка: звіт записаний у `output/` ✅
- `reject`-гілка: ідентична до `edit`, але з повідомленням про скасування; обробляється в `main.py`.

## Troubleshooting

- **`openai.APITimeoutError: Request timed out`** — локальна модель не встигає відповісти за 120 с. Підняти `REQUEST_TIMEOUT=600` у `.env` та/або перейти на легшу модель (`google/gemma-4-26b-a4b` MoE).
- **Модель видає `<unused49><unused49>...` токени** — degenerate-вивід Gemma при зламаному chat-template або перевантаженні контексту. Перезапустити LM Studio та/або перейти на іншу модель.
- **Critic щоразу повертає `REVISE` з однаковими gaps** — перевірити Qdrant (`/healthz`, `count=464`) і перезапустити `ingest.py`. `critic_fallback_agent` рятує від зламаного JSON, але не від порожньої бази знань.
- **HITL `edit`** реалізовано як `Command(resume={"decisions": [{"type": "reject", "message": feedback}]})` у `main.py`. Supervisor-prompt містить інструкцію: побачивши reject з фідбеком — переробити звіт і викликати `save_report` знову.
- **Модель «забула» викликати `save_report`** — це очікуваний режим відмови для слабких локальних моделей. `main.py:_ensure_report_saved(...)` спершу надсилає Supervisor явне нагадування і проганяє ще один HITL-раунд; якщо і це не спрацювало — напряму викликає `save_report.invoke(...)` з останнім зафіксованим AI-текстом (з обходом HITL і явним попередженням у консолі). Це гарантує, що файл опиниться в `output/` для кожного запиту.

## Що комітиться в Git і що треба відтворити локально

Ліва частина — все, що прилітає з клоном репо і достатньо для ревʼю. Права — локальні артефакти, які перевіряючому треба згенерувати самостійно, і як саме їх відтворити. Реальні правила визначаються кореневим `.gitignore` (перевірено через `git ls-files` і `git check-ignore`).

### Комітиться (піде на перевірку)

| Файл / директорія | Роль |
|---|---|
| `agents/__init__.py`, `agents/planner.py`, `agents/research.py`, `agents/critic.py` | Три суб-агенти |
| `supervisor.py` | Supervisor + agent-as-tool обгортки + middleware |
| `schemas.py` | `ResearchPlan`, `CritiqueResult` Pydantic-моделі |
| `tools.py` | `web_search`, `read_url`, `knowledge_search`, `save_report` |
| `retriever.py`, `ingest.py` | RAG pipeline (hybrid + reranking), перевикористані з hw5 |
| `config.py` | `Settings`, `build_chat_model`, усі промпти |
| `main.py` | REPL з HITL interrupt/resume |
| `requirements.txt` | Залежності |
| `data/langchain.pdf`, `data/large-language-model.pdf`, `data/retrieval-augmented-generation.pdf` | Вхідні PDF для RAG |
| `README.md` | Опис домашнього завдання |
| `SUBMISSION_NOTES.md` | **Цей файл**: підсумок + таблиця Намір-Дія-Висновок + reproducible commands |
| `uml_diagrams/MULTI_AGENT_MERMAID.md` | Mermaid-діаграми архітектури |

### НЕ комітиться

| Артефакт | Чому | Правило у `.gitignore` |
|---|---|---|
| `.env`, `.env.*` | API ключі, `MODEL_NAME`, `REQUEST_TIMEOUT` | `.env`, `.env.*` |
| `homework-lesson-8/index/` (`chunks.json`, `manifest.json`) | Generated BM25 chunks, відтворюється через `ingest.py` | `homework-lesson-*/index/` |
| `homework-lesson-8/output/*.md` | Згенеровані звіти з REPL | `homework-lesson-*/output/` |
| `homework-lesson-8/resources/` (лекційний notebook, посилання) | Навчальні матеріали, не частина здачі | `resources` |
| `homework-lesson-8/__pycache__/` | Python bytecode cache | `__pycache__/` |
| `.venv/` | Віртуальне оточення | `.venv/` |
| Docker volume `qdrant_storage` | Векторна база Qdrant, живе поза репо | (поза Git) |
| HuggingFace / transformers cache | Cross-encoder `BAAI/bge-reranker-base`, тягнеться при першому запуску | (поза репо) |
| `.idea/`, `.vscode/` | IDE-файли | `.idea/`, `.vscode/` |

### Як відтворити локальні артефакти після клону

```powershell
# 1. Qdrant (Docker)
docker start qdrant   # або docker run ... (див. вище)

# 2. .env у корені курсу з ключами OpenAI + LM Studio

# 3. Ingestion → створює index/ та наповнює Qdrant
uv run python ingest.py

# 4. REPL
uv run python main.py
```

## Acceptance Checklist

- `schemas.py` визначає `ResearchPlan` і `CritiqueResult`.
- Planner і Critic використовують `response_format=ToolStrategy(...)`.
- Supervisor завжди йде `plan → research → critique` перед `save_report`.
- Critic може вимагати до `max_revision_rounds=2` раундів доопрацювання.
- `save_report` захищений `HumanInTheLoopMiddleware(interrupt_on={"save_report": True})`.
- `approve` зберігає звіт, `edit` надсилає фідбек для нової спроби збереження, `reject` повністю скасовує збереження.
- `main.py:_ensure_report_saved(...)` гарантує, що `save_report` виконається навіть якщо слабка локальна модель «забула» його викликати (нагадування + прямий fallback-запис).
- Mermaid-діаграми є в `uml_diagrams/MULTI_AGENT_MERMAID.md`.
- У Git потрапляє тільки код, документація, `data/*.pdf` і `requirements.txt`; `index/`, `output/`, `resources/`, `.env`, `.venv/`, `__pycache__/` — ігноруються і відтворюються локально.



