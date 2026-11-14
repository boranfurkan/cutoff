"""Deliver a finished run as a GitHub pull request in which every change cites its source."""
import re
import subprocess
from pathlib import Path


def sh(*args, cwd=None, check=True) -> str:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(f"{' '.join(args[:3])}… failed: {p.stderr.strip()[:400]}")
    return p.stdout.strip()


def parse_github(ref: str) -> str | None:
    m = re.match(r"^(?:https://github\.com/)?([\w.\-]+/[\w.\-]+?)(?:\.git)?/?$", ref)
    return m.group(1) if m and not Path(ref).exists() else None


def clone(slug: str, dest: Path) -> Path:
    sh("gh", "repo", "clone", slug, str(dest), "--", "--depth", "1", "-q")
    return dest


def pr_body(report: dict) -> str:
    ups = ", ".join(f"`{u['package']}` {u['from']} → {u['to']}" for u in report["upgrades"])
    lines = [f"Upgrades {ups} and migrates the code that the new versions break.", "",
             "| | Tests |", "|---|---|",
             f"| Before the upgrade | {report['tests_original']} |",
             f"| After the bump, before migration | {report['tests_before']} |",
             f"| After migration | **{report['tests_after']}** |", "",
             "## Changes and their sources", ""]
    for e in report["edits"]:
        r = e["rule"]
        what = f"`{r['symbol']}`" + (f" → `{r['replacement']}`" if r.get("replacement") else "")
        lines += [f"**`{e['path']}:{e['line']}`** {what} ({r['kind'].replace('_', ' ')})",
                  f"{r['note']}",
                  f"> {r['source_quote'].strip()}", f">", f"> Source: {r['source_url']}", ""]
    if report["unresolved"]:
        lines += ["## Not resolved", ""] + [f"- {u}" for u in report["unresolved"]] + [""]
    lines += ["## Summary", "", report["summary"], "", "---",
              f"Opened by [Cutoff](https://github.com/boranfurkan/cutoff): {report['steps']} agent steps, "
              f"{report['duration_s']}s, {len(report['rules_used'])} cited rules. "
              "Tests were run in an isolated container; review before merging."]
    return "\n".join(lines)


def open_pr(report: dict, run_repo: Path, clone_dir: Path, slug: str) -> str:
    """Apply the run's diff to a fresh branch of the clone, push it, and open the pull request."""
    names = "-".join(u["package"].lower() for u in report["upgrades"])[:40]
    branch = f"cutoff/upgrade-{names}-{report['run_id'][-4:]}"
    base = sh("git", "rev-list", "--max-parents=0", "HEAD", cwd=run_repo)
    diff = subprocess.run(["git", "diff", base], cwd=run_repo, capture_output=True, text=True).stdout
    patch = clone_dir.parent / "change.patch"
    patch.write_text(diff)
    sh("git", "checkout", "-q", "-b", branch, cwd=clone_dir)
    sh("git", "apply", str(patch), cwd=clone_dir)
    sh("git", "add", "-A", cwd=clone_dir)
    title = "Upgrade " + ", ".join(f"{u['package']} to {u['to']}" for u in report["upgrades"]) + " and migrate code"
    sh("git", "commit", "-qm", title, cwd=clone_dir)
    sh("git", "push", "-q", "-u", "origin", branch, cwd=clone_dir)
    body = clone_dir.parent / "pr_body.md"
    body.write_text(pr_body(report))
    return sh("gh", "pr", "create", "--repo", slug, "--head", branch, "--title", title, "--body-file", str(body), cwd=clone_dir)
