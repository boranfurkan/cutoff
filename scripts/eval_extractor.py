"""Measure a local extractor model on the held-out changelog excerpts (labels: Claude Sonnet 5.5, quote-verified).

Usage: .venv/bin/python scripts/eval_extractor.py --base Qwen/Qwen3.5-2B [--adapter best-checkpoint/] [--n 30]
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from build_dataset import training_prompt
from cutoff import local_model

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True)
ap.add_argument("--adapter")
ap.add_argument("--n", type=int, default=30)
a = ap.parse_args()

norm = lambda s: re.sub(r"\s+", " ", str(s)).strip()
key = lambda s: re.sub(r"[^a-z0-9_]", "", str(s).lower().split("(")[0].split(".")[-1])
rows = [json.loads(l) for l in (ROOT / "data/eval/heldout.jsonl").open()][: a.n]
valid = tp = fp = fn = quotes = quotes_ok = empty_agree = empty_total = 0
t0 = time.time()
for r in rows:
    rules = local_model.parse_rules(local_model.generate(training_prompt(r), a.base, a.adapter))
    gold = {key(x["symbol"]) for x in r["rules"]}
    if rules is None:
        fn += len(gold)
        continue
    valid += 1
    ex = norm(r["excerpt"])
    for x in rules:
        quotes += 1
        quotes_ok += norm(x["source_quote"]) in ex and len(norm(x["source_quote"])) > 0
    pred = {key(x["symbol"]) for x in rules}
    tp += len(pred & gold); fp += len(pred - gold); fn += len(gold - pred)
    if not gold:
        empty_total += 1
        empty_agree += not pred
p, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
res = {"base": a.base, "adapter": a.adapter, "rows": len(rows), "valid_json": valid / len(rows),
       "verbatim_quote_rate": quotes_ok / max(quotes, 1), "symbol_precision": round(p, 3), "symbol_recall": round(rec, 3),
       "symbol_f1": round(2 * p * rec / max(p + rec, 1e-9), 3),
       "correctly_empty": f"{empty_agree}/{empty_total}", "seconds_per_row": round((time.time() - t0) / len(rows), 1)}
print(json.dumps(res, indent=1))
out = ROOT / "data/eval/results.jsonl"
out.open("a").write(json.dumps(res) + "\n")
