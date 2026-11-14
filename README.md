# Cutoff

**An agent that fixes code broken by stale knowledge.**

Coding agents and older repositories call APIs that have since changed, because a model's knowledge stops at its training cutoff. Cutoff takes a repository and does the whole job:

1. **Research.** Finds what changed in each dependency by searching the live web (changelogs, migration guides, release notes).
2. **Write.** Patches every call site that the changes break.
3. **Run.** Runs the project's tests in a sandbox and iterates until they pass.
4. **Deliver.** Opens a pull request in which every change cites the source that justifies it.

Dependabot and Renovate bump the version number. Cutoff migrates the code.

Built at Imperial AI Hack, 14–15 November 2026, Autonomous Agents track.

## How it is built

| Part | What it does | Built with |
|---|---|---|
| Orchestrator | Plans, patches, reads test output, decides when to stop or hand over | Claude (Anthropic API, tool use) |
| Live research | Finds and reads changelogs and migration guides, with citations | Linkup `/search` and `/fetch` |
| Rule extractor | Turns changelog prose into structured migration rules | A small model fine-tuned with Adaption AutoScientist |
| Knowledge base | Stores every breaking change found, with its source | Databricks (Delta tables) |
| Evaluation | Traces every run and scores the pass rate on seeded repos | Databricks (MLflow tracing and evaluation) |
| Sandbox | Runs the target repo's tests in isolation | Docker |

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): components, data flow, the agent's tools
- [docs/PLAN.md](docs/PLAN.md): timeline, prize targets, status, open questions
- [docs/reference/](docs/reference/): verified notes on each platform's API
- `docs/vendor/`: the vendor documentation those notes were written from; not committed, regenerate with `python3 scripts/fetch_docs.py`

## Setup

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#local-setup). Copy `.env.example` to `.env` and fill in the keys.

## APIs, models and datasets used

- Anthropic Claude API (orchestrator, dataset generation)
- Linkup API (live web search and page fetch)
- Adaption AutoScientist (fine-tuning) and an open-weight base model
- Databricks Free Edition (Delta tables, MLflow tracing and evaluation)
