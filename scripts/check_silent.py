"""Check silent-change seeds: visible tests pass before and after the bump; hidden tests pass before, fail after."""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from cutoff.agent import Run
from cutoff.sandbox import Sandbox


def check(seed):
    r = Run(seed, None, "local", log=lambda *_: None)
    r.dir.mkdir(parents=True)
    with Sandbox(r.dir / "repo") as sb:
        r.sandbox = sb
        r.prepare()
    ok = lambda s: s.startswith("PASS") if s else False
    vis_old = " passed" in r.tests_original and "failed" not in r.tests_original and "error" not in r.tests_original
    good = vis_old and r.baseline_ok and ok(r.hidden_original) and not ok(r.hidden_before)
    ups = ", ".join(f"{u['package']} {u['from']}→{u['to']}" for u in r.upgrades)
    return f"{'OK ' if good else 'BAD'} {seed.name:18} visible {r.tests_original[:22]:22} → {r.tests_before[:22]:22} | hidden {r.hidden_original[:22]:22} → {r.hidden_before[:30]:30} {ups}"


seeds = sorted(p for p in (ROOT / "seeds_silent").iterdir() if p.is_dir() and (not sys.argv[1:] or p.name in sys.argv[1:]))
with ThreadPoolExecutor(4) as pool:
    for line in pool.map(check, seeds):
        print(line)
