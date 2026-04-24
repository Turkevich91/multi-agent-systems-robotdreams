# Homework Lesson 10: Evaluating a Multi-Agent RAG System

Це ДЗ додає автоматизований evaluation layer до системи з `homework-lesson-8`.
Архітектура агентів не переписувалась: Supervisor як і раніше координує `Planner -> Researcher -> Critic -> save_report`, а урок 10 перевіряє якість цієї системи через DeepEval, golden dataset і LLM-as-a-Judge.

## Що реалізовано

| Вимога | Реалізація |
|---|---|
| Golden Dataset 15-20 прикладів | `tests/golden_dataset.json`: 15 прикладів, по 5 happy path, edge case і failure case |
| Component tests | `test_planner.py`, `test_researcher.py`, `test_critic.py` |
| Tool correctness | `test_tools.py`: Planner, Researcher, Supervisor/save_report |
| End-to-end evaluation | `test_e2e.py`: повний golden baseline з Answer Relevancy/Failure Safety + Correctness |
| Custom metric | `Homework Agent Policy Fit` у `test_e2e.py` |
| Thresholds | 0.7 для relevancy/plan/groundedness/critique, 0.6 для correctness/business baseline |
| Запуск через DeepEval | `uv run deepeval test run tests/` |

## Модельна схема

- Target system: локальна LM Studio модель з кореневого `.env` (`MODEL_NAME`, `OPENAI_BASE_URL`).
- Judge model: `EVAL_MODEL=gpt-5.4-mini`.
- DeepEval judge має ходити в official OpenAI API, тому `tests/conftest.py` тимчасово відновлює `OPENAI_BASE_URL=https://api.openai.com/v1`, якщо кореневий `.env` вказує на LM Studio.
- `OPENAI_API_KEY` потрібен тільки для judge-метрик DeepEval.

## Структура

```text
homework-lesson-10/
├── agents/                      # Planner, Researcher, Critic з hw8
├── data/                        # PDF corpus для RAG ingestion
├── tests/
│   ├── golden_dataset.json
│   ├── baseline_outputs.json
│   ├── conftest.py
│   ├── eval_config.py
│   ├── test_planner.py
│   ├── test_researcher.py
│   ├── test_critic.py
│   ├── test_tools.py
│   └── test_e2e.py
├── reviewer_artifacts/
│   └── hw10_baseline_eval_summary.md
├── uml_diagrams/
│   └── HW10_EVAL_MERMAID.md
├── config.py
├── ingest.py
├── main.py
├── retriever.py
├── schemas.py
├── supervisor.py
├── tools.py
├── SUBMISSION_NOTES.md
└── README.md
```

## Як запустити

З кореня репозиторію:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-10
uv run python -m compileall .
uv run deepeval test run tests/
```

Лише deterministic/tool smoke test без OpenAI judge:

```powershell
cd C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-10
uv run deepeval test run tests/test_tools.py
```

Для live RAG/system прогонів потрібен той самий bootstrap, що у HW8:

```powershell
docker start qdrant
uv run python ingest.py
uv run python main.py
```

Урок 10 насамперед перевіряє evaluation harness. Тому `baseline_outputs.json` лежить у репозиторії як reviewed baseline: перевіряючий може побачити, що саме оцінюється, навіть без LM Studio, Qdrant і live запуску агентів.

## Thresholds

| Metric | Threshold | Чому так |
|---|---:|---|
| Plan Quality | 0.7 | План має бути конкретним, але локальна модель може формулювати неідеально |
| Research Groundedness | 0.7 | Факти мають спиратися на retrieval context |
| Critique Quality | 0.7 | Critic має давати actionable оцінку |
| Answer Relevancy | 0.7 | Відповідь має відповідати input; застосовується до happy/edge cases |
| Correctness | 0.6 | Baseline-рівень для недетермінованої системи, без завищення до 0.95 |
| Failure Case Safety | 0.7 | Для refusal cases Answer Relevancy може карати безпечну відмову, тому потрібна safety-aware метрика |
| Homework Agent Policy Fit | 0.6 | Custom metric перевіряє бізнес-логіку: RAG/web вибір, HITL, чесність джерел |

## Перевірений smoke result

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

Під час першого повного E2E-прогону `AnswerRelevancyMetric` показав обмеження на malicious/refusal case: безпечна відмова на запит про викрадення `.env` ключів отримала низьку relevancy, бо не виконувала шкідливий intent. Після цього failure cases переведені на `Correctness + Failure Case Safety`, що краще відповідає підходу з лекції: метрика має відповідати типу поведінки, яку ми хочемо винагороджувати. Повторний повний E2E після цієї правки пройшов 16/16, а весь каталог `tests/` пройшов 22/22.
