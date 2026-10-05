"""One safe JSON entry point for the three domain tools."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from domain_server import (
    failure,
    get_trial_details_data,
    search_trials_data,
    summarize_sponsors_data,
)


ToolHandler = Callable[..., dict[str, Any]]

DEFAULT_HANDLERS: dict[str, ToolHandler] = {
    "search_trials": search_trials_data,
    "get_trial_details": get_trial_details_data,
    "summarize_sponsors": summarize_sponsors_data,
}

MIN_SAFE_AGGREGATE_TRIALS = 5


def _json_response(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, sort_keys=True)


def execute_tool(
    name: str,
    inputs: Mapping[str, Any],
    *,
    handlers: Mapping[str, ToolHandler] | None = None,
) -> str:
    """Dispatch one domain tool and always return the shared envelope as JSON."""
    registry = DEFAULT_HANDLERS if handlers is None else handlers

    if not isinstance(name, str) or not name.strip():
        return _json_response(failure("tool name must be a non-empty string"))
    clean_name = name.strip()

    if not isinstance(inputs, Mapping):
        return _json_response(failure("inputs must be a JSON object"))
    if clean_name not in registry:
        return _json_response(failure(f"unknown tool: {clean_name}"))

    if clean_name == "summarize_sponsors":
        min_trials = inputs.get("min_trials", 1)
        if (
            isinstance(min_trials, int)
            and not isinstance(min_trials, bool)
            and min_trials < MIN_SAFE_AGGREGATE_TRIALS
        ):
            return _json_response(
                failure(
                    "safety rule: sponsor aggregates require min_trials "
                    f"of at least {MIN_SAFE_AGGREGATE_TRIALS}"
                )
            )

    try:
        result = registry[clean_name](**dict(inputs))
    except TypeError as error:
        return _json_response(failure(f"invalid inputs for {clean_name}: {error}"))
    except Exception as error:  # noqa: BLE001 - this boundary must never crash callers
        return _json_response(
            failure(
                f"{clean_name} failed cleanly: {type(error).__name__}"
            )
        )

    if not isinstance(result, dict) or set(result) != {"ok", "data", "error"}:
        return _json_response(
            failure(f"{clean_name} returned an invalid response envelope")
        )
    return _json_response(result)
