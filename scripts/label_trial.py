"""Trial: label the first N sample rows with two models (direct calls) and compare.

Usage: .venv/bin/python scripts/label_trial.py [--n 30]
Output: data/work/trial_<model>.jsonl
"""
import argparse, json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from build_dataset import RULE_SCHEMA, TASK, SAMPLE, norm, read_jsonl, write_jsonl, ROOT

load_dotenv(ROOT / ".env")
import anthropic

PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0)}
client = anthropic.Anthropic()


def label(model, r):
    msg = client.messages.create(
        model=model, max_tokens=4000, system=TASK,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": RULE_SCHEMA}},
        messages=[{"role": "user", "content":
                   f"Package: {r['package']}\nUpgrade: {r.get('from_version') or 'previous release'} -> "
                   f"{r['to_version']}\n\nChangelog excerpt:\n{r['excerpt']}"}],
    )
    text = next((b.text for b in msg.content if b.type == "text"), "")
    try:
        rules = json.loads(text)["rules"] if msg.stop_reason == "end_turn" else None
    except Exception:
        rules = None
    return {"id": r["id"], "rules": rules, "stop": msg.stop_reason,
            "in": msg.usage.input_tokens, "out": msg.usage.output_tokens}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=30)
    n = ap.parse_args().n
    rows = read_jsonl(SAMPLE)[:n]
    for model, (pi, po) in PRICES.items():
        with ThreadPoolExecutor(8) as pool:
            res = list(pool.map(lambda r: label(model, r), rows))
        write_jsonl(ROOT / "data" / "work" / f"trial_{model}.jsonl", res)
        ok = [x for x in res if x["rules"] is not None]
        total = kept = 0
        for x, r in zip(res, rows):
            if x["rules"] is None: continue
            ex = norm(r["excerpt"])
            total += len(x["rules"]); kept += sum(norm(q["source_quote"]) in ex for q in x["rules"])
        i, o = sum(x["in"] for x in res), sum(x["out"] for x in res)
        print(f"{model}: {len(ok)}/{n} valid, {total} rules, {kept} with verbatim quote "
              f"({kept/max(total,1):.0%}), empty rows {sum(1 for x in ok if not x['rules'])}, "
              f"tokens {i}/{o}, cost ${i/1e6*pi+o/1e6*po:.3f}")


if __name__ == "__main__":
    main()
