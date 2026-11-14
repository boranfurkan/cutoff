# Claude API reference (for the orchestrator)

Condensed from the Claude API skill bundled with Claude Code (cached 3 Nov 2026). For anything not covered here, load that skill again rather than guessing.

## Basics
- `pip install anthropic`; `anthropic.Anthropic()` reads `ANTHROPIC_API_KEY`.
- Default model: `claude-opus-5-5` ($4 input / $20 output per million tokens, 1M context, 128K max output). Use exact IDs; never add a date suffix.
- Other current IDs: `claude-sonnet-5-5` ($2 / $10), `claude-haiku-5-5` ($0.10 / $0.50).
- `max_tokens`: about 16,000 for non-streaming calls.

## Rules that differ from older habits (Opus 5.5)
- Thinking cannot be disabled. Omit `thinking` or send `{"type": "adaptive"}`. `budget_tokens` returns a 400.
- Depth is set with `output_config={"effort": "low"|"medium"|"high"|"xhigh"|"max"}`. **The default is `medium`**; set it explicitly. For the coding loop use `high`.
- `temperature`, `top_p`, `top_k` return a 400.
- Forced `tool_choice` (`any` or a named tool) returns a 400. Use `auto`, name the tool in the prompt, and put `strict: True` on tools whose arguments must match the schema.
- No assistant prefill. For JSON, use structured outputs.
- Always check `stop_reason` before reading content. `refusal` is possible; enable server-side fallbacks with `betas=["server-side-fallback-2026-07-01"]` and `fallbacks="default"`.
- Append the full `response.content` back to `messages` every turn (thinking blocks included, unchanged).

## Agent loop
Preferred: the SDK tool runner.

```python
import anthropic
from anthropic import beta_tool

client = anthropic.Anthropic()

@beta_tool
def read_file(path: str) -> str:
    """Read a file from the repository checkout.

    Args:
        path: Path relative to the repository root.
    """
    ...

runner = client.beta.messages.tool_runner(
    model="claude-opus-5-5",
    max_tokens=16000,
    tools=[read_file],
    messages=[{"role": "user", "content": "…"}],
)
for message in runner:      # one BetaMessage per turn; stops when Claude stops calling tools
    ...
```

Fallback: a manual loop (`while True: response = client.messages.create(...)`; break on `end_turn`; execute every `tool_use` block; return **all** `tool_result` blocks in one user message; set `is_error: True` on failures).

Use non-streaming calls in the loop so MLflow autolog traces them.

## Structured output
- `client.messages.parse(..., output_format=PydanticModel)` → `response.parsed_output`.
- Or `output_config={"format": {"type": "json_schema", "schema": {...}}}` with `additionalProperties: false` and `required`.
- Used for the Claude fallback of the rule extractor and for generating the fine-tuning dataset.

## Cost control (budget: $50)
- Prompt caching: put the stable system prompt and tool list first; add `cache_control={"type": "ephemeral"}` at the top level of `messages.create`. Verify with `usage.cache_read_input_tokens`.
- Record `response.usage` per call and sum per run.
- Batch API is 50% cheaper for non-urgent bulk work (dataset generation), results within the batch window.
- Trim tool results (test output especially) before returning them to the model.

## Built-in tools worth knowing
- `{"type": "bash_20250124", "name": "bash"}` and `{"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"}` are Anthropic-defined, schema-less tools that we would execute ourselves.
- Server-side `web_search_20260209` / `web_fetch_20260209` exist, but Cutoff uses Linkup for research so that Linkup is central.
