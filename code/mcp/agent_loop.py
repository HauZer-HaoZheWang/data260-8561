"""Bounded Ollama agent loop for the HW5 clinical-trial tools."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from tool_executor import execute_tool


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_PATH = PROJECT_ROOT / "reports" / "hw05" / "agent_runs.jsonl"
DEFAULT_MODEL = "qwen3:8b"

TOOL_DESCRIPTIONS = {
    "search_trials": {
        "purpose": "Search trial title, NCT code, or sponsor name.",
        "inputs": {"query": "string", "limit": "integer 1-25"},
    },
    "get_trial_details": {
        "purpose": "Get one trial by NCT code.",
        "inputs": {"nct_code": "NCT followed by eight digits"},
    },
    "summarize_sponsors": {
        "purpose": "Aggregate trial and participant totals by sponsor.",
        "inputs": {
            "min_trials": "integer 1-5000; application safety policy may block it",
            "limit": "integer 1-50",
        },
    },
}

ToolExecutor = Callable[[str, Mapping[str, Any]], str]


class OllamaDecisionModel:
    """Small adapter that asks a local Ollama model for one JSON action."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name

    def next_action(
        self,
        messages: Sequence[dict[str, str]],
        tools: Mapping[str, Any],
    ) -> dict[str, Any]:
        import ollama

        system_prompt = (
            "You are a clinical-trial data assistant. Use the provided tools for "
            "every request about database facts. Return only one JSON object. "
            "If the user supplies an exact tool name and exact inputs, submit "
            "those inputs unchanged; application code owns validation and safety. "
            "Use at most one tool call for the request. After receiving any "
            "message beginning TOOL RESULT, you must return a final action and "
            "must not call another tool. "
            "To call a tool return "
            '{"type":"tool","name":"tool_name","inputs":{...}}. '
            "After receiving a TOOL RESULT, return "
            '{"type":"final","content":"concise answer"}. '
            "Never invent database results. Available tools: "
            + json.dumps(tools, ensure_ascii=False)
        )
        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "system", "content": system_prompt}, *messages],
            format="json",
            options={"temperature": 0},
        )
        content = response.message.content
        action = json.loads(content)
        if not isinstance(action, dict) or action.get("type") not in {"tool", "final"}:
            raise ValueError("model returned an invalid action")
        return action


class MockModel:
    """Deterministic model used only by offline tests."""

    def __init__(self, actions: Sequence[Mapping[str, Any]]):
        self._actions = [dict(action) for action in actions]
        self._index = 0

    def next_action(
        self,
        messages: Sequence[dict[str, str]],
        tools: Mapping[str, Any],
    ) -> dict[str, Any]:
        del messages, tools
        if self._index >= len(self._actions):
            return {"type": "final", "content": "mock actions exhausted"}
        action = self._actions[self._index]
        self._index += 1
        return action


def _append_run(log_path: Path, run: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(run, ensure_ascii=False, sort_keys=True) + "\n")


def run_agent(
    user_input: str,
    *,
    model: Any | None = None,
    max_steps: int = 4,
    executor: ToolExecutor = execute_tool,
    log_path: Path = DEFAULT_LOG_PATH,
) -> dict[str, Any]:
    """Run a bounded tool loop and record every action and stop reason."""
    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError("user_input must be a non-empty string")
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")

    active_model = model if model is not None else OllamaDecisionModel()
    messages: list[dict[str, str]] = [
        {"role": "user", "content": user_input.strip()}
    ]
    steps: list[dict[str, Any]] = []
    tool_call_count = 0
    stop_reason = "max_steps"
    final_response = "Stopped after reaching the maximum number of steps."

    for step_number in range(1, max_steps + 1):
        try:
            action = active_model.next_action(messages, TOOL_DESCRIPTIONS)
        except Exception as error:  # noqa: BLE001 - agent boundary must be safe
            action = {
                "type": "model_error",
                "error": f"{type(error).__name__}: {error}",
            }
            steps.append({"step": step_number, "model_action": action})
            stop_reason = "model_error"
            final_response = "The local model failed to produce a valid action."
            break

        step: dict[str, Any] = {
            "step": step_number,
            "model_action": action,
        }

        if action.get("type") == "final":
            final_response = str(action.get("content") or "").strip()
            step["final_response"] = final_response
            steps.append(step)
            stop_reason = "normal_completion"
            break

        name = str(action.get("name") or "")
        inputs = action.get("inputs")
        if not isinstance(inputs, Mapping):
            inputs = {}
        raw_result = executor(name, inputs)
        try:
            result = json.loads(raw_result)
        except json.JSONDecodeError:
            result = {
                "ok": False,
                "data": None,
                "error": "tool returned invalid JSON",
            }

        tool_call_count += 1
        step.update(
            {
                "tool_call": name,
                "tool_input": dict(inputs),
                "tool_result": result,
            }
        )
        steps.append(step)
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(action, ensure_ascii=False),
            }
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "TOOL RESULT: "
                    + json.dumps(result, ensure_ascii=False)
                    + "\nReturn the next JSON action."
                ),
            }
        )

        error_message = str(result.get("error") or "")
        if result.get("ok") is False and error_message.startswith("safety rule:"):
            stop_reason = "safety_rule_block"
            final_response = error_message
            break

    run = {
        "run_id": str(uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "user_input": user_input.strip(),
        "max_steps": max_steps,
        "step_count": len(steps),
        "tool_call_count": tool_call_count,
        "stop_reason": stop_reason,
        "final_response": final_response,
        "steps": steps,
    }
    _append_run(log_path, run)
    return run
