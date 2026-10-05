"""Objective HW5 smoke test that writes reports/hw05/verification.json."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports" / "hw05"
OUTPUT = REPORT_DIR / "verification.json"
SID4 = 8561
PORT_BASE = 8000 + (SID4 % 900)
SEED = SID4
VERIFY_SEED = 260000 + SID4
MODEL = "qwen3:8b"


def git_value(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True
    ).strip()


def check(name: str, operation: Callable[[], str]) -> dict[str, Any]:
    try:
        detail = operation()
        print(f"PASS - {name}: {detail}")
        return {"name": name, "passed": True, "detail": detail}
    except Exception as error:  # noqa: BLE001 - smoke-test boundary
        detail = f"{type(error).__name__}: {error}"
        print(f"FAIL - {name}: {detail}")
        return {"name": name, "passed": False, "detail": detail}


async def inspect_server(server_file: str, expected: set[str]) -> str:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "code" / "mcp" / server_file)],
    )
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await asyncio.wait_for(session.initialize(), timeout=15)
            listed = await asyncio.wait_for(session.list_tools(), timeout=15)
            names = {tool.name for tool in listed.tools}
            if names != expected:
                raise AssertionError(f"tools={sorted(names)}")
    return ", ".join(sorted(expected))


def backend_health() -> str:
    with urlopen(f"http://127.0.0.1:{PORT_BASE}/health", timeout=5) as response:
        payload = json.load(response)
    if response.status != 200 or payload.get("status") != "ok":
        raise AssertionError(payload)
    return json.dumps(payload, sort_keys=True)


def raw_retry_data() -> str:
    csv_path = REPORT_DIR / "raw" / "retry_experiment.csv"
    rows = csv_path.read_text(encoding="utf-8").splitlines()
    if len(rows) != 151:
        raise AssertionError(f"expected 150 data rows, found {len(rows) - 1}")
    return "150 experiment rows"


def agent_log() -> str:
    runs = [
        json.loads(line)
        for line in (REPORT_DIR / "agent_runs.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    if len(runs) != 4:
        raise AssertionError(f"expected 4 runs, found {len(runs)}")
    reasons = [run["stop_reason"] for run in runs]
    if reasons != [
        "normal_completion",
        "normal_completion",
        "normal_completion",
        "safety_rule_block",
    ]:
        raise AssertionError(reasons)
    if any(run["tool_call_count"] != 1 for run in runs):
        raise AssertionError("each run must contain exactly one tool call")
    return "4 runs; 3 normal completions and 1 safety block"


def offline_tests() -> str:
    result = subprocess.run(
        [sys.executable, "code/mcp/test_tool_executor.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    if "Final summary: 10/10 PASS" not in result.stdout:
        raise AssertionError(result.stdout[-500:])
    return "10/10 PASS"


def required_artifacts() -> str:
    required = [
        "reports/hw05/AI_USE.md",
        "reports/hw05/RUN_LOG.txt",
        "reports/hw05/METRICS.md",
        "reports/hw05/REFLECTION.md",
        "reports/hw05/raw/retry_experiment.csv",
        "reports/hw05/raw/retry_summary.json",
        "reports/hw05/raw/mcp_inspector_outputs.json",
        "reports/hw05/agent_runs.jsonl",
        "reports/hw05/report.pdf",
        "reports/hw05/Wang_HW5.pdf",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing: {missing}")
    return f"{len(required)}/{len(required)} files"


def screenshots() -> str:
    screenshot_dir = REPORT_DIR / "screenshots"
    count = len(list(screenshot_dir.glob("*.png")))
    if count < 30:
        raise AssertionError(f"expected at least 30 PNG files, found {count}")
    return f"{count} PNG files"


def main() -> None:
    print(f"HW5 smoke test started: {datetime.now(timezone.utc).isoformat()}")
    checks = [
        check("FastAPI health", backend_health),
        check(
            "Meals MCP tools",
            lambda: asyncio.run(
                inspect_server(
                    "meals_server.py",
                    {
                        "search_meals_by_name",
                        "meals_by_ingredient",
                        "random_meal",
                        "meal_details",
                    },
                )
            ),
        ),
        check(
            "Domain MCP tools",
            lambda: asyncio.run(
                inspect_server(
                    "domain_server.py",
                    {
                        "search_trials",
                        "get_trial_details",
                        "summarize_sponsors",
                    },
                )
            ),
        ),
        check("Offline tool and agent tests", offline_tests),
        check("Retry raw data", raw_retry_data),
        check("Agent run log", agent_log),
        check("Screenshots", screenshots),
        check("Required artifacts", required_artifacts),
    ]
    payload = {
        "homework": 5,
        "sid4": SID4,
        "commit_hash": git_value("rev-parse", "HEAD"),
        "branch": git_value("branch", "--show-current"),
        "model": MODEL,
        "configuration": {
            "port_base": PORT_BASE,
            "prefix": f"s{SID4}",
            "seed": SEED,
            "verify_seed": VERIFY_SEED,
            "domain_id": SID4 % 8,
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Overall status: {payload['status']}")
    print(f"Saved: {OUTPUT}")
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
