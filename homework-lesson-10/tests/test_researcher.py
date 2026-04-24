from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from tests.eval_config import EVAL_MODEL, require_judge_model


RESEARCH_INPUT = """
Original request: Compare naive RAG, sentence-window retrieval, and parent-child retrieval.
Plan: use knowledge_base and web; produce a Markdown report with trade-offs and limitations.
"""

RETRIEVAL_CONTEXT = [
    "Naive RAG retrieves fixed-size chunks directly from an index. It is simple but can lose surrounding context.",
    "Sentence-window retrieval indexes sentences and expands the returned context with neighboring sentences.",
    "Parent-child retrieval indexes smaller child chunks while returning a larger parent document or section for generation.",
    "Hybrid retrieval can combine vector search and BM25 with reciprocal rank fusion, then rerank candidate chunks with a cross-encoder.",
]

RESEARCH_OUTPUT = """
Findings:
1. Naive RAG is the simplest approach: split documents into chunks, retrieve top matches, and generate from them. Its weakness is that fixed chunks may omit neighboring context.
2. Sentence-window retrieval improves local coherence by matching at sentence level and returning nearby sentences as the generation context.
3. Parent-child retrieval improves precision and context balance by indexing small child chunks but returning larger parent sections.
4. Hybrid retrieval with BM25, vector search, reciprocal rank fusion, and cross-encoder reranking can improve candidate recall and final precision.

Uncertainty:
These are conceptual retrieval patterns; implementation details depend on corpus structure, token budget, and evaluator metrics.
"""


def test_researcher_groundedness_against_retrieval_context():
    require_judge_model()

    metric = GEval(
        name="Research Groundedness",
        evaluation_steps=[
            "Extract factual claims from the actual output.",
            "Check whether each factual claim is supported by the retrieval context.",
            "Penalize claims that are unsupported by the retrieval context, even if they sound plausible.",
            "Reward explicit uncertainty when implementation details depend on corpus or budget.",
        ],
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT,
        ],
        model=EVAL_MODEL,
        threshold=0.7,
        async_mode=False,
    )
    test_case = LLMTestCase(
        input=RESEARCH_INPUT,
        actual_output=RESEARCH_OUTPUT,
        retrieval_context=RETRIEVAL_CONTEXT,
    )

    assert_test(test_case, [metric], run_async=False)
