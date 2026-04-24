import json

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from schemas import ResearchPlan
from tests.eval_config import EVAL_MODEL, require_judge_model


PLANNER_INPUT = "Compare naive RAG, sentence-window retrieval, and parent-child retrieval. Write a report."

PLANNER_OUTPUT = json.dumps(
    {
        "goal": "Compare three RAG retrieval strategies and explain their trade-offs for report writing.",
        "search_queries": [
            "naive RAG fixed chunk retrieval tradeoffs",
            "sentence-window retrieval RAG context preservation",
            "parent-child retrieval small chunks parent documents",
            "hybrid retrieval reranking RAG evaluation",
        ],
        "sources_to_check": ["knowledge_base", "web"],
        "output_format": "Markdown report with summary, comparison table, practical trade-offs, limitations, and sources.",
    },
    ensure_ascii=False,
    indent=2,
)


def test_planner_output_matches_research_plan_schema():
    plan = ResearchPlan.model_validate_json(PLANNER_OUTPUT)

    assert plan.goal
    assert len(plan.search_queries) >= 3
    assert "knowledge_base" in plan.sources_to_check
    assert "web" in plan.sources_to_check
    assert "Markdown" in plan.output_format


def test_planner_plan_quality():
    require_judge_model()

    metric = GEval(
        name="Plan Quality",
        evaluation_steps=[
            "Check that the plan contains specific search queries, not vague placeholders.",
            "Check that sources_to_check is appropriate for local RAG plus fresh confirmation.",
            "Check that output_format matches the requested final report.",
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=EVAL_MODEL,
        threshold=0.7,
        async_mode=False,
    )
    test_case = LLMTestCase(input=PLANNER_INPUT, actual_output=PLANNER_OUTPUT)

    assert_test(test_case, [metric], run_async=False)
