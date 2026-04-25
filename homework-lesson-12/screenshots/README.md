# Обов'язкові Langfuse Screenshots

Ця папка містить фінальні UI screenshots, які були використані як Langfuse evidence.

| File | Langfuse UI Location | Що Доводить |
|---|---|---|
| `01_trace_tree.png` | `Tracing -> Traces -> open one homework-12 trace` | Повне trace tree містить Supervisor, sub-agents, tool calls і `save_report`. |
| `02_session_grouping.png` | `Sessions -> homework-12-review-session` | Кілька traces згруповані в одну session і прив'язані до user `vetal`. |
| `03_evaluator_scores.png` | `Tracing -> Traces -> open trace -> Scores` або `LLM-as-a-Judge -> Evaluators` | Щонайменше два evaluator scores були створені для fresh traces. |
| `04_prompt_management.png` | `Prompts` | Усі `hw12_*_system` prompts існують з label `production`. |

У фінальних screenshots API keys та secret values не показані.
