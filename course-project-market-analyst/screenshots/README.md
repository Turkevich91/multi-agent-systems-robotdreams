# Screenshots

Ця папка містить reviewer evidence для фінального course project. Скріни залишені як доказ реального live demo: UI був запущений локально, workflow пройшов Human Criteria Gate, згенерував AI-suggested critic, створив фінальний report, Mermaid diagrams і Langfuse evaluator scores.

## `ui/`

Скріншоти з React/Vite dashboard:

- completed dashboard зі статусом `completed`, agent stream, final report і Mermaid panel;
- fullscreen final report;
- Human Criteria Gate з базовими критиками `Financial Critic` і `Risk Manager`;
- AI-suggested `Distribution Channel Critic`, доданий через кнопку `Suggest AI critic`;
- 5 результатних Mermaid diagrams: market entry flow, payback gate, validation timeline, saturation map і critic score share.

## `langfuse/`

Скріншоти з окремого Langfuse project `CourseWork`:

- `trace-tree.png` - trace tree для `course-project-market-analyst` з nested LangGraph/model/tool observations;
- `scores.png` - evaluator scores для реальних traces;
- `evals.png` - 4 active LLM-as-a-Judge evaluators;
- `prompts.png` - список course-project prompts у Langfuse Prompt Management;
- `pt-analyst.png`, `pt-critic.png`, `pt-compiler.png` - prompt detail pages для трьох основних system prompts.

## Notes

Скріншоти не містять `.env`, API keys або приватний код. Generated report/output файли залишаються окремими artifacts; screenshots потрібні саме для швидкої візуальної перевірки demo без ручного запуску.
