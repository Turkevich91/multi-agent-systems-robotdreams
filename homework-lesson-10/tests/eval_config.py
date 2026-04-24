import json
import os
from pathlib import Path
from typing import Any

import pytest


TESTS_DIR = Path(__file__).resolve().parent
EVAL_MODEL = os.getenv("EVAL_MODEL", "gpt-5.4-mini")


def require_judge_model() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for DeepEval LLM-as-a-judge metrics.")


def load_json(filename: str) -> list[dict[str, Any]]:
    return json.loads((TESTS_DIR / filename).read_text(encoding="utf-8"))


def golden_by_id() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in load_json("golden_dataset.json")}

