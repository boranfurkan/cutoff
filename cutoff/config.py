import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

ORCHESTRATOR_MODEL = os.getenv("CUTOFF_MODEL", "claude-opus-5-5")
EXTRACTOR_MODEL = os.getenv("CUTOFF_EXTRACTOR_MODEL", "claude-sonnet-5-5")
EFFORT = os.getenv("CUTOFF_EFFORT", "high")
MAX_STEPS = int(os.getenv("CUTOFF_MAX_STEPS", "40"))
# Verification is lookup-and-match work, so it runs on a cheaper model by default.
VERIFY_MODEL = os.getenv("CUTOFF_VERIFY_MODEL", "claude-sonnet-5-5")
MAX_VERIFY_STEPS = int(os.getenv("CUTOFF_MAX_VERIFY_STEPS", "16"))
SANDBOX_IMAGE = os.getenv("CUTOFF_SANDBOX_IMAGE", "python:3.12-slim")
RUNS_DIR = ROOT / "runs"

# $ per million tokens (input, output); cache reads are billed at 10% of input, writes at 125%.
PRICES = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}


def cost(model: str, usage) -> float:
    pi, po = PRICES.get(model, (4.0, 20.0))
    read = getattr(usage, "cache_read_input_tokens", 0) or 0
    write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    return (usage.input_tokens * pi + read * pi * 0.1 + write * pi * 1.25 + usage.output_tokens * po) / 1e6


_tracing = None


def tracing():
    """Return the mlflow module with Databricks tracing configured, or None when tracing is off."""
    global _tracing
    if _tracing is None:
        if os.getenv("CUTOFF_TRACE", "0") != "1":
            _tracing = False
        else:
            import mlflow
            mlflow.set_tracking_uri("databricks")
            mlflow.set_experiment(os.getenv("CUTOFF_EXPERIMENT", "/Shared/cutoff"))
            mlflow.anthropic.autolog()
            _tracing = mlflow
    return _tracing or None
