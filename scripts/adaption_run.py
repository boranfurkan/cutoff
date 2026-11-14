"""Upload the training file to Adaption and manage an AutoScientist run.

Usage:
  .venv/bin/python scripts/adaption_run.py upload              # upload data/train/adaption_train.jsonl (raw mode)
  .venv/bin/python scripts/adaption_run.py launch --model Qwen/Qwen3.5-9B   # starts training: spends credits
  .venv/bin/python scripts/adaption_run.py status
  .venv/bin/python scripts/adaption_run.py download
State is kept in data/work/adaption.json.
"""
import argparse, json, sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
from adaption import Adaption

STATE = ROOT / "data" / "work" / "adaption.json"
TRAIN = ROOT / "data" / "train" / "adaption_train.jsonl"
client = Adaption()


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save(s):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2))


def upload(_):
    ds = client.datasets.upload_file(
        str(TRAIN), processing_mode="raw",
        column_mapping={"prompt": "prompt", "completion": "completion"},
    )
    s = load(); s["dataset_id"] = ds.dataset_id; save(s)
    client.datasets.wait_for_completion(ds.dataset_id)
    st = client.datasets.get_status(ds.dataset_id)
    print("dataset", ds.dataset_id, "status", st.status, "rows", st.row_count)


def launch(a):
    s = load()
    kw = {"dataset_id": s["dataset_id"], "training_method": "instruction",
          "idempotency_key": f"cutoff-{s['dataset_id']}-{a.model or 'auto'}"}
    if a.model:
        kw["model"] = a.model
    if a.max_iterations:
        kw["max_iterations"] = a.max_iterations
    run = client.autoscientist.create(**kw)
    s["run_id"] = run.id; save(s)
    print(run.model_dump_json(indent=2))


def status(_):
    run = client.autoscientist.get(load()["run_id"])
    print(run.model_dump_json(indent=2))


def download(_):
    run = client.autoscientist.get(load()["run_id"])
    if not run.download_available:
        sys.exit(f"no checkpoint yet (status {run.status})")
    out = ROOT / "best-checkpoint.tgz"
    with client.autoscientist.with_streaming_response.download(run.id) as r:
        r.stream_to_file(str(out))
    print("saved", out)


ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
sub.add_parser("upload"); sub.add_parser("status"); sub.add_parser("download")
p = sub.add_parser("launch"); p.add_argument("--model"); p.add_argument("--max-iterations", type=int)
a = ap.parse_args()
{"upload": upload, "launch": launch, "status": status, "download": download}[a.cmd](a)
