"""Usage: python -m cutoff.cli run <repo> [--package numpy] [--store databricks]"""
import argparse
from pathlib import Path

from . import config, deliver, report_html
from .agent import Run


def main():
    ap = argparse.ArgumentParser(prog="cutoff")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="upgrade a repo's pinned dependencies and migrate its code")
    r.add_argument("repo", type=str, help="local path, GitHub URL or owner/name")
    r.add_argument("--package", action="append", help="only upgrade this package (repeatable)")
    r.add_argument("--store", choices=["local", "databricks"])
    r.add_argument("--test-cmd", help="test command to run in the sandbox (default: python -m pytest -q)")
    r.add_argument("--pr", action="store_true", help="open a pull request (repo must be a GitHub URL or owner/name)")
    a = ap.parse_args()
    slug = deliver.parse_github(str(a.repo))
    src = a.repo
    if slug:
        src = deliver.clone(slug, config.RUNS_DIR / "clones" / f"{slug.replace('/', '__')}-{__import__('uuid').uuid4().hex[:6]}" / slug.split("/")[1])
    run = Run(src, [p.lower() for p in a.package] if a.package else None, a.store, test_cmd=a.test_cmd)
    rep = run.execute()
    if a.pr and slug and rep["edits"]:
        rep["pr_url"] = deliver.open_pr(rep, run.repo, src, slug)
        print("pull request:", rep["pr_url"])
    print(f"\n{'SUCCESS' if rep['success'] else 'FAILED'}: {rep['tests_before']}  →  {rep['tests_after']}")
    print(f"{len(rep['edits'])} changes, {rep['cited']} backed by a source, {len(rep['new_tests'])} regression tests, "
          f"fix {rep['fix_seconds']}s, total {rep['duration_s']}s, ${rep['cost_usd']} {rep['cost_by_phase']}")
    print(rep["summary"])
    path = config.RUNS_DIR / rep["run_id"] / "report.json"
    path.write_text(__import__("json").dumps(rep, indent=1))
    print("report:", report_html.write(path))


if __name__ == "__main__":
    main()
