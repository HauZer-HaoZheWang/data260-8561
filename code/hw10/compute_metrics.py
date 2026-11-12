from __future__ import annotations
import csv, json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

DATA = Path(__file__).resolve().parents[2] / "reports/hw10/data"

def jsonl(name):
    p = DATA / name
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []

def main():
    labels = {r["case_id"]: float(r["human_score"]) for r in csv.DictReader((DATA / "human_labels.csv").open()) if r.get("human_score", "").strip()}
    rows = jsonl("judge_results.jsonl")
    first = {r["case_id"]: float(r["judge_score"]) for r in rows if r.get("repeat") == 1}
    ids = [i for i in labels if i in first]
    human, judge = [labels[i] for i in ids], [first[i] for i in ids]
    result = {"n": len(ids), "spearman": None, "mad": None}
    if ids:
        result["mad"] = float(np.mean(np.abs(np.array(human) - np.array(judge))))
        if len(set(human)) > 1 and len(set(judge)) > 1:
            result["spearman"] = float(spearmanr(human, judge).statistic)
    by_case = {}
    for r in rows: by_case.setdefault(r["case_id"], []).append(float(r["judge_score"]))
    changes = [max(v) - min(v) for v in by_case.values() if len(v) >= 2]
    result.update({"repeat_change_rate": sum(x > 0 for x in changes) / len(changes) if changes else None,
                   "repeat_mean_absolute_change": float(np.mean(changes)) if changes else None,
                   "repeat_max_absolute_change": max(changes) if changes else None})
    (DATA / "computed_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__": main()
