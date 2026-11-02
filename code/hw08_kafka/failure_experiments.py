"""Command-line experiment planner and evidence writer for Part 3.

Run each scenario against live consumers and save the actual output in
reports/hw08/raw/. The script does not fabricate pass results.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "reports" / "hw08" / "raw"


def record(name, before, after, observations):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"{name}.json"
    payload = {"scenario": name, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "before_fix": before, "after_fix": after, "observations": observations}
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=["duplicate", "death", "poison", "ordering"])
    args = parser.parse_args()
    record(args.scenario, "FILL_FROM_REAL_LOG", "FILL_FROM_REAL_LOG",
           ["Run the prescribed experiment and replace placeholders with exact logs."])


if __name__ == "__main__": main()
