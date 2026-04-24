import os
import sys
from pathlib import Path

from deepeval import log_hyperparameters
from dotenv import load_dotenv


HW10_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HW10_DIR.parent

sys.path.insert(0, str(HW10_DIR))
load_dotenv(REPO_ROOT / ".env", override=False)

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# DeepEval is the judge layer, not the local target system. The root .env keeps
# OPENAI_BASE_URL pointed at LM Studio for the homework agents, so evals restore
# the official OpenAI endpoint while preserving the local target value for docs
# or optional live-system runners.
base_url = os.getenv("OPENAI_BASE_URL", "")
if base_url.startswith(("http://127.0.0.1", "http://localhost")):
    os.environ.setdefault("HW10_TARGET_OPENAI_BASE_URL", base_url)
    os.environ["OPENAI_BASE_URL"] = "https://api.openai.com/v1"


@log_hyperparameters
def deepeval_hyperparameters():
    return {
        "target_system": "homework-lesson-10 copy of homework-lesson-8",
        "target_chat_model": os.getenv("MODEL_NAME", "local LM Studio model"),
        "target_base_url": os.getenv("HW10_TARGET_OPENAI_BASE_URL", "OpenAI-compatible local endpoint"),
        "judge_model": os.getenv("EVAL_MODEL", "gpt-5.4-mini"),
        "golden_dataset_size": "15",
    }
