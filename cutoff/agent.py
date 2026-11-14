"""The Cutoff agent.

Two phases, in the order our ablations showed works best:
  1. FIX     Bump the pins, then migrate and audit in a sandbox loop: run tests, fix what breaks, probe for silent
             behaviour changes, write regression tests. No web access; fast and cheap.
  2. VERIFY  Check every change against live sources (Linkup): cite the changelog line that justifies it, replace
             workarounds with the documented API, and flag anything no source supports.
"""
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from . import config, research
from .extractor import Extractor
from .sandbox import Sandbox
from .store import get_store

TEST_CMD = "python -m pytest -q --no-header -p no:cacheprovider"
PROTECTED = re.compile(r"(^|/)(tests?/|test_[^/]*\.py$|[^/]*_test\.py$|conftest\.py$|requirements[^/]*\.txt$)")
NO_RESEARCH = os.getenv("CUTOFF_NO_RESEARCH") == "1"  # ablation: skip the VERIFY phase

FIX_SYSTEM = """You are Cutoff, an agent that makes a Python repository safe on upgraded dependencies.

The pinned dependencies have just been bumped to their latest versions. You have a sandbox with the new versions
installed and no web access. Do two things.

1. Migrate. If the tests fail, fix the application code until they pass.

2. Audit. Passing tests do not prove an upgrade is safe: releases also change behaviour silently (a default flips, a
   return type changes, parsing gets stricter or looser, output formats shift). Read how the code uses the upgraded
   libraries and what its docstrings and comments say it is meant to do. Where behaviour might have drifted, do not
   guess: write a regression test of the intended behaviour with add_regression_test and run it. If it fails, fix
   the application code so the documented intent holds on the new version, and keep the test.

Rules:
- Every edit carries a `reason`: name the library symbol and what changed about it (for example "numpy: np.trapz was
  removed, use np.trapezoid"). The reason is checked against the library's changelog afterwards, so be specific and
  do not invent details you are unsure of; say "observed in the sandbox" when you found it by experiment.
- Prefer the library's own replacement API over re-implementing removed functionality yourself. If functionality
  moved to a separate package, use add_dependency.
- Regression tests must exercise this repository's code, not the library directly, and must pass when you finish.
  Remove any test you created that you no longer want with remove_regression_test.
- You cannot edit existing tests or requirements pins, and you cannot downgrade.
- Finish with an honest report: what you fixed, what you checked and found unaffected, and anything still broken."""

VERIFY_SYSTEM = """You are the verification phase of Cutoff. Another phase has already changed a repository so that it
works on upgraded dependencies. It had no web access, so its changes rest on memory and experiment. Your job is to
check each change against live sources and attach evidence, so a human reviewer can trust the pull request.

For each change listed by the user:
1. Find the source. Call lookup_known_rules first, then search_web for the changelog, release notes or migration
   guide of the relevant version, and read_changelog on the best URL with the affected symbols as keywords. One page
   often covers several changes. Prefer the project's own documentation or repository.
2. If a rule supports the change, call cite with the change ids and the rule_id.
3. If the source documents an official replacement and the change instead re-implements the removed functionality or
   works around it, replace the workaround with the documented API using edit_file (citing the rule), then run the
   tests. If they fail and you cannot fix it quickly, restore the previous code. Then cite the original change.
4. If you cannot find a source after a reasonable search (two or three searches), call mark_unverified with a short
   note. Never cite a rule that does not actually support the change.

Call finish when every change is cited or marked unverified."""

P = lambda **props: {"type": "object", "properties": {k: ({"type": "array", "items": {"type": "string"}} if v == "list" else {"type": v}) for k, v in props.items()}, "required": list(props)}
T = {
    "list_files": ("List the files in the repository.", P()),
    "read_file": ("Read a file from the repository.", P(path="string")),
    "grep": ("Search the repository for a regular expression. Returns matching lines with file and line number.", P(pattern="string")),
    "run_tests": ("Run the test suite in the sandbox and return the tail of its output.", P()),
    "edit_file": ("Replace one exact occurrence of old_string with new_string in a file. `reason` names the library symbol and what changed about it.", P(path="string", old_string="string", new_string="string", reason="string")),
    "add_dependency": ("Add a new package to requirements.txt and install it, when functionality moved to a separate package. Cannot change existing pins.", P(package="string", reason="string")),
    "add_regression_test": ("Create a NEW test file under tests/ (name must start with test_upgrade_) that pins down behaviour the upgrade could change.", P(filename="string", content="string", reason="string")),
    "remove_regression_test": ("Delete a regression test file that you created in this run.", P(filename="string")),
    "finish": ("End this phase with an honest report.", P(summary="string", unresolved="list")),
    "lookup_known_rules": ("Look up migration rules for a package that earlier runs already verified and stored in the knowledge base. Cheap; call before searching the web.", P(package="string", keywords="list")),
    "search_web": ("Live web search (Linkup). Find the changelog, release notes or migration guide for a package version, or what replaced a specific symbol.", P(query="string")),
    "read_changelog": ("Fetch a page and extract structured migration rules from it. Returns the rules that match your keywords, each with rule_id, symbol, replacement and the supporting quote.", P(url="string", package="string", keywords="list")),
    "cite": ("Attach a rule as the evidence for one or more changes.", P(change_ids="list", rule_id="string")),
    "mark_unverified": ("Record that no source could be found for a change.", P(change_id="string", note="string")),
    "edit_verified": ("Replace one exact occurrence of old_string with new_string, to swap a workaround for the documented API. rule_id must be a rule you retrieved.", P(path="string", old_string="string", new_string="string", rule_id="string")),
}
tools = lambda *names: [{"name": n, "description": T[n][0], "input_schema": T[n][1]} for n in names]
FIX_TOOLS = tools("list_files", "read_file", "grep", "edit_file", "add_dependency", "add_regression_test",
                  "remove_regression_test", "run_tests", "finish")
VERIFY_TOOLS = tools("lookup_known_rules", "search_web", "read_changelog", "cite", "mark_unverified", "read_file",
                     "grep", "edit_verified", "run_tests", "finish")


def latest_version(package: str) -> str:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{package}/json", timeout=20) as r:
        return json.load(r)["info"]["version"]


def tests_passed(code: int, out: str) -> bool:
    return code == 0 and " passed" in out and " failed" not in out and " error" not in out.lower().split("passed")[-1]


def summary_line(out: str) -> str:
    lines = [l for l in out.strip().splitlines() if l.strip()]
    return lines[-1].strip("= ") if lines else "no output"


class Run:
    def __init__(self, repo, packages: list[str] | None = None, store_kind: str | None = None, log=print,
                 test_cmd: str | None = None):
        self.id = datetime.now().strftime("%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        self.src = Path(repo).resolve()
        self.dir = config.RUNS_DIR / self.id
        self.repo = self.dir / "repo"
        self.packages = packages
        self.test_cmd = f"{test_cmd or TEST_CMD} 2>&1 | tail -c 6000"
        self.store = get_store(store_kind)
        self.extractor = Extractor()
        self.client = anthropic.Anthropic()
        self.rules: dict[str, dict] = {}
        self.changes: list[dict] = []      # every edit / added dependency, each later cited or marked unverified
        self.new_tests: list[dict] = []
        self.events: list[dict] = []
        self.costs = {"fix": 0.0, "verify": 0.0}
        self.steps = {"fix": 0, "verify": 0}
        self.phase = "fix"
        self.log = log
        self.t0 = time.time()
        self.done = None

    # ---------- bookkeeping
    def event(self, kind: str, title: str, **detail):
        self.events.append({"t": round(time.time() - self.t0, 1), "phase": self.phase, "kind": kind, "title": title, **detail})
        self.log(f"[{time.time() - self.t0:6.0f}s] {kind:9} {title}")

    def path(self, rel: str) -> Path:
        p = (self.repo / rel).resolve()
        if not p.is_relative_to(self.repo.resolve()):
            raise ValueError("path is outside the repository")
        return p

    def git(self, *args) -> str:
        return subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=cutoff", "-c", "user.email=cutoff@localhost",
                               *args], capture_output=True, text=True).stdout

    def run_hidden(self) -> str | None:
        """Run the held-out intent tests (never shown to the agent). Returns a summary line, or None if there are none."""
        hidden = self.src / "hidden_tests"
        if not hidden.is_dir():
            return None
        dest = self.repo / "_cutoff_hidden"
        shutil.copytree(hidden, dest, dirs_exist_ok=True)
        try:
            code, out = self.sandbox.run("python -m pytest -q --no-header -p no:cacheprovider _cutoff_hidden 2>&1 | tail -c 3000")
        finally:
            shutil.rmtree(dest, ignore_errors=True)
        return ("PASS: " if tests_passed(code, out) else "FAIL: ") + summary_line(out)

    def _change(self, **c) -> dict:
        c = {"id": f"C{len(self.changes) + 1}", "phase": self.phase, "verdict": "unverified", "rule_id": None, "note": "", **c}
        self.changes.append(c)
        return c

    def _replace(self, path, old_string, new_string):
        if PROTECTED.search(path):
            raise ValueError("tests and requirements files are read-only: fix the application code instead")
        p = self.path(path)
        text = p.read_text()
        n = text.count(old_string)
        if n != 1:
            raise ValueError(f"old_string occurs {n} times in {path}; it must occur exactly once")
        p.write_text(text.replace(old_string, new_string))
        return text[: text.index(old_string)].count("\n") + 1

    # ---------- tools: shared
    def t_list_files(self):
        self.git("add", "-A", "-N")
        return self.git("ls-files") or "(no files)"

    def t_read_file(self, path):
        return self.path(path).read_text()[:40000]

    def t_grep(self, pattern):
        return self.git("grep", "-nE", "--untracked", pattern)[:8000] or "no matches"

    def t_run_tests(self):
        code, out = self.sandbox.run(self.test_cmd)
        ok = tests_passed(code, out)
        self.event("test", ("PASS: " if ok else "FAIL: ") + summary_line(out), passed=ok, output=out[-3000:])
        return out

    def t_finish(self, summary, unresolved):
        self.done = {"summary": summary, "unresolved": unresolved}
        return "ok"

    # ---------- tools: fix phase
    def t_edit_file(self, path, old_string, new_string, reason):
        line = self._replace(path, old_string, new_string)
        c = self._change(kind="edit", path=path, line=line, old=old_string, new=new_string, reason=reason)
        self.event("edit", f"{c['id']} {path}:{line}  {reason[:110]}", change_id=c["id"])
        return f"edited ({c['id']})"

    def t_add_dependency(self, package, reason):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\-]*", package):
            raise ValueError("package must be a plain PyPI name, without version or options")
        req = self.repo / "requirements.txt"
        names = {re.split(r"[=<>!~\[; ]", l, 1)[0].lower() for l in req.read_text().splitlines() if l.strip()}
        if package.lower() in names:
            raise ValueError(f"{package} is already in requirements.txt; existing pins cannot be changed")
        version = latest_version(package)
        req.write_text(req.read_text().rstrip("\n") + f"\n{package}=={version}\n")
        code, out = self.sandbox.run(f"pip install -q --root-user-action=ignore {package}=={version} 2>&1 | tail -5", timeout=600)
        c = self._change(kind="dependency", path="requirements.txt", line=len(req.read_text().splitlines()), old="",
                         new=f"{package}=={version}", reason=reason)
        self.event("edit", f"{c['id']} requirements.txt: add {package}=={version}", change_id=c["id"])
        return f"added {package}=={version} ({c['id']})" + (f"\n{out}" if code else "")

    def t_add_regression_test(self, filename, content, reason):
        if not re.fullmatch(r"test_upgrade_[a-z0-9_]+\.py", filename):
            raise ValueError("filename must look like test_upgrade_<name>.py")
        p = self.repo / "tests" / filename
        if p.exists():
            raise ValueError("that file already exists; remove it first or choose a new name")
        p.parent.mkdir(exist_ok=True)
        p.write_text(content)
        self.new_tests.append({"path": f"tests/{filename}", "reason": reason, "content": content})
        self.event("newtest", f"tests/{filename}  {reason[:100]}")
        return "created"

    def t_remove_regression_test(self, filename):
        mine = [t for t in self.new_tests if t["path"] == f"tests/{filename}"]
        if not mine:
            raise ValueError("you can only remove regression tests created in this run")
        (self.repo / "tests" / filename).unlink(missing_ok=True)
        self.new_tests = [t for t in self.new_tests if t["path"] != f"tests/{filename}"]
        self.event("newtest", f"removed tests/{filename}")
        return "removed"

    # ---------- tools: verify phase
    @staticmethod
    def _brief(rules):
        keys = ["rule_id", "kind", "symbol", "replacement", "before", "after", "note", "source_quote", "source_url"]
        return json.dumps([{k: r.get(k) for k in keys} for r in rules], indent=1)

    @staticmethod
    def _rank(rules, keywords, cap):
        kws = [k.lower().split(".")[-1].strip("()") for k in keywords if k]
        score = lambda r: sum(k and k in f"{r['symbol']} {r.get('before')} {r.get('replacement')} {r['note']}".lower() for k in kws)
        hits = sorted((r for r in rules if score(r)), key=score, reverse=True)
        return hits[:cap]

    def t_lookup_known_rules(self, package, keywords):
        found = list({r["rule_id"]: r for r in self.store.lookup_rules(package)}.values())
        found = self._rank([r for r in found if len((r.get("source_quote") or "").split()) >= 4], keywords, 12)
        for r in found:
            self.rules[r["rule_id"]] = r
        self.event("memory", f"knowledge base: {len(found)} matching rules for {package}", package=package, count=len(found))
        return self._brief(found) if found else "No stored rules match. Search the web."

    def t_search_web(self, query):
        results = research.search(query)
        self.event("search", query, results=[{"title": r["title"], "url": r["url"]} for r in results])
        return json.dumps(results, indent=1)

    def t_read_changelog(self, url, package, keywords):
        text = research.fetch(url)
        upgrade = next((f"{u['from']} -> {u['to']}" for u in self.upgrades if u["package"].lower() == package.lower()), "previous -> latest")
        rules = self.extractor.extract(text, package, upgrade, url, keywords)
        self.store.save_rules([r for r in rules if r["rule_id"] not in self.rules])
        for r in rules:
            self.rules[r["rule_id"]] = r
        hits = self._rank(rules, keywords, 15)
        self.event("read", f"{url} → {len(rules)} rules, {len(hits)} match", url=url, chars=len(text), rule_ids=[r["rule_id"] for r in hits])
        if not hits:
            return f"Fetched {len(text)} characters and extracted {len(rules)} rules, none matching the keywords. Try other keywords or another page."
        return self._brief(hits)

    def t_cite(self, change_ids, rule_id):
        if rule_id not in self.rules:
            raise ValueError(f"unknown rule_id {rule_id}")
        known = {c["id"]: c for c in self.changes}
        bad = [i for i in change_ids if i not in known]
        if bad:
            raise ValueError(f"unknown change ids {bad}")
        for i in change_ids:
            known[i].update(rule_id=rule_id, verdict="replaced" if known[i]["verdict"] == "replaced" else "confirmed")
        self.event("cite", f"{', '.join(change_ids)} ← {rule_id} ({self.rules[rule_id]['symbol'][:50]})", change_ids=change_ids, rule_id=rule_id)
        return "cited"

    def t_mark_unverified(self, change_id, note):
        c = next((c for c in self.changes if c["id"] == change_id), None)
        if not c:
            raise ValueError(f"unknown change id {change_id}")
        c.update(verdict="unverified", rule_id=None, note=note)
        self.event("unverified", f"{change_id}: {note[:120]}", change_id=change_id)
        return "recorded"

    def t_edit_verified(self, path, old_string, new_string, rule_id):
        if rule_id not in self.rules:
            raise ValueError(f"unknown rule_id {rule_id}")
        line = self._replace(path, old_string, new_string)
        c = self._change(kind="edit", path=path, line=line, old=old_string, new=new_string, rule_id=rule_id, verdict="confirmed",
                         reason=f"Replace workaround with the documented API: {self.rules[rule_id]['symbol']}")
        self.event("edit", f"{c['id']} {path}:{line}  documented replacement ({rule_id})", change_id=c["id"])
        return f"edited ({c['id']})"

    # ---------- the loop
    def call_tool(self, name, args):
        fn = getattr(self, f"t_{name}")
        ml = config.tracing()
        if not ml:
            return fn(**args)
        with ml.start_span(name=name, span_type="TOOL") as span:
            span.set_inputs(args)
            out = fn(**args)
            span.set_outputs(str(out)[:4000])
            return out

    def loop(self, phase, system, toolset, first_message, model, max_steps, effort):
        self.phase, self.done = phase, None
        allowed = {t["name"] for t in toolset}
        messages = [{"role": "user", "content": first_message}]
        while self.steps[phase] < max_steps and not self.done:
            self.steps[phase] += 1
            resp = self.client.messages.create(model=model, max_tokens=16000, system=system, tools=toolset,
                                               output_config={"effort": effort}, cache_control={"type": "ephemeral"},
                                               messages=messages)
            self.costs[phase] += config.cost(model, resp.usage)
            messages.append({"role": "assistant", "content": resp.content})
            for b in resp.content:
                if b.type == "text" and b.text.strip():
                    self.event("think", b.text.strip()[:300])
            if resp.stop_reason in ("refusal", "max_tokens"):
                self.event("error", f"model stopped: {resp.stop_reason}")
                break
            calls = [b for b in resp.content if b.type == "tool_use"]
            if not calls:
                messages.append({"role": "user", "content": "Continue, or call finish with your report."})
                continue
            results = []
            for c in calls:
                try:
                    if c.name not in allowed:
                        raise ValueError(f"tool {c.name} is not available in this phase")
                    results.append({"type": "tool_result", "tool_use_id": c.id, "content": str(self.call_tool(c.name, c.input))})
                except Exception as e:  # noqa: BLE001  the model should see tool errors and adapt
                    self.event("error", f"{c.name}: {e}"[:200])
                    results.append({"type": "tool_result", "tool_use_id": c.id, "content": f"Error: {e}", "is_error": True})
            messages.append({"role": "user", "content": results})
        return self.done or {"summary": f"Stopped after {self.steps[phase]} steps without finishing.", "unresolved": ["step budget exhausted"]}

    # ---------- phases
    def prepare(self):
        shutil.copytree(self.src, self.repo, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "*.pyc", "hidden_tests"))
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-qm", "baseline")
        req = self.repo / "requirements.txt"
        lines = req.read_text().splitlines()
        self.upgrades = []
        self.sandbox.run("pip install -q --root-user-action=ignore -r requirements.txt 2>&1 | tail -5", timeout=600)
        code, out = self.sandbox.run(self.test_cmd)
        self.tests_original = summary_line(out)
        self.hidden_original = self.run_hidden()
        self.event("scan", f"tests on pinned versions: {self.tests_original}", passed=tests_passed(code, out))
        for i, line in enumerate(lines):
            m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;#]+)", line)
            if not m or (self.packages and m.group(1).lower() not in self.packages):
                continue
            new = latest_version(m.group(1))
            if new != m.group(2):
                self.upgrades.append({"package": m.group(1), "from": m.group(2), "to": new})
                lines[i] = f"{m.group(1)}=={new}"
        req.write_text("\n".join(lines) + "\n")
        self.git("commit", "-qam", "bump dependencies")
        for u in self.upgrades:
            self.event("bump", f"{u['package']} {u['from']} → {u['to']}", **u)
        code, out = self.sandbox.run("pip install -q --root-user-action=ignore -r requirements.txt 2>&1 | tail -15", timeout=600)
        if code != 0 or "ERROR" in out:
            self.event("error", "dependency install failed", output=out)
        code, out = self.sandbox.run(self.test_cmd)
        self.tests_before = summary_line(out)
        self.hidden_before = self.run_hidden()
        self.baseline_ok = tests_passed(code, out)
        self.event("test", ("PASS: " if self.baseline_ok else "FAIL: ") + self.tests_before + " (after the bump)",
                   passed=self.baseline_ok, output=out[-3000:])
        return out

    def fix(self, test_output):
        ups = "\n".join(f"- {u['package']}: {u['from']} -> {u['to']}" for u in self.upgrades)
        state = ("The tests still pass. Audit the upgrade for silent behaviour changes." if self.baseline_ok
                 else "Migrate the code, then audit for silent behaviour changes.")
        return self.loop("fix", FIX_SYSTEM, FIX_TOOLS,
                         f"Dependencies upgraded in requirements.txt:\n{ups}\n\nFiles:\n{self.git('ls-files')}\n"
                         f"Test output after the upgrade:\n```\n{test_output}\n```\n{state}",
                         config.ORCHESTRATOR_MODEL, config.MAX_STEPS, config.EFFORT)

    def verify(self):
        ups = "\n".join(f"- {u['package']}: {u['from']} -> {u['to']}" for u in self.upgrades)
        listing = "\n\n".join(
            f"{c['id']} [{c['kind']}] {c['path']}:{c['line']}\nreason given: {c['reason']}\n- {c['old']}\n+ {c['new']}"
            for c in self.changes)
        return self.loop("verify", VERIFY_SYSTEM, VERIFY_TOOLS,
                         f"Upgrades:\n{ups}\n\nChanges to verify:\n\n{listing}",
                         config.VERIFY_MODEL, config.MAX_VERIFY_STEPS, "medium")

    def execute(self) -> dict:
        ml = config.tracing()
        if not ml:
            return self._execute()
        with ml.start_span(name=f"cutoff:{self.src.name}", span_type="AGENT") as span:
            span.set_inputs({"repo": self.src.name, "packages": self.packages})
            report = self._execute()
            span.set_outputs({k: report[k] for k in ("success", "tests_before", "tests_after", "summary", "cost_usd", "cited")})
            ml.update_current_trace(tags={"repo": self.src.name, "success": str(report["success"]), "run_id": self.id})
            return report

    def _execute(self) -> dict:
        self.dir.mkdir(parents=True)
        started = datetime.now(timezone.utc).isoformat()
        verify_report = None
        with Sandbox(self.dir / "repo") as sb:
            self.sandbox = sb
            test_output = self.prepare()
            if not self.upgrades:
                fix_report = {"summary": "Every pinned dependency is already at its latest version.", "unresolved": []}
            else:
                fix_report = self.fix(test_output)
            code, out = sb.run(self.test_cmd)
            fixed_ok, self.tests_fixed = tests_passed(code, out), summary_line(out)
            self.fix_seconds = round(time.time() - self.t0)
            self.event("verdict", ("PASS: " if fixed_ok else "FAIL: ") + self.tests_fixed + " (after the fix phase)", passed=fixed_ok)
            self.git("add", "-A")
            self.git("commit", "-qm", "fix phase")
            if self.changes and not NO_RESEARCH:
                verify_report = self.verify()
                code, out = sb.run(self.test_cmd)
                if fixed_ok and not tests_passed(code, out):  # verification must never make things worse
                    self.event("error", "verification edits broke the tests; reverting them")
                    self.git("reset", "-q", "--hard", "HEAD")
                    self.git("clean", "-qfd")
                    for c in self.changes:
                        if c["phase"] == "verify":
                            c.update(verdict="reverted", note="reverted: tests failed after this replacement")
                    code, out = sb.run(self.test_cmd)
            success, self.tests_after = tests_passed(code, out), summary_line(out)
            self.hidden_after = self.run_hidden()
            self.event("verdict", ("PASS: " if success else "FAIL: ") + self.tests_after, passed=success, output=out[-3000:])
        self.costs["verify"] += self.extractor.cost
        live = [c for c in self.changes if c["verdict"] != "reverted"]
        for c in live:
            c["rule"] = self.rules.get(c["rule_id"]) if c["rule_id"] else None
        cited = sum(1 for c in live if c["rule"])
        report = {
            "run_id": self.id, "repo": self.src.name, "started_at": started, "success": success,
            "duration_s": round(time.time() - self.t0), "fix_seconds": self.fix_seconds,
            "steps": sum(self.steps.values()), "steps_by_phase": self.steps,
            "model": config.ORCHESTRATOR_MODEL, "verify_model": None if NO_RESEARCH else config.VERIFY_MODEL,
            "extractor": self.extractor.name, "store": self.store.name,
            "cost_usd": round(sum(self.costs.values()), 3), "cost_by_phase": {k: round(v, 3) for k, v in self.costs.items()},
            "upgrades": self.upgrades, "tests_original": self.tests_original, "tests_before": self.tests_before,
            "tests_fixed": self.tests_fixed, "tests_after": self.tests_after,
            "hidden_original": self.hidden_original, "hidden_before": self.hidden_before, "hidden_after": self.hidden_after,
            "summary": fix_report["summary"], "unresolved": fix_report["unresolved"],
            "verification_summary": verify_report["summary"] if verify_report else None,
            "edits": live, "cited": cited, "unverified": len(live) - cited,
            "replaced_workarounds": sum(1 for c in live if c["phase"] == "verify"),
            "new_tests": self.new_tests, "rules_found": len(self.rules),
            "rules_used": [self.rules[r] for r in sorted({c["rule_id"] for c in live if c["rule_id"]})],
            "diff": self.git("diff", "HEAD~1") if self.changes or self.new_tests else "", "events": self.events,
        }
        (self.dir / "report.json").write_text(json.dumps(report, indent=1))
        self.store.save_run({**{k: report.get(k) for k in ("run_id", "repo", "started_at", "success", "steps",
                             "rules_found", "tests_before", "tests_after", "cost_usd", "model")},
                             "edits": len(live), "report": fix_report["summary"]})
        return report
