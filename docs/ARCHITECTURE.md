# Architecture

Status: design, written Sat 14 Nov 2026 before any agent code exists. Update this file when the design changes.

## One run, end to end

```
repo URL or path
      │
      ▼
1. SCAN        read manifests (pyproject/requirements), installed vs latest versions,
               run the test suite once to capture the failing baseline
      │
      ▼
2. RESEARCH    for each dependency that moved: Linkup /search to find the changelog or
               migration guide, Linkup /fetch to read it → raw changelog text + URL
      │
      ▼
3. EXTRACT     rule extractor turns changelog text into structured migration rules
               (fine-tuned small model; Claude as fallback) → rules saved to the knowledge base
      │
      ▼
4. PATCH       Claude applies the rules to the call sites it finds, one change at a time,
               recording which rule and source justified each edit
      │
      ▼
5. VERIFY      run tests in the Docker sandbox; on failure, feed output back and iterate
               (step budget; when the budget runs out, stop and report honestly)
      │
      ▼
6. DELIVER     branch + commit + pull request whose body lists each change with its citation,
               plus a run report (what was automated, what was left, test results)
```

Every step is traced to Databricks, so a run can be inspected afterwards and scored.

## Components

### Orchestrator (`cutoff/agent/`)
- Anthropic Python SDK, Claude with tool use. Start with the SDK tool runner (`client.beta.messages.tool_runner` + `@beta_tool`); see [reference/claude-api.md](reference/claude-api.md).
- Non-streaming calls inside the loop, because MLflow's Anthropic autolog does not trace streaming.
- A hard step budget and a token budget per run. When either is exhausted the agent stops and writes a report instead of looping.
- Guardrails live in code, not only in the prompt: the file tools refuse paths outside the repo checkout, and shell commands run only inside the sandbox container.

### Tools the model can call

| Tool | Purpose | Backed by |
|---|---|---|
| `search_changes(package, from_version, to_version)` | Find changelog / migration guide URLs | Linkup `/search` |
| `read_page(url)` | Get a page as markdown | Linkup `/fetch` |
| `extract_rules(changelog_text, package)` | Structured migration rules | fine-tuned model, Claude fallback |
| `lookup_rules(package, version_range)` | Reuse rules found on earlier runs | Databricks SQL |
| `list_files`, `read_file`, `grep` | Explore the checkout | local filesystem (path-confined) |
| `edit_file(path, old, new, rule_id)` | Apply one change, tied to a rule | local filesystem (path-confined) |
| `run_tests()` | Run the suite, return trimmed output | Docker |
| `finish(report)` | End the run with a structured report | n/a |

`edit_file` requires a `rule_id`, which is what makes "every change cites its source" true by construction and not by prompt.

### Migration rule (the shared data shape)

```json
{
  "package": "examplelib",
  "from_version": "1.x",
  "to_version": "2.0",
  "kind": "renamed | removed | signature_changed | behavior_changed | moved",
  "symbol": "examplelib.old_name",
  "replacement": "examplelib.new_name",
  "before": "old_name(x, flag=True)",
  "after": "new_name(x, mode='strict')",
  "note": "one sentence on what changed and why it breaks",
  "source_url": "https://…/CHANGELOG.md",
  "source_quote": "short verbatim quote that supports the rule"
}
```

This shape is the output of the extractor, the row format of the knowledge base, the training target for the fine-tune, and the citation in the pull request.

### Storage interface (`cutoff/store/`)
One small interface (`save_rules`, `lookup_rules`, `save_run`) with two implementations:
- `DatabricksStore`: Delta tables through `databricks-sql-connector`. The real one.
- `LocalStore`: JSON files on disk. Used for development and as the fallback if Databricks quota runs out.

### Evaluation (`cutoff/eval/`)
- A set of about 10 seeded repositories, each small, with a pinned old dependency and a test suite that fails on the new version.
- One command runs the agent on all of them and records pass/fail per repo.
- Scores are logged to Databricks with MLflow so the result is visible in the workspace. The headline number for the video is "fixed N of 10".

### Sandbox
Docker container per run: repo checkout mounted, network allowed only for package installs, a time limit on every command.

### UI (`web/`)
A single run-report page: timeline of steps, each code change next to the quote and link that justified it, test results before and after. Designed in Figma first (for the Figma prize), then built.

## Models

| Role | Model | Why |
|---|---|---|
| Orchestrator | `claude-opus-5-5` | Planning, patching and debugging need the strongest model |
| Bulk dataset generation | to be confirmed with the user (a cheaper Claude model would cut cost) | Thousands of short generations |
| Rule extractor | fine-tuned open-weight model from Adaption | The Adaption prize entry; runs locally |

Budget: $50 of Anthropic credits in total. Track spend per run from `response.usage`.

## Local setup

- Python: `/opt/homebrew/bin/python3.14` in a virtualenv (`python3.14 -m venv .venv`). The system Python is 3.9, which is too old for the Anthropic MCP helpers and current MLflow.
- Docker Desktop must be running for the sandbox.
- `gh` is installed and logged in, for creating the public repo and pull requests.
- Keys go in `.env` (see `.env.example`); never commit them.

## Repository layout (planned)

```
cutoff/            Python package: agent/, tools/, store/, eval/, extractor/
web/               run-report UI
data/              fine-tuning dataset and seeded repos manifest
scripts/           fetch_docs.py, dataset generation, Adaption launch
docs/              this folder
```
