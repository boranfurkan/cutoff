"""Show every Adaption training run recorded in data/work/adaption_runs.json."""
import json
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
from adaption import Adaption

c = Adaption()
for r in json.loads((ROOT / "data/work/adaption_runs.json").read_text())["runs"]:
    x = c.autoscientist.get(r["run_id"])
    aug = "+aug" if r.get("augmentation_domain_rows") else ""
    print(f"{r['run_id'][:8]} {r['model']:18} {r['dataset']}{aug:5} {x.status:10} iter {x.iterations_completed:.0f}/{x.max_iterations:.0f} "
          f"best_win_rate {x.best_win_rate} {('ERR ' + str(x.error)[:120]) if x.error else ''}")
