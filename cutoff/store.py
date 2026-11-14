"""Knowledge base of migration rules and run records. Local JSON files or Databricks Delta tables."""
import json
import os
from pathlib import Path

from .config import ROOT

RULE_COLS = ["rule_id", "package", "from_version", "to_version", "kind", "symbol", "replacement",
             "before", "after", "note", "source_url", "source_quote", "extractor"]
RUN_COLS = ["run_id", "repo", "started_at", "success", "steps", "edits", "rules_found",
            "tests_before", "tests_after", "cost_usd", "model", "report"]


class LocalStore:
    name = "local"

    def __init__(self, path: Path = ROOT / "runs" / "store"):
        self.path = path
        path.mkdir(parents=True, exist_ok=True)

    def _append(self, file, rows):
        with (self.path / file).open("a") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def save_rules(self, rules):
        self._append("rules.jsonl", rules)

    def save_run(self, run):
        self._append("runs.jsonl", [run])

    def lookup_rules(self, package):
        p = self.path / "rules.jsonl"
        if not p.exists():
            return []
        return [r for r in map(json.loads, p.open()) if r["package"] == package]


class DatabricksStore:
    name = "databricks"
    RULES = "workspace.default.cutoff_rules"
    RUNS = "workspace.default.cutoff_runs"

    def __init__(self):
        from databricks import sql
        self._sql = sql
        with self._conn() as c, c.cursor() as cur:
            cur.execute(f"CREATE TABLE IF NOT EXISTS {self.RULES} ({', '.join(c + ' STRING' for c in RULE_COLS)}, created_at TIMESTAMP)")
            cur.execute(f"""CREATE TABLE IF NOT EXISTS {self.RUNS} (run_id STRING, repo STRING, started_at STRING,
                success BOOLEAN, steps INT, edits INT, rules_found INT, tests_before STRING, tests_after STRING,
                cost_usd DOUBLE, model STRING, report STRING, created_at TIMESTAMP)""")

    def _conn(self):
        return self._sql.connect(server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
                                 http_path=os.environ["DATABRICKS_HTTP_PATH"],
                                 access_token=os.environ["DATABRICKS_TOKEN"])

    def save_rules(self, rules):
        if not rules:
            return
        row = "(" + ", ".join("?" for _ in RULE_COLS) + ", current_timestamp())"
        with self._conn() as c, c.cursor() as cur:  # one multi-row statement: row-by-row inserts take ~1s each
            for i in range(0, len(rules), 15):
                batch = rules[i:i + 15]
                cur.execute(f"INSERT INTO {self.RULES} VALUES " + ", ".join(row for _ in batch),
                            [r.get(k) for r in batch for k in RULE_COLS])

    def save_run(self, run):
        ph = ", ".join("?" for _ in RUN_COLS)
        with self._conn() as c, c.cursor() as cur:
            cur.execute(f"INSERT INTO {self.RUNS} VALUES ({ph}, current_timestamp())", [run.get(k) for k in RUN_COLS])

    def lookup_rules(self, package):
        with self._conn() as c, c.cursor() as cur:
            cur.execute(f"SELECT {', '.join(RULE_COLS)} FROM {self.RULES} WHERE package = ?", [package])
            return [dict(zip(RULE_COLS, row)) for row in cur.fetchall()]


def get_store(kind: str | None = None):
    kind = kind or os.getenv("CUTOFF_STORE", "local")
    return DatabricksStore() if kind == "databricks" else LocalStore()
