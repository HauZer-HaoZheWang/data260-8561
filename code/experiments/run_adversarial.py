from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR / "code" / "experiments"))

import run_batch as R

# Reuse the whole batch runner, but point it at the adversarial case
# and write to a separate CSV so the main results stay untouched.
R.CASE_PATH = PROJECT_DIR / "reports" / "hw02" / "cases" / "adversarial_input.json"
R.CSV_PATH = PROJECT_DIR / "reports" / "hw02" / "raw" / "adversarial_results.csv"
R.CONFIGS = [
    {"name": "adversarial", "ceiling": 6, "runs": 5},
]

if __name__ == "__main__":
    R.main()
