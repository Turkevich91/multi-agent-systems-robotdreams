import json

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from schemas import CritiqueResult
from tests.eval_config import EVAL_MODEL, require_judge_model


CRITIC_INPUT = """
User request: Compare naive RAG, sentence-window retrieval, and parent-child retrieval.
Plan: cover retrieval mechanics, trade-offs, limitations, and source selection.
Findings: The research explains all three methods, compares precision/context/cost, and notes that implementation details depend on corpus structure and token budget.
"""

CRITIC_OUTPUT = json.dumps(
    {
        "verdict": "APPROVE",
        "is_fresh": True,
        "is_complete": True,
        "is_well_structured": True,
        "strengths": [
            "The findings compare all three requested retrieval methods.",
            "The trade-offs are concrete enough for a final Markdown report.",
            "Limitations around corpus structure and token budget are stated.",
        ],
        "gaps": [],
        "revision_requests": [],
    },
    ensure_ascii=False,
    indent=2,
)


def test_critic_output_matches_schema():
    critique = CritiqueResult.model_validate_json(CRITIC_OUTPUT)

    assert critique.verdict == "APPROVE"
    assert critique.is_complete
    assert critique.strengths
    assert critique.gaps == []
    assert critique.revision_requests == []


def test_critic_quality_metric():
    require_judge_model()

    metric = GEval(
        name="Critique Quality",
        evaluation_steps=[
            "Check that the critique directly evaluates the original request and research findings.",
            "Check that APPROVE is justified by concrete strengths.",
            "Check that gaps and revision_requests are empty when there are no material issues.",
            "If the verdict were REVISE, revision_requests would need to be actionable.",
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=EVAL_MODEL,
        threshold=0.7,
        async_mode=False,
    )
    test_case = LLMTestCase(input=CRITIC_INPUT, actual_output=CRITIC_OUTPUT)

    assert_test(test_case, [metric], run_async=False)
