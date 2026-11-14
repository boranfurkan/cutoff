"""The Cutoff agent: bump dependencies, research what changed, patch the code, prove it with tests."""
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

SYSTEM = """You are Cutoff, an agent that migrates a Python repository after its dependencies were upgraded.

The dependencies have already been bumped to their latest versions and the test suite now fails. Your knowledge of
these libraries may be out of date, so do not patch from memory. Work like this:

1. Read the failing test output and the code involved.
2. Research what changed: call lookup_known_rules for the package first, then search_web for the changelog,
   release notes or migration guide of the new version, and read_changelog on the best URL. Pass the symbols from
   the errors as keywords. read_changelog returns structured migration rules, each with a rule_id and a source.
3. Apply the rules with edit_file. Every edit must name the rule_id that justifies it. If no rule covers an edit you
   need, research further (a more specific search, another page) until one does.
4. Run the tests. Repeat until they pass.
5. Call finish with a short summary. If you cannot get the tests passing, call finish anyway and say exactly what
   is still broken and why; never claim success the tests do not show.

Constraints enforced by the tools: you cannot edit tests or requirements files, and you cannot downgrade
dependencies. If a rule says functionality moved into a separate package, use add_dependency. Fix the application code so it works with the new versions. Make the smallest change that each rule
requires; also fix other usages of the same removed or renamed API that the tests may not cover."""

TOOLS = [
    {"name": "lookup_known_rules", "description": "Look up migration rules for a package that earlier runs already found and stored in the knowledge base. Cheap; call before searching the web.",
     "input_schema": {"type": "object", "properties": {"package": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}, "description": "Symbols from the errors, e.g. applymap, fillna; only matching rules are returned."}}, "required": ["package", "keywords"]}},
    {"name": "search_web", "description": "Live web search (Linkup). Use it to find the changelog, release notes or migration guide for a package version, or what replaced a specific removed symbol. Returns titles, URLs and snippets.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "read_changelog", "description": "Fetch a page (changelog, release notes, migration guide) and extract structured migration rules from it. Returns rules with rule_id, kind, symbol, replacement, example and the supporting quote. Give keywords (symbols from the errors) so the relevant sections are prioritised.",
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "package": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}}}, "required": ["url", "package", "keywords"]}},
    {"name": "list_files", "description": "List the files in the repository.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "read_file", "description": "Read a file from the repository.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "grep", "description": "Search the repository for a regular expression. Returns matching lines with file and line number.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "edit_file", "description": "Replace one exact occurrence of old_string with new_string in a file. rule_id must be a rule returned by read_changelog or lookup_known_rules; it becomes the citation for this change.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}, "rule_id": {"type": "string"}}, "required": ["path", "old_string", "new_string", "rule_id"]}},
    {"name": "add_dependency", "description": "Add a new package to requirements.txt and install it, when a migration rule says functionality moved to a separate package. rule_id must justify it. Cannot change or downgrade existing pins.",
     "input_schema": {"type": "object", "properties": {"package": {"type": "string"}, "rule_id": {"type": "string"}}, "required": ["package", "rule_id"]}},
    {"name": "run_tests", "description": "Run the test suite in the sandbox and return the tail of its output.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "finish", "description": "End the run with an honest report.",
     "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}, "unresolved": {"type": "array", "items": {"type": "string"}}}, "required": ["summary", "unresolved"]}},
]


# Ablation: the same agent with no research tools, patching from the model's built-in knowledge only.
NO_RESEARCH = os.getenv("CUTOFF_NO_RESEARCH") == "1"
if NO_RESEARCH:
    TOOLS = [t for t in TOOLS if t["name"] not in ("lookup_known_rules", "search_web", "read_changelog", "add_dependency")]
    for t in TOOLS:
        if t["name"] == "edit_file":
            t["description"] = "Replace one exact occurrence of old_string with new_string in a file."
            t["input_schema"] = {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["path", "old_string", "new_string"]}
    SYSTEM = """You migrate a Python repository after its dependencies were upgraded. The dependencies have already been
bumped to their latest versions and the test suite now fails. You have no web access: use your own knowledge of the
libraries, the error messages and the code. Edit the application code with edit_file, run the tests, and repeat until
they pass. You cannot edit tests or requirements files or downgrade dependencies. Call finish with an honest summary;
if you cannot get the tests passing, say exactly what is still broken."""


def latest_version(package: str) -> str:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{package}/json", timeout=20) as r:
        return json.load(r)["info"]["version"]


def tests_passed(code: int, out: str) -> bool:
    return code == 0 and " passed" in out and " failed" not in out and " error" not in out.lower().split("passed")[-1]


def summary_line(out: str) -> str:
    lines = [l for l in out.strip().splitlines() if l.strip()]
    return lines[-1].strip("= ") if lines else "no output"


class Run:
    def __init__(self, repo: Path, packages: list[str] | None, store_kind: str | None = None, log=print, test_cmd: str | None = None):
        self.test_cmd = f"{test_cmd or TEST_CMD} 2>&1 | tail -c 6000"
        self.id = datetime.now().strftime("%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        self.src = Path(repo).resolve()
        self.dir = config.RUNS_DIR / self.id
        self.repo = self.dir / "repo"
        self.packages = packages
        self.store = get_store(store_kind)
        self.extractor = Extractor()
        self.client = anthropic.Anthropic()
        self.rules: dict[str, dict] = {}
        self.edits: list[dict] = []
        self.events: list[dict] = []
        self.cost = 0.0
        self.steps = 0
        self.log = log
        self.t0 = time.time()
        self.finish = None

    # ---------- bookkeeping
    def event(self, kind: str, title: str, **detail):
        self.events.append({"t": round(time.time() - self.t0, 1), "kind": kind, "title": title, **detail})
        self.log(f"[{time.time() - self.t0:6.0f}s] {kind:9} {title}")

    def path(self, rel: str) -> Path:
        p = (self.repo / rel).resolve()
        if not p.is_relative_to(self.repo.resolve()):
            raise ValueError("path is outside the repository")
        return p

    def git(self, *args) -> str:
        return subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=cutoff", "-c", "user.email=cutoff@localhost",
                               *args], capture_output=True, text=True).stdout

    # ---------- tools
    def t_lookup_known_rules(self, package, keywords=()):
        found = list({r["rule_id"]: r for r in self.store.lookup_rules(package)}.values())
        found = [r for r in found if len((r.get("source_quote") or "").split()) >= 4]
        kws = [k.lower().split(".")[-1] for k in keywords if k]
        if kws:  # most relevant first: rules whose symbol or text mentions a keyword
            score = lambda r: sum(k in f"{r['symbol']} {r.get('before')} {r['note']}".lower() for k in kws)
            found = sorted((r for r in found if score(r)), key=score, reverse=True)
        for r in found:
            self.rules[r["rule_id"]] = r
        self.event("memory", f"knowledge base: {len(found)} stored rules for {package}", package=package, count=len(found))
        return self._brief(found) if found else "No stored rules match. Search the web."

    def t_search_web(self, query):
        results = research.search(query)
        self.event("search", query, results=[{"title": r["title"], "url": r["url"]} for r in results])
        return json.dumps(results, indent=1)

    def t_read_changelog(self, url, package, keywords):
        text = research.fetch(url)
        upgrade = next((f"{u['from']} -> {u['to']}" for u in self.upgrades if u["package"] == package), "previous -> latest")
        rules = self.extractor.extract(text, package, upgrade, url, keywords)
        new = [r for r in rules if r["rule_id"] not in self.rules]
        for r in rules:
            self.rules[r["rule_id"]] = r
        self.store.save_rules(new)
        self.event("read", f"{url} → {len(rules)} rules", url=url, chars=len(text), rule_ids=[r["rule_id"] for r in rules])
        if not rules:
            return f"Fetched {len(text)} characters but found no migration rules matching. Try other keywords or another page."
        return self._brief(rules)

    @staticmethod
    def _brief(rules):
        keys = ["rule_id", "kind", "symbol", "replacement", "before", "after", "note", "source_quote"]
        return json.dumps([{k: r.get(k) for k in keys} for r in rules[:60]], indent=1)

    def t_list_files(self):
        return self.git("ls-files") or "(no files)"

    def t_read_file(self, path):
        return self.path(path).read_text()[:40000]

    def t_grep(self, pattern):
        out = self.git("grep", "-nE", pattern)
        return out[:8000] or "no matches"

    def t_edit_file(self, path, old_string, new_string, rule_id=None):
        if PROTECTED.search(path):
            raise ValueError("tests and requirements files are read-only: fix the application code instead")
        if NO_RESEARCH:
            rule_id = "NONE"
            self.rules.setdefault("NONE", {"rule_id": "NONE", "symbol": "(no source)", "kind": "uncited", "replacement": None,
                                           "note": "edited from model memory", "source_url": "", "source_quote": ""})
        if rule_id not in self.rules:
            raise ValueError(f"unknown rule_id {rule_id}: every edit must cite a rule from read_changelog or lookup_known_rules")
        p = self.path(path)
        text = p.read_text()
        n = text.count(old_string)
        if n != 1:
            raise ValueError(f"old_string occurs {n} times in {path}; it must occur exactly once")
        p.write_text(text.replace(old_string, new_string))
        line = text[: text.index(old_string)].count("\n") + 1
        self.edits.append({"path": path, "line": line, "old": old_string, "new": new_string, "rule_id": rule_id})
        self.event("edit", f"{path}:{line} ({rule_id}: {self.rules[rule_id]['symbol']})", path=path, line=line,
                   old=old_string, new=new_string, rule_id=rule_id)
        return "edited"

    def t_add_dependency(self, package, rule_id):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\-]*", package):
            raise ValueError("package must be a plain PyPI name, without version or options")
        if rule_id not in self.rules:
            raise ValueError(f"unknown rule_id {rule_id}")
        req = self.repo / "requirements.txt"
        names = {re.split(r"[=<>!~\[; ]", l, 1)[0].lower() for l in req.read_text().splitlines() if l.strip()}
        if package.lower() in names:
            raise ValueError(f"{package} is already in requirements.txt; existing pins cannot be changed")
        version = latest_version(package)
        req.write_text(req.read_text().rstrip("\n") + f"\n{package}=={version}\n")
        code, out = self.sandbox.run(f"pip install -q --root-user-action=ignore {package}=={version} 2>&1 | tail -5", timeout=600)
        self.edits.append({"path": "requirements.txt", "line": len(req.read_text().splitlines()), "old": "",
                           "new": f"{package}=={version}", "rule_id": rule_id})
        self.event("edit", f"requirements.txt: add {package}=={version} ({rule_id})", path="requirements.txt",
                   old="", new=f"{package}=={version}", rule_id=rule_id)
        return f"added {package}=={version}" + (f"\n{out}" if code else "")

    def t_run_tests(self):
        code, out = self.sandbox.run(self.test_cmd)
        ok = tests_passed(code, out)
        self.event("test", ("PASS: " if ok else "FAIL: ") + summary_line(out), passed=ok, output=out[-3000:])
        return out

    def t_finish(self, summary, unresolved):
        self.finish = {"summary": summary, "unresolved": unresolved}
        return "ok"

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

    # ---------- phases
    def prepare(self):
        shutil.copytree(self.src, self.repo, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "*.pyc"))
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-qm", "baseline")
        req = self.repo / "requirements.txt"
        lines = req.read_text().splitlines()
        self.upgrades = []
        code, out = self.sandbox.run("pip install -q --root-user-action=ignore -r requirements.txt 2>&1 | tail -5", timeout=600)
        code, out = self.sandbox.run(self.test_cmd)
        self.tests_original = summary_line(out)
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
        self.baseline_ok = tests_passed(code, out)
        self.event("test", ("PASS: " if self.baseline_ok else "FAIL: ") + self.tests_before + " (after the bump)",
                   passed=self.baseline_ok, output=out[-3000:])
        return out

    def loop(self, failing_output: str):
        ups = "\n".join(f"- {u['package']}: {u['from']} -> {u['to']}" for u in self.upgrades)
        messages = [{"role": "user", "content":
                     f"Dependencies upgraded in requirements.txt:\n{ups}\n\nFiles:\n{self.git('ls-files')}\n"
                     f"Test output after the upgrade:\n```\n{failing_output}\n```\nMigrate the code."}]
        while self.steps < config.MAX_STEPS and not self.finish:
            self.steps += 1
            resp = self.client.messages.create(
                model=config.ORCHESTRATOR_MODEL, max_tokens=16000, system=SYSTEM, tools=TOOLS,
                output_config={"effort": config.EFFORT}, cache_control={"type": "ephemeral"}, messages=messages)
            self.cost += config.cost(config.ORCHESTRATOR_MODEL, resp.usage)
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
                    out = self.call_tool(c.name, c.input)
                    results.append({"type": "tool_result", "tool_use_id": c.id, "content": str(out)})
                except Exception as e:  # noqa: BLE001  the model should see tool errors and adapt
                    self.event("error", f"{c.name}: {e}"[:200])
                    results.append({"type": "tool_result", "tool_use_id": c.id, "content": f"Error: {e}", "is_error": True})
            messages.append({"role": "user", "content": results})
        if not self.finish:
            self.finish = {"summary": f"Stopped after {self.steps} steps without finishing.", "unresolved": ["step budget exhausted"]}

    def execute(self) -> dict:
        ml = config.tracing()
        if not ml:
            return self._execute()
        with ml.start_span(name=f"cutoff:{self.src.name}", span_type="AGENT") as span:
            span.set_inputs({"repo": self.src.name, "packages": self.packages})
            report = self._execute()
            span.set_outputs({k: report[k] for k in ("success", "tests_before", "tests_after", "summary", "cost_usd")})
            ml.update_current_trace(tags={"repo": self.src.name, "success": str(report["success"]), "run_id": self.id})
            return report

    def _execute(self) -> dict:
        self.dir.mkdir(parents=True)
        started = datetime.now(timezone.utc).isoformat()
        with Sandbox(self.dir / "repo") as sb:
            self.sandbox = sb
            failing = self.prepare()
            if self.baseline_ok:
                self.finish = {"summary": "Tests pass on the upgraded dependencies; nothing to migrate.", "unresolved": []}
            else:
                self.loop(failing)
            code, out = sb.run(self.test_cmd)
            success = tests_passed(code, out)
            self.tests_after = summary_line(out)
            self.event("verdict", ("PASS: " if success else "FAIL: ") + self.tests_after, passed=success, output=out[-3000:])
        self.cost += self.extractor.cost
        used = {e["rule_id"] for e in self.edits}
        report = {
            "run_id": self.id, "repo": self.src.name, "started_at": started, "success": success,
            "duration_s": round(time.time() - self.t0), "steps": self.steps, "model": config.ORCHESTRATOR_MODEL,
            "extractor": self.extractor.name, "store": self.store.name, "cost_usd": round(self.cost, 3),
            "upgrades": self.upgrades, "tests_original": self.tests_original, "tests_before": self.tests_before,
            "tests_after": self.tests_after, "summary": self.finish["summary"], "unresolved": self.finish["unresolved"],
            "edits": [{**e, "rule": self.rules[e["rule_id"]]} for e in self.edits],
            "rules_found": len(self.rules), "rules_used": [self.rules[r] for r in sorted(used)],
            "diff": self.git("diff", "HEAD"), "events": self.events,
        }
        (self.dir / "report.json").write_text(json.dumps(report, indent=1))
        self.store.save_run({**{k: report.get(k) for k in ("run_id", "repo", "started_at", "success", "steps",
                             "rules_found", "tests_before", "tests_after", "cost_usd", "model")},
                             "edits": len(self.edits), "report": self.finish["summary"]})
        return report
