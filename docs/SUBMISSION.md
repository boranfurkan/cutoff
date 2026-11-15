# Submission pack

Numbers below come from the final sweep at 03:10 on Sun 15 Nov (`runs/eval-1115-030749.json`, `runs/eval-1115-031027.json`).

## Devpost fields

**Project name:** Cutoff

**Tagline:** Dependency upgrades you can merge: fixed, audited for silent changes, and backed by sources.

**Track:** Autonomous Agents

**Bounties (max 2 from the track):** Best use of Linkup, Databricks bounty

**Also entering:** Best Use of Adaption (model ID: fill in from the winning run), Best-Designed AI Product (Figma link: fill in, or leave out if no design is done)

**Repository:** https://github.com/boranfurkan/cutoff

**Demo pull requests:**
- Silent change caught: https://github.com/boranfurkan/cutoff-demo-orders-api/pull/1
- Loud breakage migrated: https://github.com/boranfurkan/cutoff-demo-sales-report/pull/2

### Description

**The problem.** Upgrading a dependency breaks code in two ways. Sometimes loudly: an import fails and a test goes red. Sometimes silently: a default flips, a return type changes, a parser gets stricter, and every test still passes. Tools like Dependabot bump the version number and stop there. The maintainer is left to read the changelog and hope the tests cover what changed.

**What Cutoff does.** Point it at a Python repository and it:
1. Bumps the pinned versions.
2. Fixes the code in a Docker sandbox: migrates what breaks, then audits for silent behaviour changes by testing what the code's own docstrings say it should do, and writes regression tests for what it finds.
3. Verifies every change against live sources: finds the changelog line that justifies it and cites it, and flags any change no source supports.
4. Opens a pull request a reviewer can check without redoing the research.

**How well it works.** We built 19 small repositories around real library releases, each checked to pass on the old version and break on the new one.
- Loud breakage (11 repos): 11 of 11 pass their tests after Cutoff.
- Silent behaviour changes (8 repos): tests pass before and after the bump, but held-out tests of the intended behaviour fail. Cutoff restores the intended behaviour in 8 of 8. The agent never sees those held-out tests.
- 53 of 58 code changes are backed by a cited source. The other 5 are flagged in the pull request.
- A typical run takes about 70 seconds and costs about $0.24.

**What we learned by testing our own idea.** Our first design had the agent research the web before every fix. We then switched research off and reran everything: the agent still fixed all 19. The sandbox loop, not the research, is what makes the fix possible. So we redesigned: fix first from experiment, then use research to verify and cite. The result is cheaper and faster, and the citations stayed. Both experiments are in the repository.

**What is automated and what is not.** The whole run is automated, from version bump to pull request. The test repositories are ones we wrote; they are small and their docstrings state intent clearly. Real projects are messier, and we did not find a real open-source repository that breaks cleanly in the time we had.

### How it is built

- **Fix phase:** Claude Opus 5.5 through the Anthropic API with tool use. Tools: read, search and edit files, add a dependency, add or remove a regression test, run the tests. Guardrails are in code: it cannot edit existing tests or downgrade pins.
- **Verify phase:** Claude Sonnet 5.5 with Linkup. Linkup `/search` finds the changelog or release notes, Linkup `/fetch` reads the page, and an extractor turns the relevant sections into structured migration rules, each with a verbatim quote. A rule whose quote is not found word for word in the page is discarded.
- **Sandbox:** one Docker container per run.
- **Databricks:** every verified rule goes into a Delta table that later runs reuse before searching the web; run records go into a second table; every run is traced with MLflow; and runs are scored in MLflow's evaluation view by code-based scorers (tests pass, intent preserved, edits cited, tests untouched, honest report).
- **Adaption:** we collected 6,868 real changelog excerpts from 66 libraries' GitHub releases, labelled 1,600 with Claude, and fine-tuned open-weight Qwen models with AutoScientist to do the changelog-to-rules extraction.

### Bounty: Best use of Linkup
Linkup is the evidence layer. Every citation in a Cutoff pull request comes from a Linkup search and fetch, and each quote is checked word for word against the fetched page. Without Linkup the agent can still fix code, but it cannot show why a change is correct.

### Bounty: Databricks
Cutoff runs on a laptop and uses Databricks as its memory and its measuring stick: a Delta table of cited migration rules shared across repositories, a table of run records, MLflow traces of every agent step, and MLflow evaluation runs that produce the pass rates we report.

### APIs, models and datasets
Anthropic Claude API (Opus 5.5, Sonnet 5.5), Linkup API, Databricks Free Edition (Delta tables, MLflow), Adaption AutoScientist, Qwen 3.5 base models, Docker, GitHub CLI. Dataset: release notes from public GitHub repositories, labelled by us during the hackathon.

---

## Video script (2:00 maximum; screen recording with voice-over, no intro, no music)

**0:00–0:15 · The problem.** Screen: the orders-api repo, `requirements.txt` with `fastapi==0.146.0`, and the docstring in `api/main.py`.
> "This is an order API for warehouse tablets. The docstring says: a null quantity means one unit. A maintainer wants to upgrade FastAPI. Dependabot would bump the version, the tests would pass, and they'd merge. And every tablet order with a blank quantity would start failing."

**0:15–1:30 · One real run.** Screen: terminal. Run:
`python -m cutoff.cli run boranfurkan/cutoff-demo-orders-api --pr`
> "Cutoff bumps FastAPI from 0.146 to 0.163. The tests still pass: four out of four."
> (as the `newtest` line appears) "It doesn't stop there. It reads what the code is meant to do and writes a test for it. That test fails."
> (as the `edit` lines appear) "It fixes the code and keeps the test."
> (as the `cite` line appears) "Then it checks its own work. It searches the web with Linkup, reads FastAPI's release notes, and finds the line that explains the change."
> (as the pull request URL appears) "And it opens a pull request."

Cut to the pull request in the browser. Scroll slowly.
> "The pull request shows the tests before and after, each change, and the quote and link that justify it. This run took 46 seconds and cost ten cents. Everything you saw was automated; nothing is mocked. If you speed this section up, label it."

Cut to the report page for the same run.
> "Every run also produces this report."

**1:30–1:50 · How it's built.** Screen: the Databricks experiment (traces, then the evaluation run), then the rules table.
> "The fix phase is Claude Opus in a Docker sandbox. The verify phase uses Linkup for live sources. Every verified rule is stored in Databricks and reused by later runs, and every run is traced and scored there. We also fine-tuned a small model with Adaption to read changelogs."

**1:50–2:00 · What's new, and how often it works.** Screen: the results table in the README.
> "The closest tools, Dependabot and Renovate, bump the version. Cutoff makes the upgrade safe and shows its evidence. On our 19 test repositories it fixed all 19 and caught all 8 silent changes."

### Recording notes
- Do a dry run first; the knowledge base will already hold the FastAPI rule, which makes the verify phase faster.
- The demo repo's PR #1 already exists. Either close it before recording so the run can open a fresh one, or record the run and show the existing PR.
- Keep the terminal font large. Stay under 2:00; Devpost cuts the video off there.

## Likely judge questions

- **"Isn't this just Claude?"** The model does the reasoning. What we built is what makes it trustworthy: the sandbox, guardrails in code, the audit step, held-out tests to measure it, and citations checked word for word. We also measured what research adds and designed around the answer.
- **"How do you know the silent-change result is real?"** The held-out tests are never copied into the agent's workspace. They pass on the old version, fail after the bump, and pass again after Cutoff.
- **"What doesn't work?"** Real repositories with complex setup (databases, extra requirement files). Five of 58 changes had no source. Large changelogs like pandas make verification slower and dearer.
- **"Why two models?"** Fixing needs the strongest model. Verifying is lookup and matching, so a cheaper one does it.
