# HW10 Baseline Eval Summary

Цей artifact створений для швидкого рев'ю без запуску локальної інфраструктури.

## Dataset

| Category | Count | Purpose |
|---|---:|---|
| happy_path | 5 | Типові research/RAG/evaluation запити |
| edge_case | 5 | Короткі, широкі, двомовні, fresh-data та infrastructure запити |
| failure_case | 5 | Safety, fabrication, HITL bypass, nonsense, credential theft |

## Metrics

| Test file | Metric | Threshold |
|---|---|---:|
| `test_planner.py` | GEval Plan Quality | 0.7 |
| `test_researcher.py` | GEval Research Groundedness | 0.7 |
| `test_critic.py` | GEval Critique Quality | 0.7 |
| `test_tools.py` | ToolCorrectnessMetric | 0.5 |
| `test_e2e.py` | AnswerRelevancyMetric for happy/edge cases | 0.7 |
| `test_e2e.py` | GEval Correctness for all cases | 0.6 |
| `test_e2e.py` | GEval Failure Case Safety for failure cases | 0.7 |
| `test_e2e.py` | GEval Homework Agent Policy Fit | 0.6 |

## Current Smoke Result

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

One full E2E baseline experiment was run before the metric split. It found a useful metric-design issue: `AnswerRelevancyMetric` failed the malicious `.env` exfiltration refusal because the safe answer did not satisfy the harmful intent. This is why failure cases now use the safety-aware GEval metric instead of Answer Relevancy. After that correction, the full `test_e2e.py` pass rate is 100%, and the full `tests/` directory passes 22/22.
