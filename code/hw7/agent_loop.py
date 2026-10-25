"""Deterministic, bounded tool loop and Reflexion extension for HW7."""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from pathlib import Path

MCP_DIR = Path(__file__).resolve().parents[1] / "mcp"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))


def default_executor(name: str, inputs: Mapping[str, Any]) -> str:
    # Lazy import keeps the offline HW7 tests independent of MySQL/SQLAlchemy packages.
    from tool_executor import execute_tool
    return execute_tool(name, inputs)


ToolExecutor = Callable[[str, Mapping[str, Any]], str]


@dataclass
class SequenceModel:
    """Small deterministic model used for reproducible demonstrations/tests."""

    actions: Sequence[Mapping[str, Any]]
    index: int = 0

    def next_action(self, messages: Sequence[dict[str, str]], tools: Mapping[str, Any]):
        del messages, tools
        if self.index >= len(self.actions):
            return {"type": "final", "content": "No further action."}
        action = dict(self.actions[self.index])
        self.index += 1
        return action


def _parse_result(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"ok": False, "data": None, "error": f"invalid tool JSON: {exc}"}
    return value if isinstance(value, dict) else {"ok": False, "data": None, "error": "tool result was not an object"}


def run_agent(
    user_input: str,
    *,
    model: Any,
    executor: ToolExecutor = default_executor,
    max_steps: int = 8,
    repair_limit: int = 1,
) -> dict[str, Any]:
    """Run tool calls, append tool-role results, and recover bounded model errors."""
    messages = [{"role": "user", "content": user_input}]
    trace: list[dict[str, Any]] = []
    repairs = 0
    tool_calls = 0
    stop_reason = "budget_exhausted"
    final = ""
    for step in range(1, max_steps + 1):
        try:
            action = model.next_action(messages, {})
            if not isinstance(action, Mapping) or action.get("type") not in {"tool", "final"}:
                raise ValueError("action must be a tool or final object")
        except Exception as exc:  # bounded repair path
            if repairs >= repair_limit:
                stop_reason = "human_review"
                trace.append({"step": step, "error": str(exc), "repair": False})
                break
            repairs += 1
            trace.append({"step": step, "error": str(exc), "repair": True})
            messages.append({"role": "user", "content": f"REPAIR: {exc}. Return one valid JSON action."})
            continue
        if action.get("type") == "final":
            final = str(action.get("content", ""))
            stop_reason = "success"
            trace.append({"step": step, "final": final})
            break
        name = action.get("name")
        inputs = action.get("inputs")
        if not isinstance(name, str) or not isinstance(inputs, Mapping):
            if repairs >= repair_limit:
                stop_reason = "human_review"
                trace.append({"step": step, "action": dict(action), "repair": False})
                break
            repairs += 1
            messages.append({"role": "user", "content": "REPAIR: tool name and inputs must be valid."})
            trace.append({"step": step, "action": dict(action), "repair": True})
            continue
        result = _parse_result(executor(name, inputs))
        tool_calls += 1
        trace.append({"step": step, "tool": name, "inputs": dict(inputs), "observation": result})
        messages.extend([
            {"role": "assistant", "content": json.dumps(action)},
            {"role": "tool", "content": json.dumps(result)},
        ])
    return {"final": final, "trace": trace, "tool_calls": tool_calls, "repairs": repairs, "stop_reason": stop_reason}


def verify_task(task: str, run: Mapping[str, Any]) -> tuple[bool, str]:
    """Deterministic verifier that checks required tool names and successful observations."""
    tools = [item.get("tool") for item in run.get("trace", []) if item.get("tool")]
    required = {
        "A": ["search_trials", "get_trial_details"],
        "B": ["summarize_sponsors", "search_trials"],
        "C": ["search_trials", "get_trial_details", "get_trial_details"],
    }[task]
    ok = tools[: len(required)] == required and all(
        item.get("observation", {}).get("ok")
        for item in run.get("trace", []) if item.get("tool")
    )
    return ok, "required tool chain completed" if ok else f"expected {required}, got {tools}"


def run_reflexion(task: str, attempts: Sequence[Mapping[str, Any]], *, max_retries: int = 2) -> dict[str, Any]:
    """Run fixed attempts with concise evidence-backed reflections and hard budgets."""
    reflections: list[dict[str, Any]] = []
    for index, attempt in enumerate(attempts[: max_retries + 1]):
        ok, evidence = verify_task(task, attempt)
        if ok:
            return {"task": task, "success": True, "attempts": index + 1, "stop_reason": "success", "reflections": reflections}
        reflections.append({"attempt": index + 1, "evidence": evidence, "strategy": "follow the fixed task chain and verify each successful observation"})
    reason = "budget_exhausted" if len(attempts) > max_retries + 1 else "human_review"
    return {"task": task, "success": False, "attempts": min(len(attempts), max_retries + 1), "stop_reason": reason, "reflections": reflections}
