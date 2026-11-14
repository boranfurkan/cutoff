# Cutoff: project instructions

Hackathon project for Imperial AI Hack. **Submission deadline: Sunday 15 November 2026, 12:00 London time.** Solo build.

## Read first
- `docs/PLAN.md`: deadlines, prize targets, status checklist, open questions. Keep the checklist current.
- `docs/ARCHITECTURE.md`: components, the migration-rule shape, the agent's tools.
- `docs/reference/*.md`: verified API notes for Linkup, Adaption, Databricks and the Claude API. Read the relevant one before writing code against that platform; if it doesn't cover something, read `docs/vendor/<platform>/` before guessing.
- Hackathon rules and logistics: `~/Desktop/imperial-ai-hack/`.

## Rules
- All code must be written during the hackathon. Do not copy code from earlier projects.
- The repository will be public. Never commit secrets; keys live in `.env` (see `.env.example`).
- Commits: only when asked, as the user, with no AI attribution.
- Spend limits: $50 Anthropic, $20 Linkup, 1,250 Adaption credits, a Databricks daily compute quota. Say what a step will cost before running anything that spends meaningfully.
- Report results honestly. The video must state how often the agent actually works.

## Conventions
- Python 3.14 from `/opt/homebrew/bin/python3.14` in `.venv`.
- Claude calls go through the official `anthropic` SDK, non-streaming inside the agent loop.
- Every code edit the agent makes must reference a migration rule with a source URL.
