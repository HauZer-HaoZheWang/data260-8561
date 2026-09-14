from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


#Make project folders importable
PROJECT_DIR = Path(__file__).resolve().parents[2]
CODE_DIR = PROJECT_DIR / "code"
SRC_DIR = PROJECT_DIR / "src"

sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(SRC_DIR))


from graph.state import initialize_state
from graph.workflow import build_workflow


#Set input file path required by HW2.
CASE_PATH = (
    PROJECT_DIR
    / "reports"
    / "hw02"
    / "cases"
    / "schema_input.json"
)

#Set output folder required by HW2
RESULT_DIR = (
    PROJECT_DIR
    / "reports"
    / "hw02"
    / "raw"
)

CSV_PATH = RESULT_DIR / "batch_results.csv"


#Define all experiment configurations.
CONFIGS = [
    {
        "name": "schema_30",
        "ceiling": 6,
        "runs": 30
    },
    {
        "name": "ceiling_2",
        "ceiling": 2,
        "runs": 20
    },
    {
        "name": "ceiling_10",
        "ceiling": 10,
        "runs": 20
    },
]


#Define all columns in the CSV file
CSV_FIELDS = [
    "config",
    "ceiling",
    "run_number",
    "outcome",
    "approved",
    "turn_count",
    "planner_runs",
    "retry_count",
    "last_node",
    "wall_latency_ms",
    "model_latency_ms",
    "input_tokens",
    "output_tokens",
    "issues",
    "planner_proposal",
    "error_type",
    "error_message",
]


def classify_result(
    final: dict[str, Any],
    max_turns: int
) -> str:
    #Read final feedback, turn count and trace
    feedback = final.get("reviewer_feedback")
    turn_count = final.get("turn_count", 0)
    trace = final.get("trace", [])

    #Get the last node recorded in trace.
    last_node = trace[-1].get("node") if trace else None

    #Count how many times Planner ran
    planner_runs = sum(
        1
        for record in trace
        if record.get("node") == "planner"
    )

    #The first Planner run is not a retry.
    retry_count = max(planner_runs - 1, 0)

    #Only Reviewer can approve the final proposal
    success = (
        last_node == "reviewer"
        and isinstance(feedback, dict)
        and feedback.get("approved") is True
    )

    #Classify successful result by retry number.
    if success:
        if retry_count == 0:
            return "valid_first_attempt"

        if retry_count == 1:
            return "valid_after_1_retry"

        return "valid_after_2plus_retries"

    #If not approved and reached ceiling, classify as ceiling.
    if turn_count >= max_turns:
        return "hit_turn_ceiling"

    #Normal workflow should not finish here
    return "unexpected"


def write_csv_row(row: dict[str, Any]) -> None:
    #Create raw result folder if it does not exist.
    RESULT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    #Check whether CSV needs a header
    needs_header = (
        not CSV_PATH.exists()
        or CSV_PATH.stat().st_size == 0
    )

    #Open CSV with append mode, so old rows will not be deleted.
    with CSV_PATH.open(
        "a",
        newline="",
        encoding="utf-8"
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=CSV_FIELDS
        )

        #Only write header when CSV is new or empty
        if needs_header:
            writer.writeheader()

        #Write the current result immediately.
        writer.writerow(row)


def load_case() -> dict[str, Any]:
    #Read experiment input from schema_input.json
    with CASE_PATH.open(
        "r",
        encoding="utf-8"
    ) as case_file:
        return json.load(case_file)


def get_trace_metrics(
    final: dict[str, Any]
) -> dict[str, Any]:
    #Read trace from final state.
    trace = final.get("trace", [])

    #Count how many times Planner ran
    planner_runs = sum(
        1
        for record in trace
        if record.get("node") == "planner"
    )

    #The first Planner run is not a retry
    retry_count = max(planner_runs - 1, 0)

    #Get the last node recorded in trace.
    last_node = (
        trace[-1].get("node")
        if trace
        else ""
    )

    #Add latency from all model calls
    model_latency_ms = sum(
        float(record.get("latency_ms", 0) or 0)
        for record in trace
    )

    #Add input tokens from all model calls.
    input_tokens = sum(
        int(record.get("input_tokens", 0) or 0)
        for record in trace
    )

    #Add output tokens from all model calls
    output_tokens = sum(
        int(record.get("output_tokens", 0) or 0)
        for record in trace
    )

    return {
        "planner_runs": planner_runs,
        "retry_count": retry_count,
        "last_node": last_node,
        "model_latency_ms": round(
            model_latency_ms,
            2
        ),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def main() -> None:
    #Read input case once before running experiments.
    case_data = load_case()

    #Compile workflow only once
    app = build_workflow()

    #Calculate the total number of runs.
    total_runs = sum(
        config["runs"]
        for config in CONFIGS
    )

    completed_runs = 0

    #Run every experiment configuration
    for config in CONFIGS:
        config_name = config["name"]
        ceiling = config["ceiling"]
        run_count = config["runs"]

        #Set ceiling without changing router.py.
        os.environ["MAX_TURNS"] = str(ceiling)

        #Run the current configuration many times
        for run_index in range(run_count):
            completed_runs += 1
            run_number = run_index + 1

            #Print progress before starting each run.
            print(
                f"[{completed_runs}/{total_runs}] "
                f"Running {config_name}, "
                f"run {run_number}/{run_count}, "
                f"ceiling={ceiling}"
            )

            #Record the whole workflow start time
            start_time = time.time()

            try:
                #Create a completely new state for every run.
                initial_state = initialize_state(
                    title=case_data.get("title", ""),
                    content=case_data.get("content", ""),
                    email=case_data.get("email", ""),
                    strict=case_data.get("strict", False),
                    task=case_data.get("task", "")
                )

                #Run the whole workflow
                final_state = app.invoke(initial_state)

                #Calculate whole workflow latency by ms.
                wall_latency_ms = (
                    time.time() - start_time
                ) * 1000

                #Classify the final result
                outcome = classify_result(
                    final_state,
                    max_turns=ceiling
                )

                #Calculate token, retry and latency information.
                metrics = get_trace_metrics(final_state)

                #Read final Reviewer feedback
                feedback = final_state.get(
                    "reviewer_feedback"
                )

                #Read approval and issues from feedback.
                if isinstance(feedback, dict):
                    approved = feedback.get(
                        "approved",
                        False
                    )

                    issues = feedback.get(
                        "issues",
                        []
                    )

                else:
                    approved = False
                    issues = []

                #Create one normal CSV row
                row = {
                    "config": config_name,
                    "ceiling": ceiling,
                    "run_number": run_number,
                    "outcome": outcome,
                    "approved": approved,
                    "turn_count": final_state.get(
                        "turn_count",
                        0
                    ),
                    "planner_runs": metrics[
                        "planner_runs"
                    ],
                    "retry_count": metrics[
                        "retry_count"
                    ],
                    "last_node": metrics[
                        "last_node"
                    ],
                    "wall_latency_ms": round(
                        wall_latency_ms,
                        2
                    ),
                    "model_latency_ms": metrics[
                        "model_latency_ms"
                    ],
                    "input_tokens": metrics[
                        "input_tokens"
                    ],
                    "output_tokens": metrics[
                        "output_tokens"
                    ],
                    "issues": json.dumps(
                        issues,
                        ensure_ascii=False
                    ),
                    "planner_proposal": json.dumps(
                        final_state.get(
                            "planner_proposal",
                            {}
                        ),
                        ensure_ascii=False
                    ),
                    "error_type": "",
                    "error_message": "",
                }

            except Exception as error:
                #Calculate time used before error happened
                wall_latency_ms = (
                    time.time() - start_time
                ) * 1000

                #Create an error row instead of stopping the batch.
                row = {
                    "config": config_name,
                    "ceiling": ceiling,
                    "run_number": run_number,
                    "outcome": "error",
                    "approved": False,
                    "turn_count": "",
                    "planner_runs": "",
                    "retry_count": "",
                    "last_node": "",
                    "wall_latency_ms": round(
                        wall_latency_ms,
                        2
                    ),
                    "model_latency_ms": "",
                    "input_tokens": "",
                    "output_tokens": "",
                    "issues": "[]",
                    "planner_proposal": "{}",
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }

            #Write current row immediately after one run finishes.
            write_csv_row(row)

            #Print the result of current run
            print(
                f"Finished {config_name} "
                f"run {run_number}: "
                f"{row['outcome']}"
            )

    #Print output location after all runs finish.
    print(
        "All experiments finished. "
        f"Results saved to: {CSV_PATH}"
    )


if __name__ == "__main__":
    main()