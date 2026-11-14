"""Score the most recent finished run of each seed repo and log the evaluation to Databricks. No model calls.

Usage: CUTOFF_TRACE=1 .venv/bin/python scripts/score_runs.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from cutoff import config, scoring

seeds = {p.name for p in (ROOT / "seeds").iterdir() if p.is_dir()}
latest = {}
for p in sorted((ROOT / "runs").glob("*/report.json"), key=lambda p: p.stat().st_mtime):
    r = json.loads(p.read_text())
    if r["repo"] in seeds:
        latest[r["repo"]] = r
assert config.tracing(), "set CUTOFF_TRACE=1"
result = scoring.evaluate(list(latest.values()))
print(json.dumps(result.metrics, indent=1))
