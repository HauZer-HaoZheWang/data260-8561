"""Offline HW10 evidence checker. It never invents missing measurements."""
from pathlib import Path
import csv, json, sys

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "reports/hw10/data"
required = ["eval_cases.json", "human_labels.csv", "judge_results.jsonl", "spans.jsonl", "latency_experiment.jsonl", "trace_examples.json"]
missing = [x for x in required if not (DATA / x).exists()]
print("DATA:", DATA)
if missing:
    print("MISSING:", ", ".join(missing))
    sys.exit(1)
cases = json.loads((DATA / "eval_cases.json").read_text())
labels = list(csv.DictReader((DATA / "human_labels.csv").open()))
latency = [json.loads(x) for x in (DATA / "latency_experiment.jsonl").read_text().splitlines() if x.strip()]
print(f"cases={len(cases)} labels={len(labels)} latency_rows={len(latency)}")
if len(cases) != 20 or len(labels) != 20:
    raise SystemExit("Expected exactly 20 cases and 20 labels")
if any(not r.get("human_score", "").strip() for r in labels):
    raise SystemExit("Human labels are not complete")
if len(latency) != 50 or any(r.get("cache_hit") is not False for r in latency):
    raise SystemExit("Expected 50 confirmed cache misses")
print("HW10 evidence shape: OK")
