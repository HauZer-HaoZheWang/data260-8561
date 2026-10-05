"""Show one allowed and one blocked Part 5 safety-rule call."""

from __future__ import annotations

import json

from tool_executor import execute_tool


def main() -> None:
    allowed = json.loads(
        execute_tool(
            "summarize_sponsors",
            {"min_trials": 100, "limit": 2},
        )
    )
    blocked = json.loads(
        execute_tool(
            "summarize_sponsors",
            {"min_trials": 1, "limit": 2},
        )
    )

    assert allowed["ok"] is True
    assert blocked == {
        "ok": False,
        "data": None,
        "error": "safety rule: sponsor aggregates require min_trials of at least 5",
    }

    print("HW5 Part 5 safety-rule demonstration")
    print("ALLOWED CALL (min_trials=100):")
    print(json.dumps(allowed, ensure_ascii=False))
    print("BLOCKED CALL (min_trials=1):")
    print(json.dumps(blocked, ensure_ascii=False))
    print("Safety-rule demonstration: 2/2 PASS")


if __name__ == "__main__":
    main()
