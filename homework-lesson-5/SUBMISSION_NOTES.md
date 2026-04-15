# Домашнє завдання 5: Research Agent з RAG-системою

## Короткий підсумок

У межах домашнього завдання було реалізовано Research Agent з локальною RAG-системою. Агент отримав новий інструмент `knowledge_search`, який шукає у локальній базі знань, побудованій на PDF-документах з директорії `data`.

Векторною базою даних обрано Qdrant у Docker. Для semantic search використовуються OpenAI embeddings `text-embedding-3-small`, для lexical search використовується BM25, а фінальні результати проходять reranking через cross-encoder `BAAI/bge-reranker-base`.

Частину артефактів не потрібно відправляти в Git: Docker volume з Qdrant, локальний індекс `index/`, кеші Python та ключі API. Тому нижче описано хід роботи у форматі `Намір - Дія - Висновок`.

## Намір - Дія - Висновок

| Намір | Дія | Висновок |
|---|---|---|
| Зрозуміти вимоги домашнього завдання | Переглянуто `README.md`, навчальні ресурси та структуру `homework-lesson-5` | Потрібно реалізувати ingestion pipeline, hybrid retrieval, reranking і підключити RAG як tool агента |
| Вибрати векторну базу даних | Обрано Qdrant, оскільки він ближчий до production-підходу і працює як окремий сервіс | Векторне сховище винесено в Docker-контейнер, а локально зберігаються лише допоміжні chunks для BM25 |
| Запустити Qdrant | Піднято контейнер Docker `qdrant/qdrant:latest` з портами `6333:6333` і `6334:6334`, storage винесено у Docker volume `qdrant_storage` | Qdrant доступний на `http://localhost:6333`, стан collection після ingestion - `green` |
| Налаштувати конфігурацію проєкту | У `config.py` додано параметри для OpenAI embeddings, Qdrant URL, назви collection, batch size, chunk size, top-k і reranking | Chat model може працювати через LM Studio, а embeddings можуть окремо йти в OpenAI API |
| Не змішувати chat endpoint і embeddings endpoint | Додано логіку: якщо `OPENAI_BASE_URL` локальний (`localhost` або `127.0.0.1`), embeddings за замовчуванням йдуть у `https://api.openai.com/v1` | Gemma4 залишається chat-моделлю в LM Studio, а `text-embedding-3-small` використовується через OpenAI API |
| Реалізувати завантаження документів | У `ingest.py` додано підтримку PDF, TXT і MD файлів з директорії `data` | Для поточного набору даних завантажено 3 PDF-документи |
| Реалізувати chunking | Документи розбиті через `RecursiveCharacterTextSplitter` з `chunk_size=500` і `chunk_overlap=100` | З 52 сторінок/документів отримано 464 чанки |
| Створити embeddings | Для кожного чанка згенеровано embedding моделлю `text-embedding-3-small` | Розмір вектора становить 1536 |
| Наповнити Qdrant | У `ingest.py` реалізовано створення або перестворення collection `homework_lesson_5_knowledge` і batch upsert vectors + payload | У Qdrant записано 464 points |
| Зберегти chunks для BM25 | Після ingestion локально створюється `index/chunks.json` з текстом чанків і metadata | BM25 може працювати локально без повторного читання PDF |
| Не комітити generated artifacts | У `.gitignore` додано правило `homework-lesson-*/index/` | Локальний індекс не потрапляє в Git, але може бути відтворений командою `uv run python ingest.py` |
| Реалізувати semantic retrieval | У `retriever.py` додано пошук у Qdrant через query vector | Semantic search знаходить релевантні chunks за змістом, навіть якщо формулювання запиту відрізняється від тексту документа |
| Реалізувати lexical retrieval | У `retriever.py` додано BM25 через `rank_bm25` | Lexical search доповнює semantic search, особливо для точних термінів і назв |
| Об'єднати результати semantic + BM25 | Реалізовано hybrid ensemble через Reciprocal Rank Fusion з вагами semantic і BM25 | Результати з двох retrieval-підходів об'єднуються в один ранжований список |
| Додати reranking | Після hybrid retrieval кандидати проходять reranking через `BAAI/bge-reranker-base` | Фінальні результати стають точнішими, бо cross-encoder оцінює пару `query + chunk` |
| Зробити fallback для reranking | Якщо reranker недоступний, система повертає hybrid results без падіння всього tool | Агент може продовжувати роботу навіть за проблем із HuggingFace або локальним кешем reranker |
| Реалізувати `knowledge_search` tool | У `tools.py` додано tool, який викликає hybrid retriever і повертає source, page, scores та текст chunk | Агент отримав доступ до локальної бази знань |
| Відновити web tools | У `tools.py` реалізовано `web_search`, `read_url` і `write_report` | Агент може комбінувати локальний RAG з веб-пошуком і зберігати Markdown-звіти |
| Підключити tools до агента | В `agent.py` створено LangChain agent з tools: `knowledge_search`, `web_search`, `read_url`, `write_report` | Агент сам може вирішувати, коли шукати в локальній базі, а коли використовувати веб |
| Оновити CLI-запуск | У `main.py` додано streaming tool calls, thread config, UTF-8 console setup і обробку recursion limit | Під час запуску видно, які tools викликає агент і що вони повертають |
| Оновити залежності | У `pyproject.toml` і `requirements.txt` додано `qdrant-client`, `rank-bm25`, `sentence-transformers`, `pypdf` та інші потрібні пакети | Проєкт може встановити всі залежності для ingestion, retrieval і reranking |
| Документувати запуск | У `README.md` додано команди для запуску Qdrant, ingestion і агента | Перевіряючий може відтворити pipeline без Docker volume та локального індексу з репозиторію |
| Перевірити Qdrant | Після ingestion виконано перевірку collection через Qdrant client | Collection `homework_lesson_5_knowledge` має 464 points, status `green`, vector size `1536`, distance `Cosine` |
| Перевірити `knowledge_search` | Виконано тестовий запит `What is retrieval augmented generation and hybrid search?` | Tool повернув 3 релевантні chunks з локальних PDF, включно з `retrieval-augmented-generation.pdf` і `large-language-model.pdf` |

## Команди для відтворення

### 1. Запустити Qdrant

```powershell
docker run -d --name qdrant `
  -p 6333:6333 `
  -p 6334:6334 `
  -v qdrant_storage:/qdrant/storage `
  qdrant/qdrant:latest
```

Якщо контейнер уже існує, достатньо:

```powershell
docker start qdrant
```

### 2. Перевірити `.env`

У корені курсу має бути `.env`. Значення ключів не потрібно комітити.

Приклад потрібної структури:

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
MODEL_NAME=google/gemma-4-26b-a4b
TEMPERATURE=0.2
REQUEST_TIMEOUT=120
MAX_RETRIES=1
```

Якщо chat-модель працює локально через LM Studio, а embeddings потрібно рахувати через OpenAI API, можна додати окремі параметри:

```env
OPENAI_EMBEDDING_API_KEY=...
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
```

### 3. Запустити ingestion

```powershell
cd C:\Users\vetal\PycharmProjects\ROBOT-DREAMS-MULTI-AGENT-SYSTEMS\homework-lesson-5
uv run python ingest.py
```

Очікуваний результат для поточного набору PDF:

```text
Loaded 52 document pages/files from 3 source files
Created 464 chunks (chunk_size=500, overlap=100)
Embedding vector size: 1536
Saved 464 chunks to Qdrant collection 'homework_lesson_5_knowledge'
```

### 4. Перевірити Qdrant collection

```powershell
uv run python -c "from qdrant_client import QdrantClient; from config import settings; c=QdrantClient(url=settings.qdrant_url); print(c.count(collection_name=settings.qdrant_collection, exact=True).count)"
```

Очікуваний результат:

```text
464
```

### 5. Перевірити локальний RAG tool

```powershell
uv run python -c "from tools import knowledge_search; print(knowledge_search.invoke({'query': 'What is retrieval augmented generation and hybrid search?'})[:1500])"
```

Очікуваний результат: відповідь має містити локальні sources, page numbers, hybrid score, rerank score і текст знайдених chunks.

### 6. Запустити агента

```powershell
uv run python main.py
```

Приклад запиту:

```text
Що таке RAG і чим hybrid retrieval кращий за чистий semantic search?
```

## Що не комітиться

| Артефакт | Чому не комітиться |
|---|---|
| `.env` | Містить API ключі та локальні налаштування |
| `homework-lesson-5/index/` | Generated BM25 chunks і manifest, відтворюються через `ingest.py` |
| Docker volume `qdrant_storage` | Містить векторну базу Qdrant, не є частиною Git-репозиторію |
| `__pycache__/` | Python cache |
| HuggingFace cache | Локальний кеш reranker model, завантажується автоматично |

## Поточний результат

Стан реалізації після виконання ingestion:

```text
Qdrant collection: homework_lesson_5_knowledge
Points count: 464
Collection status: green
Vector size: 1536
Distance: Cosine
Embedding model: text-embedding-3-small
Reranker: BAAI/bge-reranker-base
```

Система виконує повний RAG pipeline:

```text
PDF documents -> chunks -> OpenAI embeddings -> Qdrant vectors
User query -> query embedding -> Qdrant semantic search
User query -> BM25 lexical search
Semantic + BM25 -> hybrid ranking -> cross-encoder reranking
Final chunks -> knowledge_search tool -> Research Agent
```
