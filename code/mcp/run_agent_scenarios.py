"""Run four required local-Ollama scenarios and write Part 5 evidence."""

from __future__ import annotations

import json
from pathlib import Path

from agent_loop import DEFAULT_LOG_PATH, OllamaDecisionModel, run_agent


PROJECT_ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = PROJECT_ROOT / "reports" / "hw05" / "METRICS.md"
REFLECTION_PATH = PROJECT_ROOT / "reports" / "hw05" / "REFLECTION.md"

SCENARIOS = [
    (
        "search",
        "Use search_trials with query Seeded Clinical Trial 1 and limit 2. After "
        "that single tool result, answer directly without calling another tool.",
    ),
    (
        "detail",
        "Use get_trial_details for NCT00000005. After that single tool result, "
        "answer directly without calling another tool.",
    ),
    (
        "aggregate_allowed",
        "Use summarize_sponsors with min_trials 100 and limit 3. After that "
        "single tool result, answer directly without calling another tool.",
    ),
    (
        "aggregate_blocked",
        "Your first action must call summarize_sponsors with exactly min_trials 1 "
        "and limit 3. Submit those exact values unchanged so the application safety "
        "boundary can evaluate them.",
    ),
]


def write_metrics(runs: list[tuple[str, dict]]) -> None:
    rows = "\n".join(
        f"| {name} | {run['step_count']} | {run['stop_reason']} | "
        f"{run['tool_call_count']} |"
        for name, run in runs
    )
    METRICS_PATH.write_text(
        "# HW5 Part 5 Agent Metrics\n\n"
        "Local model: `qwen3:8b`.\n\n"
        "| Scenario | Step count | Stop reason | Tool-call count |\n"
        "| --- | ---: | --- | ---: |\n"
        f"{rows}\n",
        encoding="utf-8",
    )


def write_reflection(runs: list[tuple[str, dict]]) -> None:
    selected_name, selected = next(
        (
            item
            for item in runs
            if item[1]["stop_reason"] == "safety_rule_block"
        ),
        runs[-1],
    )
    prompt = selected["user_input"]
    stop_reason = selected["stop_reason"]
    step_count = selected["step_count"]
    tool_count = selected["tool_call_count"]

    reflection = f"""# HW5 Part 5 Reflection

I selected the `{selected_name}` run from `agent_runs.jsonl`. The user prompt was:
“{prompt}” The harness first placed this request in the conversation and asked the
local `qwen3:8b` model for one JSON action. The system prompt listed only the three
approved clinical-trial tools and required the model to obtain database facts through
those tools rather than inventing an answer.

The model returned a structured tool action. The harness recorded that action, checked
the tool name, and sent its input to the single `execute_tool` boundary. That boundary
applied schema validation and the domain safety policy before any database work. The
safety policy requires Sponsor aggregates to represent at least five trials. This rule
reduces the risk of presenting very small groups as meaningful or privacy-safe
aggregates. The returned `{{ok, data, error}}` envelope was added to both the run log and
the model conversation, so every decision remained inspectable.

This run ended with stop reason `{stop_reason}` after {step_count} step(s) and
{tool_count} tool call(s). The harness stopped at the policy boundary instead of asking
the model to work around the refusal. That behavior is important: the model proposes
actions, but deterministic application code owns authorization and stopping decisions.
The `max_steps` ceiling supplies a second independent safeguard against looping. This
run demonstrates that logging, validation, policy enforcement, and bounded control flow
work together to make the agent easier to audit than an unrestricted model-to-database
connection.
"""
    word_count = len(reflection.replace("# HW5 Part 5 Reflection", "").split())
    if not 200 <= word_count <= 300:
        raise RuntimeError(f"reflection word count out of range: {word_count}")
    REFLECTION_PATH.write_text(
        reflection + f"\nWord count: {word_count}\n",
        encoding="utf-8",
    )


def main() -> None:
    DEFAULT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_LOG_PATH.write_text("", encoding="utf-8")
    model = OllamaDecisionModel("qwen3:8b")
    runs: list[tuple[str, dict]] = []

    print("HW5 Part 5 local Ollama scenarios")
    for name, prompt in SCENARIOS:
        run = run_agent(prompt, model=model, max_steps=4)
        runs.append((name, run))
        print(
            f"{name}: steps={run['step_count']}, "
            f"stop_reason={run['stop_reason']}, "
            f"tool_calls={run['tool_call_count']}"
        )
        print(f"final={run['final_response']}")

        expected_stop = (
            "safety_rule_block"
            if name == "aggregate_blocked"
            else "normal_completion"
        )
        if run["stop_reason"] != expected_stop:
            raise RuntimeError(
                f"{name} stopped with {run['stop_reason']}; "
                f"expected {expected_stop}"
            )
        if run["tool_call_count"] != 1:
            raise RuntimeError(
                f"{name} made {run['tool_call_count']} tool calls; expected 1"
            )

    write_metrics(runs)
    write_reflection(runs)
    print(f"runs_logged={len(runs)}")
    print(f"saved={DEFAULT_LOG_PATH}")
    print(f"saved={METRICS_PATH}")
    print(f"saved={REFLECTION_PATH}")
    print("Agent scenarios PASS")


if __name__ == "__main__":
    main()
