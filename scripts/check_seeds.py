"""Check every seed repo: tests must pass on the pinned versions and fail after the bump. No model calls.

Usage: .venv/bin/python scripts/check_seeds.py [seed-name ...]
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cutoff.agent import Run
from cutoff.sandbox import Sandbox

SEEDS = Path(__file__).resolve().parent.parent / "seeds"


def check(seed: Path):
    r = Run(seed, None, "local", log=lambda *_: None)
    r.dir.mkdir(parents=True)
    with Sandbox(r.dir / "repo") as sb:
        r.sandbox = sb
        out = r.prepare()
    ups = ", ".join(f"{u['package']} {u['from']}→{u['to']}" for u in r.upgrades)
    good = "passed" in r.tests_original and "failed" not in r.tests_original and "error" not in r.tests_original and not r.baseline_ok
    return seed.name, good, r.tests_original, r.tests_before, ups, out


names = sys.argv[1:]
seeds = sorted(p for p in SEEDS.iterdir() if p.is_dir() and (not names or p.name in names))
with ThreadPoolExecutor(5) as pool:
    for name, good, before, after, ups, out in pool.map(check, seeds):
        print(f"{'OK ' if good else 'BAD'} {name:18} old: {before[:38]:38} new: {after[:34]:34} {ups}")
        if names:
            print(out[-2500:])
