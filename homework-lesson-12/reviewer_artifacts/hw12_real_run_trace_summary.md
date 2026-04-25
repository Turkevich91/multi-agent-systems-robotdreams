# HW12 Trace Summary Реальних Прогонів

Цей artifact фіксує реальні Langfuse запуски, які були використані як evidence для перевіряючого.

## Bootstrap Prompt Management

Команда:

```powershell
uv run python bootstrap_langfuse.py
```

Результат:

```text
Created/updated prompt hw12_planner_system v1 labels=['production']
Created/updated prompt hw12_planner_fallback_system v1 labels=['production']
Created/updated prompt hw12_researcher_system v1 labels=['production']
Created/updated prompt hw12_critic_system v1 labels=['production']
Created/updated prompt hw12_critic_fallback_system v1 labels=['production']
Created/updated prompt hw12_supervisor_system v1 labels=['production']
Langfuse prompt bootstrap complete.
```

## Перевірки Інфраструктури

Qdrant collection:

```text
homework_lesson_12_knowledge 464
```

RAG smoke-test:

```text
knowledge_search("retrieval augmented generation") returned chunks from retrieval-augmented-generation.pdf and large-language-model.pdf.
```

## Langfuse Traces

| Trace ID | Query | Result |
|---|---|---|
| `3cd857bb52795e497b04441cc7d5df37` | Explain how Langfuse tracing helps debug a multi-agent RAG workflow. | Smoke E2E до фінального evaluator setup; дійшов до HITL і зберіг `langfuse_multi_agent_rag_debugging.md`. |
| `511ba698fe49808b44662f20495bed96` | Compare naive RAG, sentence-window retrieval, and parent-child retrieval. | Fresh run після активації evaluators; дійшов до HITL і зберіг `rag_comparison_report.md`. |
| `86103007c4203c31c116d8bf0fcf6534` | When should a research agent use local RAG instead of web search? | Fresh run після активації evaluators; дійшов до HITL і зберіг `research_agent_retrieval_strategy.md`. |

## Нотатки

- Langfuse LLM-as-a-Judge evaluators створені в UI і мають status `Active`:
  - `hw12_relevance_score` з numeric output.
  - `hw12_groundedness_pass` з boolean output.
- Фінальні screenshots зроблені з Langfuse UI після того, як evaluator scores завершили async processing.
- `homework-lesson-12/output/` навмисно ігнорується git; generated reports є runtime artifacts.
