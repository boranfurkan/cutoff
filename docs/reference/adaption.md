# Adaption reference

Condensed from `docs/vendor/adaption/` (fetched 14 Nov 2026) and from looking at the app. Where this file and the vendor docs differ, the vendor docs win.

## What it is
- **Adaptive Data**: improves or generates training datasets.
- **AutoScientist**: picks a base model and training recipe, trains for up to 5 iterations, evaluates each one against the base model, keeps the best checkpoint.
- **Inference Stacks / Responses API**: hosted inference for a fixed list of hosted models, plus saved "stacks" (model + tools + datasets + memory) created in the app.

## Setup
- `pip install "adaption>=0.7.0"` (0.16.0+ for the Responses API).
- API key: app → Settings → API keys. Shown once. `export ADAPTION_API_KEY=pt_live_...`; `Adaption()` reads it.
- Async: `AsyncAdaption`.

## Fine-tune from our own prompt/completion file

```python
from adaption import Adaption
client = Adaption()

dataset = client.datasets.upload_file(
    "data/rules.jsonl",                 # CSV, JSON, JSONL or Parquet
    processing_mode="raw",              # train on our rows as-is, skip Adaptive Data
    column_mapping={"prompt": "prompt", "completion": "completion"},  # our file's headers
)
client.datasets.wait_for_completion(dataset.dataset_id)

run = client.autoscientist.create(dataset_id=dataset.dataset_id)   # options below
run = client.autoscientist.wait_for_completion(run.id)             # 4-hour default timeout; re-call to keep waiting
print(run.status, run.best_win_rate, run.download_available)

with client.autoscientist.with_streaming_response.download(run.id) as r:
    r.stream_to_file("best-checkpoint.tgz")
```

`autoscientist.create` options:

| Parameter | Notes |
|---|---|
| `model` | an ID from `client.autoscientist.list_models()`; omitted = AutoScientist chooses |
| `max_iterations` | 1–5, default currently 3 |
| `target_win_rate` | >0.5 to 1; default 0.7 for small models, 0.8 for larger; the loop stops early when reached |
| `training_method` | `"instruction"` (SFT) or `"alignment"` (SFT then DPO; needs a preference-pair dataset and 12,000 pairs) |
| `augmentation_domain_rows`, `augmentation_general_rows` | rows Adaption adds before training; priced separately |
| `hyperparams` | overrides; leave `batch_size` at its default or the launch fails |
| `column_mapping` | refers to the processed dataset schema |
| `idempotency_key` | repeat-safe launches |

Run statuses: `pending`, `running`, `succeeded`, `failed`. `succeeded` means the target was reached **or** iterations ran out, so always read `best_win_rate`.

## Dataset requirements
- SFT minimum: **1,000 effective rows** (10,000 for the largest models).
- Recommended: 20,000 domain rows with about 40% general rows on top, via augmentation. General rows guard against the model forgetting general ability.
- Raw processing works only for local uploads. Rows longer than the model's context are truncated, not rejected.

## Base models that matter to us

| Model ID | Size | Min rows | Runs on an M3 Pro, 18 GB? |
|---|---|---|---|
| `Qwen/Qwen3.5-0.8B` | 0.8B | 1,000 | yes, easily |
| `meta-llama/Llama-3.2-3B-Instruct` | 3B | 1,000 | yes |
| `google/gemma-3-4b-it` | 4B | 1,000 | yes |
| `mistralai/Mistral-7B-Instruct-v0.2` | 7B | 1,000 | yes when quantised to 4-bit |
| `openai/gpt-oss-20b` and larger | 20B+ | 1,000–10,000 | no |

The app's "Tiny AutoScientist" option restricts the choice to models under 10B. The docs' advice for a flat or negative win rate is "use at least a 7–8B model", so the smallest models carry a risk of a poor score.

## Win rate (what the prize ranks)
- The adapted model against its own base model, head to head, "on evaluations derived from your dataset". 70% means the adapted model won about 70% of comparisons.
- `best_win_rate` is the best across iterations.
- Not documented: how the evaluation split is made, or what judges the comparison. `datasets.custom_evals` exists (see vendor docs) and may let us define the evaluation.
- No leaderboard is mentioned in the public docs. See the open question in PLAN.md.

## Cost and time
- "Runtime is hours, and the run uses training credits" (train runbook). No numbers are published.
- The app shows the price of domain expansion, diversity expansion and training separately before you confirm. `datasets.adapt(..., estimate=True)` returns an estimate for adaptation.
- Balance: 1,250 credits. Unused credits do not expire.

## Using the trained model
- **Download**: a `.tgz` with a LoRA adapter (`adapter_config.json`, `adapter_model.safetensors`, tokenizer files). Load it over the same base model with PEFT, or convert for MLX/Ollama. The vendor docs give no local-loading instructions, so budget time for this.
- **Hosted**: the Responses API serves a fixed list (`gemma-4-31b-it`, `glm-5.2`, `qwen3.5-397b`, `gemma-4-26b-a4b-it`, `qwen3.8-27b`, `deepseek-v4-flash`, `glm-53-flash`) and `stack:<slug>`. Whether a stack can use our trained checkpoint is **not stated**; the app labels the feature "Deploy a Self-Improving Model", so check there after a run finishes.

```python
response = client.responses.create(model="stack:your-stack-slug", input="…")
print(response.output_text)
```

## Our fine-tuning task
Prompt: a changelog excerpt plus the package name and versions. Completion: a JSON list of migration rules in the shape defined in ARCHITECTURE.md. The base model is weak at this (strict structure, exact symbols, no invention); a tuned model should be clearly better, which is what the win rate rewards.

## MCP server and Claude plugin (for development)
- MCP URL: `https://api.prod.adaptionlabs.ai/api/v1/mcp` (Streamable HTTP, OAuth sign-in in the browser, or an API key).
- Claude Code plugin: `claude plugin marketplace add adaptionlabs/adaption-claude-plugin` then `claude plugin install adaption@adaption`, then `/mcp` → Adaption → Authenticate.
- The plugin adds three skills: `adaption-dataset`, `adaption-invent`, `adaption-training`.

With the plugin connected, Claude Code can upload the dataset, launch the run and poll it directly, without an API key in `.env`.
