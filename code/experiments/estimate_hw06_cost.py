"""Estimate 10,000 thirty-turn conversation costs from real experiment JSON."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INPUT_PRICE = 1.0 / 1_000_000
OUTPUT_PRICE = 5.0 / 1_000_000
CONVERSATIONS = 10_000


def cost(row: dict) -> dict:
    turns = row["turns"]
    input_tokens = sum(item["metrics"].get("prompt_tokens", 0) for item in turns)
    output_tokens = sum(item["metrics"].get("completion_tokens", 0) for item in turns)
    total = CONVERSATIONS * (input_tokens * INPUT_PRICE + output_tokens * OUTPUT_PRICE)
    return {"setting": row["setting"], "input_tokens_per_30_turns": input_tokens, "output_tokens_per_30_turns": output_tokens, "cost_for_10000": round(total, 6), "probe_quality": row["summary"]["mean_probe_score"]}


def main() -> None:
    path = ROOT / "reports" / "hw06" / "raw" / "memory_experiments.json"
    rows = [cost(row) for row in json.loads(path.read_text(encoding="utf-8"))]
    best = max(rows, key=lambda row: (row["probe_quality"], -row["cost_for_10000"]))
    worst = max(rows, key=lambda row: (row["cost_for_10000"], -row["probe_quality"]))
    result = {"settings": rows, "best": best, "worst": worst, "rule": "best maximizes probe quality then minimizes cost; worst maximizes cost then breaks ties by lower quality"}
    output = ROOT / "reports" / "hw06" / "raw" / "cost_estimate.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
