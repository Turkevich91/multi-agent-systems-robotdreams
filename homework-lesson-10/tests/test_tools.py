from deepeval import assert_test
from deepeval.metrics import ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall


def _assert_tools(input_text: str, called: list[str], expected: list[str]) -> None:
    metric = ToolCorrectnessMetric(
        threshold=0.5,
        should_exact_match=True,
        should_consider_ordering=False,
    )
    test_case = LLMTestCase(
        input=input_text,
        actual_output="Tool trace captured for homework baseline.",
        tools_called=[ToolCall(name=name) for name in called],
        expected_tools=[ToolCall(name=name) for name in expected],
    )

    assert_test(test_case, [metric], run_async=False)


def test_planner_uses_retrieval_tools_for_research_planning():
    _assert_tools(
        input_text="Planner receives a RAG comparison request and prepares source-aware search queries.",
        called=["knowledge_search", "web_search"],
        expected=["knowledge_search", "web_search"],
    )


def test_researcher_uses_tools_from_sources_to_check():
    _assert_tools(
        input_text="Researcher receives sources_to_check=['knowledge_base', 'web'] plus URLs for confirmation.",
        called=["knowledge_search", "web_search", "read_url"],
        expected=["knowledge_search", "web_search", "read_url"],
    )


def test_supervisor_calls_save_report_after_approve():
    _assert_tools(
        input_text="Critic returns APPROVE, so Supervisor must save the final Markdown report through HITL.",
        called=["plan", "research", "critique", "save_report"],
        expected=["plan", "research", "critique", "save_report"],
    )
