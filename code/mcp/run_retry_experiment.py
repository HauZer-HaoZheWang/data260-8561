"""Run the reproducible 150-call HW5 retry experiment."""

from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any

from retry_policy import RetryExhaustedError, SeededFailureInjector, run_with_retry


VERIFY_SEED = 268561
FAILURE_RATES = (0.0, 0.2, 0.5)
CALLS_PER_RATE = 50
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 0.5
BASE_DELAY_SECONDS = 0.005
MAX_DELAY_SECONDS = 0.020

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "reports" / "hw05" / "raw"
CSV_PATH = RAW_DIR / "retry_experiment.csv"
SUMMARY_PATH = RAW_DIR / "retry_summary.json"
ANALYSIS_PATH = PROJECT_ROOT / "reports" / "hw05" / "PART3_RETRY_ANALYSIS.md"


def operation() -> str:
    return "ok"


def run_rate(failure_rate: float) -> list[dict[str, Any]]:
    injector = SeededFailureInjector(failure_rate, VERIFY_SEED)
    rows: list[dict[str, Any]] = []

    for call_number in range(1, CALLS_PER_RATE + 1):
        try:
            outcome = run_with_retry(
                operation,
                timeout_seconds=TIMEOUT_SECONDS,
                max_attempts=MAX_ATTEMPTS,
                base_delay_seconds=BASE_DELAY_SECONDS,
                max_delay_seconds=MAX_DELAY_SECONDS,
                should_fail=injector,
            )
            rows.append(
                {
                    "verify_seed": VERIFY_SEED,
                    "failure_rate": failure_rate,
                    "call_number": call_number,
                    "success": True,
                    "attempts": outcome.attempts,
                    "latency_ms": round(outcome.latency_ms, 3),
                    "error": "",
                }
            )
        except RetryExhaustedError as error:
            rows.append(
                {
                    "verify_seed": VERIFY_SEED,
                    "failure_rate": failure_rate,
                    "call_number": call_number,
                    "success": False,
                    "attempts": error.attempts,
                    "latency_ms": round(error.latency_ms, 3),
                    "error": "retry attempts exhausted",
                }
            )
    return rows


def percentile_99(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(0.99 * len(ordered)) - 1)
    return ordered[index]


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for rate in FAILURE_RATES:
        selected = [row for row in rows if row["failure_rate"] == rate]
        latencies = [float(row["latency_ms"]) for row in selected]
        successes = sum(bool(row["success"]) for row in selected)
        summaries.append(
            {
                "failure_rate": rate,
                "calls": len(selected),
                "success_rate_percent": round(100.0 * successes / len(selected), 1),
                "mean_latency_ms": round(statistics.fmean(latencies), 3),
                "p99_latency_ms": round(percentile_99(latencies), 3),
            }
        )
    return summaries


def write_outputs(rows: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "verify_seed": VERIFY_SEED,
        "calls_per_rate": CALLS_PER_RATE,
        "total_calls": len(rows),
        "max_attempts": MAX_ATTEMPTS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "base_delay_seconds": BASE_DELAY_SECONDS,
        "max_delay_seconds": MAX_DELAY_SECONDS,
        "results": summaries,
    }
    SUMMARY_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    table_rows = "\n".join(
        "| {rate:.0%} | {success:.1f}% | {mean:.3f} | {p99:.3f} |".format(
            rate=item["failure_rate"],
            success=item["success_rate_percent"],
            mean=item["mean_latency_ms"],
            p99=item["p99_latency_ms"],
        )
        for item in summaries
    )
    ANALYSIS_PATH.write_text(
        "# Part 3 Retry Policy Analysis\n\n"
        f"VERIFY_SEED = {VERIFY_SEED}. Each failure rate used "
        f"{CALLS_PER_RATE} calls, for {len(rows)} calls total. The policy used "
        f"{MAX_ATTEMPTS} maximum attempts, a {TIMEOUT_SECONDS:.1f}-second timeout, "
        f"and bounded exponential backoff from {BASE_DELAY_SECONDS * 1000:.0f} ms "
        f"to {MAX_DELAY_SECONDS * 1000:.0f} ms.\n\n"
        "| Injected failure rate | Success rate | Mean latency (ms) | p99 latency (ms) |\n"
        "| ---: | ---: | ---: | ---: |\n"
        f"{table_rows}\n\n"
        "The policy is suitable for an interactive assistant because three bounded "
        "attempts recover most transient failures while keeping worst-case waiting "
        "short. The 50% condition shows the tradeoff: retries improve reliability but "
        "increase tail latency and still cannot guarantee success.\n\n"
        "For batch processing, I would allow more attempts and longer timeouts because "
        "throughput and eventual completion matter more than immediate feedback. I "
        "would also increase the maximum backoff and add jitter so many workers do not "
        "retry at the same time.\n",
        encoding="utf-8",
    )


def main() -> None:
    rows = [row for rate in FAILURE_RATES for row in run_rate(rate)]
    replay = [row for rate in FAILURE_RATES for row in run_rate(rate)]
    first_sequence = [(row["success"], row["attempts"]) for row in rows]
    replay_sequence = [(row["success"], row["attempts"]) for row in replay]
    assert first_sequence == replay_sequence
    assert len(rows) == 150

    summaries = summarize(rows)
    write_outputs(rows, summaries)

    print("HW5 Part 3 reproducible retry experiment")
    print(f"VERIFY_SEED={VERIFY_SEED}")
    print("rate  calls  success_rate  mean_ms  p99_ms")
    for item in summaries:
        print(
            f"{item['failure_rate']:.0%}    "
            f"{item['calls']:>3}    "
            f"{item['success_rate_percent']:>6.1f}%      "
            f"{item['mean_latency_ms']:>7.3f}  "
            f"{item['p99_latency_ms']:>7.3f}"
        )
    print(f"raw_rows={len(rows)}")
    print(f"reproducible_sequence={first_sequence == replay_sequence}")
    print(f"saved={CSV_PATH}")
    print(f"saved={SUMMARY_PATH}")
    print(f"saved={ANALYSIS_PATH}")
    print("Retry experiment PASS")


if __name__ == "__main__":
    main()
