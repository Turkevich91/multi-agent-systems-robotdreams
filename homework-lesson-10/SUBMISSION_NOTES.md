# Submission Notes: Homework Lesson 10

## Коротко

ДЗ 10 перетворює multi-agent RAG систему з `homework-lesson-8` на систему з вимірюваною якістю. Агентний runtime залишився знайомим: `Supervisor -> Planner -> Researcher -> Critic -> save_report`. Новий шар - це DeepEval tests, golden dataset, baseline outputs, component-level метрики, tool correctness і end-to-end evaluation.

Мета для перевіряючого: можна відкрити код, JSON datasets, Mermaid-діаграми і ці нотатки та зрозуміти, що саме тестується, без обов'язкового запуску LM Studio або Qdrant.

## Evidence Map

| Артефакт | Що показує |
|---|---|
| `tests/golden_dataset.json` | 15 reviewed прикладів: happy path, edge cases, failure cases |
| `tests/baseline_outputs.json` | Baseline-відповіді, які оцінюються DeepEval-метриками |
| `tests/test_planner.py` | Schema check + GEval Plan Quality |
| `tests/test_researcher.py` | GEval Research Groundedness через retrieval_context |
| `tests/test_critic.py` | Schema check + GEval Critique Quality |
| `tests/test_tools.py` | ToolCorrectnessMetric для Planner, Researcher і Supervisor/save_report |
| `tests/test_e2e.py` | Full golden baseline: AnswerRelevancy/Failure Safety + Correctness + custom business metric |
| `tests/conftest.py` | Розділення target LM Studio endpoint і OpenAI judge endpoint |
| `reviewer_artifacts/hw10_baseline_eval_summary.md` | Коротка карта baseline evaluation для читання без запуску |
| `uml_diagrams/HW10_EVAL_MERMAID.md` | Mermaid-діаграми evaluation architecture |

## Намір - Дія - Висновок

| Намір | Дія | Висновок |
|---|---|---|
| Зберегти контекст HW8 | Перенесено `agents/`, `config.py`, `schemas.py`, `supervisor.py`, `tools.py`, `retriever.py`, `ingest.py`, `main.py` | HW10 тестує ту саму архітектуру, а не нову іграшкову систему |
| Відокремити RAG індекс уроку 10 | У `config.py` collection змінено на `homework_lesson_10_knowledge` | Qdrant дані HW8/HW9/HW10 не змішуються |
| Створити golden dataset | Додано 15 прикладів у `tests/golden_dataset.json` | Виконана вимога 15-20 examples з трьома категоріями |
| Дати baseline без live запуску | Додано `tests/baseline_outputs.json` | Перевіряючий бачить фактичний eval input/output, навіть якщо не запускає LM Studio |
| Перевірити Planner | `test_planner.py` валідовує `ResearchPlan` і оцінює Plan Quality через GEval | План має конкретні queries, sources_to_check і output_format |
| Перевірити Researcher | `test_researcher.py` використовує retrieval_context і GEval Research Groundedness | Окремо тестується groundedness, а не просто гарна мова |
| Перевірити Critic | `test_critic.py` валідовує `CritiqueResult` і Critique Quality | Critic повинен давати конкретний verdict і обгрунтування |
| Перевірити tools | `test_tools.py` використовує ToolCorrectnessMetric | Зафіксовано очікувані tool calls: `knowledge_search`, `web_search`, `read_url`, `save_report` |
| Перевірити end-to-end якість | `test_e2e.py` запускає baseline по всіх 15 golden cases | Є regression harness для всієї системної поведінки |
| Додати custom metric | `Homework Agent Policy Fit` перевіряє RAG/web вибір, HITL і відмову від фабрикації | Виконана вимога бізнес-метрики під конкретну систему |
| Не зламати локальне середовище | `conftest.py` переводить DeepEval judge на official OpenAI endpoint, якщо `OPENAI_BASE_URL` вказує на LM Studio | Target model і judge model не конфліктують між собою |
| Залишити перевірку дешевою | `test_tools.py` не використовує LLM judge і вже дає швидкий smoke test | Є легкий прогін перед повним OpenAI judge-run |

## Requirements Checklist

| Вимога README | Статус | Де дивитися |
|---|---|---|
| Golden Dataset 15-20 прикладів | Done | `tests/golden_dataset.json` |
| Happy path + edge cases + failure cases | Done | 5 + 5 + 5 categories |
| Component tests Planner/Researcher/Critic | Done | `test_planner.py`, `test_researcher.py`, `test_critic.py` |
| Tool correctness мінімум 3 кейси | Done | `test_tools.py` |
| End-to-end evaluation на golden dataset | Done | `test_e2e.py` |
| Мінімум 2 метрики E2E | Done | AnswerRelevancyMetric / Failure Case Safety + GEval Correctness |
| Custom GEval metric | Done | `Homework Agent Policy Fit` |
| Обгрунтовані thresholds | Done | README section `Thresholds` |
| `deepeval test run tests/` | Done | Повний каталог `tests/` пройшов: 22 passed, 0 failed |

## Judge/Target Split

Це важливий технічний момент для цього локального середовища:

- HW8/HW10 агенти використовують локальну модель у LM Studio через `OPENAI_BASE_URL=http://127.0.0.1:1234/v1`.
- На момент підготовки submission target model у `.env`: `google/gemma-4-26b-a4b`.
- DeepEval judge використовує OpenAI API і модель з `EVAL_MODEL`.
- У `.env` зараз зафіксовано `EVAL_MODEL="gpt-5.4-mini"`.
- `tests/conftest.py` захищає DeepEval від випадкового походу в LM Studio як judge endpoint.

Тобто локальна Gemma в LM Studio є системою, яку оцінюємо, а `gpt-5.4-mini` є зовнішнім суддею.

## Commands

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-10
uv run python -m compileall .
uv run deepeval test run tests/test_tools.py
uv run deepeval test run tests/
```

Для RAG/live system:

```powershell
docker start qdrant
uv run python ingest.py
uv run python main.py
```

## Verified So Far

```text
uv run python -m compileall homework-lesson-10
OK

cd homework-lesson-10
uv run deepeval test run tests/test_tools.py
3 passed
Pass Rate: 100.0%

uv run deepeval test run tests/test_planner.py
2 passed, Plan Quality: 0.8

uv run deepeval test run tests/test_researcher.py
1 passed, Research Groundedness: 1.0

uv run deepeval test run tests/test_critic.py
2 passed, Critique Quality: 0.9

uv run pytest tests/test_e2e.py::test_custom_business_logic_metric_on_policy_case -q
1 passed

uv run deepeval test run tests/test_e2e.py
16 passed, 0 failed, Pass Rate: 100.0%
Answer Relevancy: 10/10 passed, avg 0.989
Correctness: 15/15 passed, avg 0.953
Failure Case Safety: 5/5 passed, avg 1.000
Homework Agent Policy Fit: 1/1 passed, avg 1.000

uv run deepeval test run tests/
22 passed, 0 failed, Pass Rate: 100.0%
Plan Quality: 1/1 passed, avg 0.800
Research Groundedness: 1/1 passed, avg 1.000
Critique Quality: 1/1 passed, avg 0.900
Tool Correctness: 3/3 passed, avg 1.000
Answer Relevancy: 10/10 passed, avg 1.000
Correctness: 15/15 passed, avg 0.953
Failure Case Safety: 5/5 passed, avg 1.000
Homework Agent Policy Fit: 1/1 passed, avg 1.000
```

Перший повний E2E-прогін був корисним baseline experiment: усі correctness checks пройшли, але `AnswerRelevancyMetric` провалив malicious refusal case про викрадення `.env` ключів. Це очікувана пастка метрик з лекції: relevancy може винагороджувати відповідь на шкідливий intent, тоді як система повинна відмовити. Тому failure cases тепер оцінюються через `Correctness + Failure Case Safety`, а `AnswerRelevancyMetric` використовується для happy/edge research cases. Після правки повний `test_e2e.py` пройшов 16/16, а весь каталог `tests/` пройшов 22/22.

## Що не комітиться

| Артефакт | Чому |
|---|---|
| `.env` | Містить ключі та локальні endpoint-и |
| `index/` | Відтворюється через `uv run python ingest.py` |
| `output/` | Нові live-звіти є локальними runtime artifacts |
| `__pycache__/` | Python cache |
| Qdrant Docker volume | Живе поза Git, відтворюється bootstrap + ingestion |
