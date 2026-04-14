# Homework Lesson 4: Research Agent з власним ReAct Loop

Ця версія переробляє `homework-lesson-3`: LangChain agent abstraction прибрано, а ReAct loop реалізовано вручну через OpenAI-compatible Chat Completions API.

## Швидкий запуск

1. Запустіть LM Studio server на `http://127.0.0.1:1234/v1` і виберіть модель `google/gemma-4-26b-a4b`.
2. Встановіть залежності з кореня репозиторію:
   ```powershell
   uv sync
   ```
3. Запустіть інтерактивний агент:
   ```powershell
   uv run python .\homework-lesson-4\main.py
   ```

Для запуску через `pip`:
```powershell
cd .\homework-lesson-4
python -m pip install -r requirements.txt
python main.py
```

## Конфігурація

За замовчуванням використовується локальний OpenAI-compatible endpoint LM Studio, тому реальний OpenAI API key не потрібен.

Якщо потрібно змінити endpoint або модель, скопіюйте `.env.example` у `.env` і відредагуйте:

```env
OPENAI_API_KEY=lm-studio
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
MODEL_NAME=google/gemma-4-26b-a4b
TEMPERATURE=0.2
REQUEST_TIMEOUT=120
MAX_RETRIES=1
```

## Архітектура

- `config.py`: Pydantic Settings, system prompt, ліміти ітерацій та context engineering.
- `tools.py`: реалізації `web_search`, `read_url`, `write_report`, JSON Schema tool definitions і tool registry.
- `agent.py`: власний ReAct loop: LLM API call, обробка `tool_calls`, виконання tools, додавання tool observations у `messages`.
- `main.py`: інтерактивний REPL; один екземпляр `ResearchAgent` зберігає пам'ять діалогу в межах сесії.
- `example_output/report.md`: приклад структури звіту.
- `resources/`: матеріали лекції та посилання на статті про prompt engineering і ReAct.

## E2E evidence

Після запуску з локальною Gemma 4 результати трьох перевірочних прогонів збережено в `example_output/`:

- `e2e_test_summary.md`: короткий transcript, аналіз кроків і чеклист вимог ДЗ.
- `test_1_react_vs_cot_comparison.md`: звіт про ReAct loop vs Chain-of-Thought.
- `test_2_rag_comparison_report.md`: звіт про naive RAG, sentence-window retrieval і parent-child retrieval.
- `test_3_agent_prompt_engineering_analysis.md`: звіт про практики Prompt Engineering з лекції.

## Що реалізовано

- Власний ReAct loop без `create_react_agent`, `create_agent`, `AgentExecutor`, `MemorySaver` або LangGraph.
- Tool calling через JSON Schema у форматі OpenAI-compatible API.
- Пам'ять діалогу через список `messages` у класі `ResearchAgent`.
- Логування кожної ітерації: назва tool, аргументи, скорочений результат.
- Обробка помилок tools: помилка повертається в контекст як observation, а агент може продовжити.
- Ліміт ітерацій через `settings.max_iterations`, після якого агент робить фінальну відповідь без нових tool calls.
- Покращений system prompt із чіткою роллю, ReAct-стратегією, self-reflection перед збереженням звіту, обмеженнями і правилами роботи з недовіреним вебконтентом.

## Приклад логу

```text
You: Порівняй naive RAG та sentence-window retrieval

--- ReAct iteration 1 ---
Tool call: web_search({"query": "naive RAG approach explained"})
Result: [
  {
    "title": "...",
    "url": "https://...",
    "snippet": "..."
  }
]

--- ReAct iteration 2 ---
Tool call: read_url({"url": "https://example.com/rag-comparison"})
Result: URL: https://example.com/rag-comparison

Article text...

--- ReAct iteration 3 ---
Tool call: write_report({"filename": "rag_comparison.md", "content": "# RAG Comparison..."})
Result: Report saved to: C:\...\homework-lesson-4\output\rag_comparison.md

Agent:
Звіт збережено у `output/rag_comparison.md`. Основна різниця: ...
```

## Структура

```text
homework-lesson-4/
├── main.py
├── agent.py
├── tools.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── example_output/
│   └── report.md
├── resources/
│   ├── (7981) Understanding ReACT with LangChain - YouTube.url
│   ├── Prompt engineering _ OpenAI API.url
│   ├── Prompting Techniques _ Prompt Engineering Guide.url
│   ├── Untitled.url
│   └── Лекція 4 – Prompt Engineering.pptx
└── README.md
```
