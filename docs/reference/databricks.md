# Databricks reference

Condensed from `docs/vendor/databricks/` (fetched 14 Nov 2026) and from looking at the Free Edition workspace. Where this file and the vendor docs differ, the vendor docs win.

## Design choice
The agent runs on the laptop. Databricks is the backend for two things: the migration-rule knowledge base (Delta tables) and observability (MLflow traces and evaluation). We do not host the agent inside Databricks, because Free Edition restricts outbound internet from its compute to "a limited set of trusted domains" (list not published), which could block Anthropic, Linkup and GitHub.

## Free Edition limits
- Serverless compute only, quota-limited. **Exceeding the quota shuts compute down for the rest of the day.** The number is not published.
- One SQL warehouse, 2X-Small.
- Up to 3 Databricks Apps; each stops 24 hours after start.
- One AI Search (vector search) endpoint with one search unit.
- Max 5 concurrent job tasks; one pipeline per type.
- No GPU serving, no R or Scala, no commercial use.

## Auth from the laptop
1. Workspace → Settings → Developer → Access tokens → Manage → Generate new token. Pick a lifetime and scopes ("Other APIs" lets you choose; SQL and MLflow access are needed).
2. Environment:

```bash
export DATABRICKS_HOST="https://<workspace>.cloud.databricks.com"
export DATABRICKS_TOKEN="<personal access token>"
export DATABRICKS_SERVER_HOSTNAME="<workspace>.cloud.databricks.com"   # for the SQL connector
export DATABRICKS_HTTP_PATH="/sql/1.0/warehouses/<id>"                  # SQL Warehouses → the warehouse → Connection details
```

**Verified 14 Nov 20:28:** a personal access token works on Free Edition for the REST API, the SQL connector and MLflow. Our warehouse is "Serverless Starter Warehouse" (`6e9e45b30146e869`, 2X-Small, starts in about 8 seconds). Default catalog and schema are `workspace.default`; catalogs visible: `samples`, `system`, `workspace`.

## Tracing (MLflow 3)

```bash
pip install --upgrade "mlflow[databricks]>=3.14.0" anthropic
```

```python
import mlflow
from mlflow.entities import SpanType

mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/cutoff")        # appears under Experiments → Traces
mlflow.anthropic.autolog()                     # traces Anthropic SDK calls

@mlflow.trace(span_type=SpanType.TOOL)
def run_tests(): ...

@mlflow.trace(span_type=SpanType.AGENT)
def run_agent(repo): ...
```

- Autolog captures prompts, responses, latency, model name, tool-call requests and exceptions.
- **Streaming calls are not traced**, so the agent loop uses non-streaming `messages.create`. Async is supported.
- Decorate our own tool functions with `@mlflow.trace` to get a span per tool execution.
- Optional: `mlflow.set_experiment(experiment_name=..., trace_location=UnityCatalog(catalog_name=..., schema_name=..., table_prefix=...))` stores traces as Delta tables in Unity Catalog, which makes them queryable with SQL. A good fit for the bounty if it works on Free Edition (then also set `MLFLOW_TRACING_SQL_WAREHOUSE_ID`).

## Evaluation
- `mlflow.genai.evaluate()` runs scorers over an evaluation dataset and records an evaluation run in the experiment.
- Scorers are either built-in LLM judges (Correctness, Completeness and others) or code-based: a Python function decorated with `@scorer`.
- Our main scorer is code-based and objective: did the repo's test suite pass after the agent ran?
- Traces can also be scored from the UI: Traces tab → select → Actions → Evaluate.
- The exact `evaluate` signature was not on the pages read. Before writing this code, read `docs/vendor/databricks/mlflow3__genai__eval-monitor__evaluate-app.md` and `…__concepts__scorers.md`.
- Built-in LLM judges run on Databricks-hosted models; availability and limits on Free Edition are not stated.

## Delta tables from the laptop

```bash
pip install databricks-sql-connector
```

```python
import os
from databricks import sql

with sql.connect(
    server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
    http_path=os.getenv("DATABRICKS_HTTP_PATH"),
    access_token=os.getenv("DATABRICKS_TOKEN"),
) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM samples.nyctaxi.trips LIMIT ?", [2])   # ? placeholders
        rows = cursor.fetchall()
```

Tables use three-level names (`catalog.schema.table`). The tutorial refers to `workspace.default` as the schema a trial account can create tables in; confirm the catalog name in the workspace's Catalog page.

Planned tables: `workspace.default.cutoff_rules` (one row per migration rule, with source URL and quote) and `workspace.default.cutoff_runs` (one row per agent run: repo, result, steps, tokens, cost).

## Other pieces we might use
- **AI Search**: one endpoint is allowed; a Delta Sync index over `cutoff_rules` would give semantic lookup of rules. Only worth it if time allows.
- **Databricks Apps**: could host the run-report UI (3 apps allowed, each stops after 24 hours). Outbound access from apps is not stated.
- **Genie**: natural-language questions over the rules and runs tables; a cheap demo moment.

## MCP servers (for development)
- **MLflow MCP server**: gives a coding agent live access to traces. `.mcp.json` entry runs `uv run --with "mlflow[databricks,mcp]>=3.5.1" mlflow mcp run` with `MLFLOW_TRACKING_URI=databricks`, `DATABRICKS_HOST`, `DATABRICKS_TOKEN`. Needs `uv`, which is not installed on this machine.
- **Databricks-provided MCPs** (Databricks SQL, Genie One and others) are listed in the workspace under Unity Gateway → MCPs.
- Databricks also publishes agent skills (`mlflow/skills`).
