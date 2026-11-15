# Cutoff

**An agent that fixes code broken by stale knowledge.**

Upgrading a dependency breaks code in two ways. Sometimes loudly: an import fails, a test goes red. Sometimes silently: a default flips, a return type changes, a parser gets stricter, and every test still passes. Cutoff handles both:

1. **Bump** the pinned versions.
2. **Fix** in a sandbox: migrate what breaks, then audit for silent behaviour changes by testing what the code's own docstrings say it should do, and write regression tests for what it finds.
3. **Verify** every change against live sources: cite the changelog line that justifies it, swap workarounds for the documented API, and flag anything no source supports.
4. **Deliver** a pull request a reviewer can check without redoing the research.

Dependabot and Renovate bump the version number. Cutoff makes the upgrade safe and shows its evidence.

Built at Imperial AI Hack, 14–15 November 2026, Autonomous Agents track.

## Results

Measured on 19 small repositories we built around real library releases (`seeds/`, `seeds_silent/`), each checked to pass on the old version and break on the new one:

| | Result |
|---|---|
| Loud breakage (11 repos): tests pass after Cutoff | 11 / 11 |
| Silent behaviour changes (8 repos): held-out intent tests pass after Cutoff | 8 / 8 |
| Changes backed by a cited source | 53 of 58 (the other 5 are flagged in the PR) |
| Median cost per repo | about $0.24 |
| Median time per repo, including verification | about 70 seconds |

### The fine-tuned extractor

The verify phase turns changelog text into structured rules. By default Claude Sonnet does that. We also fine-tuned Qwen 3.5 2B for the job with Adaption AutoScientist, on 1,138 changelog excerpts we collected and labelled during the hackathon.

| | Untuned Qwen 2B | Fine-tuned |
|---|---|---|
| Adaption win rate against the base model | n/a | 0.84 |
| Breaking changes found on 30 held-out excerpts | 28% | 47% |
| Valid output format | 93% | 100% |
| Quotes copied word for word | 90% | 100% |

Used as the extractor on the 8 silent-change repos (`CUTOFF_LOCAL_BASE=Qwen/Qwen3.5-2B CUTOFF_LOCAL_ADAPTER=models/qwen2b-v2`), it runs on a laptop and the agent still restores intent in 8 of 8, with a citation attached to all 13 changes. Reading those citations by hand, about 10 are clearly on point and 3 are loosely related, so Sonnet stays the default.

Two later runs scored higher on Adaption's own measure (Qwen 3.5 2B at 0.89, Gemma 3 4B at 1.00). The 0.89 model did worse on our held-out excerpts, reporting a breaking change in all 8 excerpts that have none, and we could not run the Gemma model locally, so the 0.84 model is the one we use.

### What research adds

We also ran the agent with web research switched off. It still fixes all 19: the sandbox loop, not the research, is what makes the fix possible. That result is why research is a verification step here and not the driver. See `docs/PLAN.md` for both ablations.

## How it is built

| Part | What it does | Built with |
|---|---|---|
| Fix phase | Migrates, audits for silent changes, writes regression tests | Claude Opus 5.5 (Anthropic API, tool use) |
| Verify phase | Finds the source for each change and attaches the citation | Claude Sonnet 5.5 + Linkup `/search` and `/fetch` |
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
