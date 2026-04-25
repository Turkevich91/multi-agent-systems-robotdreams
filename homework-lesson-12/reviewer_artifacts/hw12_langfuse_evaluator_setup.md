# Налаштовані Langfuse Evaluators

Ці evaluators були створені в Langfuse UI:

```text
LLM-as-a-Judge -> Evaluators -> Set up evaluator
```

Завдання просить мінімум два evaluators з різними score types. Нижче зафіксована пара, яка була використана у здачі і закриває основні ризики multi-agent RAG системи: релевантність відповіді та groundedness фактів.

## Evaluator 1: Relevance Score

Name:

```text
hw12_relevance_score
```

Score type:

```text
Numeric
```

Recommended range:

```text
0.0 to 1.0
```

Target:

```text
Trace input/output
```

Prompt, внесений у Langfuse:

```text
You are evaluating a multi-agent research assistant.

User input:
{{input}}

Assistant output:
{{output}}

Score how well the output answers the user's actual request.

Use this rubric:
- 1.0: directly answers all important parts of the request
- 0.7: answers the main request but misses some useful detail
- 0.4: partially related but incomplete or too generic
- 0.0: unrelated, evasive, or unusable

Return only a numeric score between 0.0 and 1.0.
```

Чому був обраний цей evaluator:

```text
Supervisor може створити охайний report навіть тоді, коли Planner або Researcher змістилися від початкового запиту. Relevance score ловить саме цей failure mode на рівні final trace.
```

## Evaluator 2: Groundedness Pass

Name:

```text
hw12_groundedness_pass
```

Score type:

```text
Boolean
```

Target:

```text
Trace input/output
```

Prompt, внесений у Langfuse:

```text
You are evaluating whether a multi-agent RAG research report is grounded.

User input:
{{input}}

Assistant output:
{{output}}

Return true only if the answer:
- includes concrete source references, URLs, or local knowledge-base citations
- separates verified facts from uncertainty
- avoids making unsupported claims when sources are missing

Return false if the answer contains important uncited claims, overconfident claims, or no usable source trail.

Return only true or false.
```

Чому був обраний цей evaluator:

```text
MAS поєднує Qdrant RAG і web search. Критичне питання якості не тільки в тому, чи відповідь звучить переконливо, а й у тому, чи її можна простежити до evidence.
```

## Optional Third Evaluator

Цей evaluator не використовувався як обов'язковий evidence у фінальній здачі, але залишений як приклад дешевого розширення evaluation suite.

Name:

```text
hw12_report_structure
```

Score type:

```text
Categorical
```

Categories:

```text
excellent, acceptable, weak
```

Prompt:

```text
Evaluate the structure of the final research report.

User input:
{{input}}

Assistant output:
{{output}}

Return:
- excellent: clear title, executive summary, analysis, trade-offs, limitations, and sources
- acceptable: mostly structured but one section is weak or missing
- weak: hard to scan, missing several expected sections, or not a report

Return only one category.
```
