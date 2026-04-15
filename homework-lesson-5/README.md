# Завдання: Research Agent з RAG-системою

Розширте свого Research Agent з `homework-lesson-3` — додайте **RAG-інструмент** з гібридним пошуком та reranking, щоб агент міг шукати не лише в інтернеті, а й у локальній базі знань.

---

### Що змінюється порівняно з попередніми homework

| Було (homework-lesson-3)                        | Стає (homework-lesson-5) |
|-------------------------------------------------|---|
| Tools: `web_search`, `read_url`, `write_report` | + новий tool: `knowledge_search` |
| Агент шукає лише в інтернеті                    | Агент шукає і в інтернеті, і в локальній базі знань |
|                                                 | Є pipeline для завантаження документів у векторну БД |
|                                                 | Hybrid search (semantic + BM25) з cross-encoder reranking |

---

### Що потрібно реалізувати

#### 1. Knowledge Ingestion Pipeline (`ingest.py`)

Скрипт, який завантажує документи у векторну базу даних:

- **Завантаження документів** — PDF файли з директорії `./data/`
- **Chunking** — розбиття на чанки з `RecursiveCharacterTextSplitter` (або semantic chunking — за бажанням)
- **Embeddings** — використайте `text-embedding-3-small` або `text-embedding-3-large`
- **Векторна БД** — Qdrant у Docker
- **Збереження індексу** — vectors зберігаються у Qdrant Docker volume, а chunks для BM25 і manifest зберігаються локально в `index/`

Скрипт запускається окремо: `python ingest.py` або `uv run python ingest.py` — і створює/оновлює Qdrant collection та локальні BM25 chunks.

#### 2. Hybrid Retrieval з Reranking (`retriever.py`)

Модуль, що реалізує пошук по базі знань:

- **Semantic search** — пошук за cosine similarity у векторній БД
- **BM25 search** — лексичний пошук за ключовими словами
- **Ensemble** — об'єднання результатів semantic + BM25 (наприклад, через `EnsembleRetriever` або вручну)
- **Reranking** — cross-encoder reranker (наприклад, `BAAI/bge-reranker-base`) для фільтрації шуму

#### 3. RAG Tool для агента (`tools.py`)

Новий tool `knowledge_search`, який агент використовує поряд з `web_search`, `read_url`, `write_report`:

```python
def knowledge_search(query: str) -> str:
    """Search the local knowledge base. Use for questions about ingested documents."""
    ...
```

Агент сам вирішує, коли шукати в інтернеті (`web_search`), а коли — в локальній базі (`knowledge_search`).

#### 4. Тестові дані (`data/`)

У `./data/` вже є декілька документів для тестування. За бажанням, додайте ще для перевірки роботи системи з різними типами.

---

### Структура проекту

```
homework-lesson-5/
├── main.py              # Entry point (з homework-lesson-3/4, адаптований)
├── agent.py             # Agent setup з новим knowledge_search tool
├── tools.py             # web_search, read_url, write_report, knowledge_search
├── retriever.py         # Hybrid retrieval + reranking logic
├── ingest.py            # Ingestion pipeline: docs → chunks → embeddings → vector DB
├── config.py            # Settings
├── requirements.txt     # Залежності
├── data/                # Документи для ingestion
│   └── (ваші PDF/TXT файли)
├── index/               # Generated chunks для BM25, не комітиться
├── uml_diagram/         # Mermaid UML-діаграми
├── SUBMISSION_NOTES.md  # Опис ходу роботи для перевірки
└── .env                 # API ключі (не комітити!)
```

---

### Запуск реалізації

1. Встановіть залежності:
   ```powershell
   cd C:\Users\vetal\PycharmProjects\ROBOT-DREAMS-MULTI-AGENT-SYSTEMS
   uv sync
   ```

2. Налаштуйте `.env` у корені репозиторію. Якщо чат-модель працює через LM Studio, а embeddings — через інший endpoint, можна розділити налаштування. Якщо `OPENAI_BASE_URL` вказує на `localhost` або `127.0.0.1`, embeddings за замовчуванням будуть відправлені в `https://api.openai.com/v1`.
   ```env
   OPENAI_API_KEY=...
   OPENAI_BASE_URL=http://127.0.0.1:1234/v1
   MODEL_NAME=google/gemma-4-26b-a4b

   OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
   OPENAI_EMBEDDING_API_KEY=...
   EMBEDDING_MODEL=text-embedding-3-small

   QDRANT_URL=http://localhost:6333
   QDRANT_COLLECTION=homework_lesson_5_knowledge
   ```

3. Запустіть Qdrant на стандартних портах:
   ```powershell
   docker run -d --name qdrant `
     -p 6333:6333 `
     -p 6334:6334 `
     -v qdrant_storage:/qdrant/storage `
     qdrant/qdrant:latest
   ```

   Якщо контейнер уже створений:
   ```powershell
   docker start qdrant
   ```

4. Створіть chunks, embeddings і наповніть Qdrant:
   ```powershell
   cd homework-lesson-5
   uv run python ingest.py
   ```

5. Запустіть агента:
   ```powershell
   uv run python main.py
   ```

6. Для правильного відображення UML-діаграм у Markdown потрібна підтримка Mermaid. У PyCharm/IntelliJ встановіть плагін Mermaid або відкривайте файл у GitHub/GitLab/VS Code з Mermaid preview.

Додаткова документація:
- `SUBMISSION_NOTES.md` — опис виконаних кроків у форматі `Намір - Дія - Висновок`.
- `uml_diagram/RAG_SYSTEM_MERMAID.md` — Mermaid-схеми ingestion, retrieval та компонентів.

---

### Очікуваний результат

1. **Ingestion працює** — `python ingest.py` завантажує документи з `./data/`, створює chunks, рахує embeddings, наповнює Qdrant і зберігає `index/chunks.json` для BM25
2. **Hybrid search** — пошук використовує і semantic, і BM25, результати об'єднуються
3. **Reranking** — cross-encoder фільтрує нерелевантні результати
4. **Агент використовує RAG** — агент самостійно вирішує, коли шукати в базі знань, а коли в інтернеті
5. **Multi-step reasoning** — агент комбінує результати з різних джерел (web + knowledge base)
6. **Звіт** — агент генерує Markdown-звіт з посиланнями на джерела

Приклад логу в консолі:
```
You: Що таке RAG і які є підходи до retrieval?

🔧 Tool call: knowledge_search(query="RAG retrieval approaches")
📎 Result: [3 documents found]
   - [Page 2] Retrieval-augmented generation combines...
   - [Page 5] Hybrid search approaches include...
   - [Page 3] Dense retrieval using bi-encoders...

🔧 Tool call: web_search(query="RAG retrieval techniques 2026")
📎 Result: Found 5 results...

🔧 Tool call: read_url(url="https://example.com/advanced-rag")
📎 Result: [5000 chars] Latest RAG techniques...

🔧 Tool call: write_report(filename="rag_approaches.md", content="# RAG Approaches...")
📎 Result: Report saved to output/rag_approaches.md

Agent: RAG — це техніка, де...
```
