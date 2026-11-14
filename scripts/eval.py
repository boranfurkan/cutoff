"""Run the agent on every seed repo and report the pass rate. Logs to Databricks when CUTOFF_TRACE=1.

Usage: CUTOFF_TRACE=1 CUTOFF_STORE=databricks .venv/bin/python scripts/eval.py [seed-name ...] [--workers 3]
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from cutoff import config
from cutoff.agent import Run

ap = argparse.ArgumentParser()
ap.add_argument("seeds", nargs="*")
ap.add_argument("--workers", type=int, default=3)
ap.add_argument("--dir", default="seeds", help="seeds or seeds_silent")
a = ap.parse_args()
seeds = sorted(p for p in (ROOT / a.dir).iterdir() if p.is_dir() and (not a.seeds or p.name in a.seeds))


def one(seed):
    try:
        return Run(seed, None, log=lambda m: print(f"{seed.name:18}{m}", flush=True)).execute()
    except Exception as e:  # noqa: BLE001
        return {"repo": seed.name, "success": False, "summary": f"crashed: {e}", "cost_usd": 0, "steps": 0,
                "edits": [], "rules_used": [], "cited": 0, "fix_seconds": 0, "duration_s": 0, "tests_before": "", "tests_after": "", "upgrades": [],
                "hidden_after": None, "new_tests": []}


t0 = time.time()
with ThreadPoolExecutor(a.workers) as pool:
    reports = list(pool.map(one, seeds))
rows = [{"repo": r["repo"], "success": r["success"],
         "upgrade": ", ".join(f"{u['package']} {u['from']}→{u['to']}" for u in r["upgrades"]),
         "tests_before": r["tests_before"], "tests_after": r["tests_after"], "edits": len(r["edits"]),
         "cited": r.get("cited", 0), "fix_seconds": r.get("fix_seconds", 0), "steps": r["steps"], "seconds": r["duration_s"],
         "cost_usd": r["cost_usd"], "run_id": r.get("run_id"), "hidden_after": r.get("hidden_after"),
         "hidden_pass": (r.get("hidden_after") or "").startswith("PASS"), "new_tests": len(r.get("new_tests", []))} for r in reports]
passed = sum(r["success"] for r in rows)
hidden = [r for r in rows if r["hidden_after"]]
summary = {"hidden_passed": sum(r["hidden_pass"] for r in hidden), "hidden_total": len(hidden),
           "no_research": __import__("os").getenv("CUTOFF_NO_RESEARCH") == "1", "dir": a.dir,
           "passed": passed, "total": len(rows), "pass_rate": passed / len(rows),
           "cost_usd": round(sum(r["cost_usd"] for r in rows), 2), "wall_seconds": round(time.time() - t0),
           "model": config.ORCHESTRATOR_MODEL, "rows": rows}
out = ROOT / "runs" / f"eval-{time.strftime('%m%d-%H%M%S')}.json"
out.write_text(json.dumps(summary, indent=1))
print()
for r in rows:
    print(f"{'PASS' if r['success'] else 'FAIL'} {r['repo']:18} {r['upgrade'][:44]:44} edits {r['edits']:2} cited {r['cited']:2} "
          f"steps {r['steps']:2} fix {r['fix_seconds']:3}s total {r['seconds']:4}s ${r['cost_usd']}" + (f"  hidden {r['hidden_after'][:28]}" if r["hidden_after"] else ""))
if hidden:
    print(f"hidden intent tests: {summary['hidden_passed']}/{len(hidden)} repos")
print(f"\n{passed}/{len(rows)} fixed, ${summary['cost_usd']}, {summary['wall_seconds']}s -> {out}")
ml = config.tracing()
if ml:
    with ml.start_run(run_name=f"eval-{time.strftime('%m%d-%H%M')}"):
        ml.log_params({"model": config.ORCHESTRATOR_MODEL, "extractor": config.EXTRACTOR_MODEL, "seeds": len(rows)})
        ml.log_metrics({"pass_rate": summary["pass_rate"], "passed": passed, "cost_usd": summary["cost_usd"],
                        "avg_steps": sum(r["steps"] for r in rows) / len(rows)})
        ml.log_table({k: [r[k] for r in rows] for k in rows[0]}, "eval_results.json")
    from cutoff import scoring
    full = [r for r in reports if "events" in r]
    if full:
        print(json.dumps(scoring.evaluate(full).metrics, indent=1))
    print("logged to Databricks experiment")
