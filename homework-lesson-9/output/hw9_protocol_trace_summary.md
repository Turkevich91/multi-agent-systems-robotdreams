# HW9 Protocol Trace Summary

Date: 2026-04-22

This reviewer artifact records the implementation-level smoke checks completed before the full interactive Supervisor/HITL run.

## Environment

- LM Studio OpenAI-compatible server: available at `http://127.0.0.1:1234/v1`
- Active chat model in LM Studio: `google/gemma-4-26b-a4b`
- Qdrant container: running on `localhost:6333`
- HW9 Qdrant collection: `homework_lesson_9_knowledge`

## RAG / Qdrant

- `uv run python ingest.py` completed.
- Documents loaded: 52 pages/files from 3 PDFs.
- Chunks created: 464.
- Qdrant points upserted: 464.
- Count check returned: `464`.
- `knowledge_search_impl("retrieval augmented generation")` returned local chunks from `retrieval-augmented-generation.pdf` and `large-language-model.pdf`.

## MCP Discovery

`SearchMCP` at `http://127.0.0.1:8901/mcp`:

- Tools: `knowledge_search`, `read_url`, `web_search`
- Resources: `resource://knowledge-base-stats`

`ReportMCP` at `http://127.0.0.1:8902/mcp`:

- Tools: `save_report`
- Resources: `resource://output-dir`

## MCP -> LangChain Conversion

`mcp_tools_to_langchain(...)` converted SearchMCP tools into LangChain `StructuredTool` objects:

- Converted tools: `knowledge_search`, `read_url`, `web_search`
- Direct `web_search` tool invocation returned 2417 characters for query `retrieval augmented generation`.

## ACP Discovery

ACP server at `http://127.0.0.1:8903` exposed:

- `planner`
- `researcher`
- `critic`

## ACP Agent Smoke

Planner:

- Request: `Define retrieval augmented generation in a short report plan.`
- Returned valid JSON with keys: `goal`, `search_queries`, `sources_to_check`, `output_format`.

Researcher:

- Request: `Research briefly: What is retrieval augmented generation? Use local knowledge if useful.`
- Returned 1457 characters of source-backed findings.
- Output defined RAG and described retrieval, generation, hallucination reduction, and domain/current-data benefits.

Critic:

- Request: short RAG findings with local source note.
- Returned valid `CritiqueResult` JSON.
- In this local-model smoke, structured-output fallback produced `verdict=REVISE`, which confirms the fallback guard works when LM Studio does not produce a clean `ToolStrategy` response.

## Pending Full Interactive Run

## Full Interactive Supervisor Run

The full Supervisor path was executed on 2026-04-23 with the real local environment:

`Supervisor -> ACP Planner -> ACP Researcher -> ACP Critic -> HITL save_report -> ReportMCP -> output/hw9_rag_comparison_report.md`

### Scenario 1: edit -> approve

User request:

`Compare naive RAG, sentence-window retrieval, and parent-child retrieval. Write a concise Ukrainian Markdown report and save it as hw9_rag_comparison_report.md.`

Observed flow:

1. `delegate_to_planner` returned a structured plan with 4 search queries.
2. `delegate_to_researcher` returned a Ukrainian comparison draft.
3. `delegate_to_critic` returned `APPROVE`.
4. Supervisor called `save_report` with `filename=hw9_rag_comparison_report.md`.
5. HITL decision `edit` requested:
   - add a compact comparison table near the top;
   - mention MCP for tools and ACP for agent delegation.
6. Supervisor revised the report and called `save_report` again.
7. HITL decision `approve` completed the save.
8. `ReportMCP` wrote:
   `C:\Users\vetal\PycharmProjects\multi-agent-systems-robotdreams\homework-lesson-9\output\hw9_rag_comparison_report.md`

### Scenario 2: reject

User request:

`Briefly explain what MCP (Model Context Protocol) is and save it as hw9_reject_smoke.md.`

Observed flow:

1. Supervisor reached `save_report` normally.
2. HITL decision `reject` cancelled the save.
3. Supervisor returned a cancellation message.

### Bug Found and Fixed During Real Run

During the first reject attempt, `main.py:_ensure_report_saved(...)` incorrectly retried `save_report` even after the user explicitly rejected saving.

Fix applied:

- `trace["save_cancelled"]` is now set when the user chooses the full reject path.
- `_ensure_report_saved(...)` now exits immediately when `save_cancelled` is true.

After the fix, the reject scenario completed correctly with no retry and no saved file.

## Reviewer Outcome

- `hw9_rag_comparison_report.md` is the real saved output from the interactive Supervisor/HITL run.
- `hw9_protocol_trace_summary.md` is the real protocol/test trace from MCP, ACP, and interactive save testing.

The system now has evidence for:

- MCP discovery
- ACP discovery
- MCP -> LangChain conversion
- ACP planner/researcher/critic execution
- HITL `edit`
- HITL `approve`
- HITL `reject`

The remaining step, if desired, is only commit/stage hygiene.
