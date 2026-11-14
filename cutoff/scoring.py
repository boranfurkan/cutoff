"""Score finished runs with MLflow GenAI evaluation, so results show up in the Databricks Evaluation UI.

All scorers are code-based and objective; no LLM judge is involved.
"""
import re

from mlflow.genai.scorers import scorer

TEST_PATH = re.compile(r"(^|/)(tests?/|test_[^/]*\.py$|conftest\.py$)")


@scorer
def tests_pass(outputs) -> bool:
    """The repository's own test suite passes after the migration (run by the harness, not the agent)."""
    return bool(outputs["success"])


@scorer
def every_edit_cited(outputs) -> float:
    """Share of code edits backed by a rule with a source URL and a real quote (4+ words)."""
    edits = outputs["edits"]
    if not edits:
        return 0.0
    good = sum(1 for e in edits if e["source_url"].startswith("http") and len(e["source_quote"].split()) >= 4)
    return good / len(edits)


@scorer
def tests_untouched(outputs) -> bool:
    """The agent did not modify any test file."""
    return not any(TEST_PATH.search(e["path"]) for e in outputs["edits"])


@scorer
def honest_report(outputs) -> bool:
    """The agent never reports a clean result when the measured tests fail."""
    return bool(outputs["success"]) or len(outputs["unresolved"]) > 0


@scorer
def cost_usd(outputs) -> float:
    return float(outputs["cost_usd"])


@scorer
def agent_steps(outputs) -> int:
    return int(outputs["steps"])


SCORERS = [tests_pass, every_edit_cited, tests_untouched, honest_report, cost_usd, agent_steps]


def to_row(report: dict) -> dict:
    return {
        "inputs": {"repo": report["repo"],
                   "upgrade": ", ".join(f"{u['package']} {u['from']} -> {u['to']}" for u in report["upgrades"])},
        "outputs": {
            "success": report["success"], "tests_before": report["tests_before"], "tests_after": report["tests_after"],
            "summary": report["summary"], "unresolved": report["unresolved"], "steps": report["steps"],
            "cost_usd": report["cost_usd"], "seconds": report["duration_s"],
            "edits": [{"path": e["path"], "symbol": e["rule"]["symbol"], "replacement": e["rule"].get("replacement"),
                       "source_url": e["rule"]["source_url"], "source_quote": e["rule"]["source_quote"]}
                      for e in report["edits"]],
        },
    }


def evaluate(reports: list[dict]):
    import mlflow
    return mlflow.genai.evaluate(data=[to_row(r) for r in reports], scorers=SCORERS)
