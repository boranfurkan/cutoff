"""Build the fine-tuning dataset: changelog excerpt -> structured migration rules.

Steps (run in order):
  select    pick a balanced sample from data/raw/changelog_chunks.jsonl (free)
  estimate  rough labeling cost per model (free, offline)
  submit    send the sample to Claude through the Message Batches API (50% price) -- costs money
  collect   download batch results, keep only rules whose quote appears verbatim in the excerpt
  export    write data/train/adaption_train.jsonl (prompt, completion) and data/eval/heldout.jsonl

Usage:
  .venv/bin/python scripts/build_dataset.py select --train 1500 --heldout 100
  .venv/bin/python scripts/build_dataset.py estimate
  .venv/bin/python scripts/build_dataset.py submit --model claude-sonnet-5-5
  .venv/bin/python scripts/build_dataset.py collect
  .venv/bin/python scripts/build_dataset.py export
"""
import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "changelog_chunks.jsonl"
SAMPLE = ROOT / "data" / "work" / "sample.jsonl"
BATCH_STATE = ROOT / "data" / "work" / "batch.json"
LABELED = ROOT / "data" / "work" / "labeled.jsonl"
TRAIN = ROOT / "data" / "train" / "adaption_train.jsonl"
HELDOUT = ROOT / "data" / "eval" / "heldout.jsonl"

KINDS = ["renamed", "removed", "signature_changed", "behavior_changed", "moved", "default_changed", "dependency_dropped"]

RULE_SCHEMA = {
    "type": "object",
    "properties": {
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": KINDS},
                    "symbol": {"type": "string"},
                    "replacement": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "before": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "after": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "note": {"type": "string"},
                    "source_quote": {"type": "string"},
                },
                "required": ["kind", "symbol", "replacement", "before", "after", "note", "source_quote"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["rules"],
    "additionalProperties": False,
}

# The instruction both Claude (labeling) and the fine-tuned model (training prompt) receive.
TASK = """Extract migration rules from a library changelog excerpt.

A migration rule is a change that can break code which uses the library: something renamed, removed, moved,
given a new signature, a changed default, changed behavior that callers rely on, or a dropped Python/dependency
version. Ignore new features, bug fixes, performance work, docs and internal changes, unless they remove or
replace something callers use.

For each rule return:
- kind: one of renamed | removed | signature_changed | behavior_changed | moved | default_changed | dependency_dropped
- symbol: the affected public name (e.g. "pkg.module.func", "Class.method", "--cli-flag", "Python 3.9")
- replacement: what to use instead, or null if there is none
- before / after: a minimal code example of the old and new usage, or null when the excerpt gives too little to write one
- note: one sentence on what changed and how it breaks callers
- source_quote: a short span copied EXACTLY, character for character, from the excerpt that supports the rule

Only use information in the excerpt. Do not invent symbols or versions. If nothing in the excerpt can break
callers, return {"rules": []}.
Answer with JSON only: {"rules": [...]}"""


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def training_prompt(row: dict) -> str:
    frm = row.get("from_version") or "previous release"
    return f"{TASK}\n\nPackage: {row['package']}\nUpgrade: {frm} -> {row['to_version']}\n\nChangelog excerpt:\n{row['excerpt']}"


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.open()] if p.exists() else []


def write_jsonl(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def cmd_select(args):
    rows = read_jsonl(RAW)
    rng = random.Random(14112026)
    by_pkg = defaultdict(lambda: {True: [], False: []})
    for r in rows:
        by_pkg[r["package"]][r["mentions_breaking"]].append(r)
    for d in by_pkg.values():
        rng.shuffle(d[True])
        rng.shuffle(d[False])

    total = args.train + args.heldout
    want = {True: round(total * 0.8), False: total - round(total * 0.8)}
    picked = []
    for flag in (True, False):  # round-robin across packages so no library dominates
        pools = [d[flag] for d in by_pkg.values() if d[flag]]
        while len([p for p in picked if p["mentions_breaking"] == flag]) < want[flag] and any(pools):
            for pool in pools:
                if pool and len([p for p in picked if p["mentions_breaking"] == flag]) < want[flag]:
                    picked.append(pool.pop())
    rng.shuffle(picked)

    # Hold out whole packages' worth of rows? No: hold out random rows, but keep the split fixed by id.
    for i, r in enumerate(picked):
        r["split"] = "heldout" if i < args.heldout else "train"
    write_jsonl(SAMPLE, picked)
    pk = len({r["package"] for r in picked})
    print(f"selected {len(picked)} rows from {pk} packages "
          f"({sum(r['mentions_breaking'] for r in picked)} mention breaking changes, {args.heldout} held out) -> {SAMPLE}")


PRICES = {  # batch prices, $ per million tokens (half of standard)
    "claude-opus-5-5": (2.0, 10.0),
    "claude-sonnet-5-5": (1.0, 5.0),
    "claude-haiku-5-5": (0.05, 0.25),
}


def cmd_estimate(args):
    rows = read_jsonl(SAMPLE)
    if not rows:
        sys.exit("run `select` first")
    chars = sum(len(training_prompt(r)) for r in rows)
    in_tok = chars / 3.5
    out_tok = len(rows) * 900  # JSON rules plus low-effort thinking, rough
    print(f"{len(rows)} requests, ~{in_tok/1e6:.2f}M input tokens, ~{out_tok/1e6:.2f}M output tokens (rough)")
    for model, (pi, po) in PRICES.items():
        print(f"  {model:20} ~${in_tok/1e6*pi + out_tok/1e6*po:6.2f} with the Batch API")


def cmd_submit(args):
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    rows = read_jsonl(SAMPLE)
    if not rows:
        sys.exit("run `select` first")
    if args.limit:
        rows = rows[: args.limit]
    client = anthropic.Anthropic()
    system = [{"type": "text", "text": TASK, "cache_control": {"type": "ephemeral"}}]
    requests = [
        Request(
            custom_id=r["id"],
            params=MessageCreateParamsNonStreaming(
                model=args.model,
                max_tokens=4000,
                system=system,
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": RULE_SCHEMA}},
                messages=[{"role": "user", "content":
                           f"Package: {r['package']}\nUpgrade: {r.get('from_version') or 'previous release'} -> "
                           f"{r['to_version']}\n\nChangelog excerpt:\n{r['excerpt']}"}],
            ),
        )
        for r in rows
    ]
    batch = client.messages.batches.create(requests=requests)
    BATCH_STATE.parent.mkdir(parents=True, exist_ok=True)
    BATCH_STATE.write_text(json.dumps({"batch_id": batch.id, "model": args.model, "count": len(requests)}))
    print(f"submitted batch {batch.id} with {len(requests)} requests on {args.model}; status {batch.processing_status}")


def cmd_collect(args):
    import anthropic

    state = json.loads(BATCH_STATE.read_text())
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(state["batch_id"])
    if batch.processing_status != "ended":
        c = batch.request_counts
        sys.exit(f"batch {batch.id} still {batch.processing_status}: {c.processing} processing, {c.succeeded} done")

    by_id = {r["id"]: r for r in read_jsonl(SAMPLE)}
    out, stats = [], defaultdict(int)
    in_tok = out_tok = 0
    for res in client.messages.batches.results(batch.id):
        if res.result.type != "succeeded":
            stats[f"request_{res.result.type}"] += 1
            continue
        msg = res.result.message
        in_tok += msg.usage.input_tokens + (msg.usage.cache_read_input_tokens or 0)
        out_tok += msg.usage.output_tokens
        if msg.stop_reason != "end_turn":
            stats[f"stop_{msg.stop_reason}"] += 1
            continue
        text = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            rules = json.loads(text)["rules"]
        except (json.JSONDecodeError, KeyError, TypeError):
            stats["bad_json"] += 1
            continue
        row = by_id[res.custom_id]
        excerpt = norm(row["excerpt"])
        kept = [x for x in rules if norm(x["source_quote"]) and norm(x["source_quote"]) in excerpt]
        stats["rules_total"] += len(rules)
        stats["rules_kept"] += len(kept)
        if rules and not kept:
            stats["row_dropped_no_verbatim_quote"] += 1
            continue
        stats["rows_with_rules" if kept else "rows_empty"] += 1
        out.append({**row, "rules": kept})
    write_jsonl(LABELED, out)
    print(f"labeled {len(out)} rows -> {LABELED}")
    print(f"tokens: {in_tok:,} in, {out_tok:,} out")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")


def cmd_export(args):
    rows = read_jsonl(LABELED)
    if not rows:
        sys.exit("run `collect` first")
    train = [{"prompt": training_prompt(r), "completion": json.dumps({"rules": r["rules"]}, ensure_ascii=False)}
             for r in rows if r["split"] == "train"]
    held = [r for r in rows if r["split"] == "heldout"]
    write_jsonl(TRAIN, train)
    write_jsonl(HELDOUT, held)
    print(f"train: {len(train)} rows -> {TRAIN}")
    print(f"heldout: {len(held)} rows -> {HELDOUT}")
    if len(train) < 1000:
        print("WARNING: Adaption needs at least 1,000 effective rows for SFT; add augmentation or select more.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--train", type=int, default=1500)
    s.add_argument("--heldout", type=int, default=100)
    sub.add_parser("estimate")
    s = sub.add_parser("submit")
    s.add_argument("--model", required=True, choices=list(PRICES))
    s.add_argument("--limit", type=int, default=0, help="only submit the first N rows (for a trial run)")
    sub.add_parser("collect")
    sub.add_parser("export")
    args = ap.parse_args()
    {"select": cmd_select, "estimate": cmd_estimate, "submit": cmd_submit,
     "collect": cmd_collect, "export": cmd_export}[args.cmd](args)


if __name__ == "__main__":
    main()
