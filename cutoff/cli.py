"""Usage: python -m cutoff.cli run <repo> [--package numpy] [--store databricks]"""
import argparse
from pathlib import Path

from .agent import Run


def main():
    ap = argparse.ArgumentParser(prog="cutoff")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="upgrade a repo's pinned dependencies and migrate its code")
    r.add_argument("repo", type=Path)
    r.add_argument("--package", action="append", help="only upgrade this package (repeatable)")
    r.add_argument("--store", choices=["local", "databricks"])
    a = ap.parse_args()
    run = Run(a.repo, [p.lower() for p in a.package] if a.package else None, a.store)
    rep = run.execute()
    print(f"\n{'SUCCESS' if rep['success'] else 'FAILED'}: {rep['tests_before']}  →  {rep['tests_after']}")
    print(f"{len(rep['edits'])} edits citing {len(rep['rules_used'])} rules, {rep['steps']} steps, "
          f"{rep['duration_s']}s, ${rep['cost_usd']}")
    print(rep["summary"])
    print(f"report: runs/{rep['run_id']}/report.json")


if __name__ == "__main__":
    main()
