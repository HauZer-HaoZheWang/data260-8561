"""Capture machine-readable Part 2 MCP calls for the HW5 raw-data folder."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "reports" / "hw05" / "raw" / "mcp_inspector_outputs.json"


def serializable_result(result: Any) -> dict[str, Any]:
    return {
        "is_error": bool(result.isError),
        "structured_content": result.structuredContent,
        "content": [item.model_dump(mode="json") for item in result.content],
    }


async def capture_server(
    server_file: str,
    calls: list[tuple[str, str, dict[str, Any]]],
) -> dict[str, Any]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "code" / "mcp" / server_file)],
    )
    captured: list[dict[str, Any]] = []

    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await asyncio.wait_for(session.initialize(), timeout=15)
            tools = await asyncio.wait_for(session.list_tools(), timeout=15)
            for label, tool_name, inputs in calls:
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, inputs),
                    timeout=30,
                )
                captured.append(
                    {
                        "label": label,
                        "tool": tool_name,
                        "inputs": inputs,
                        "result": serializable_result(result),
                    }
                )

    return {
        "server_file": server_file,
        "registered_tools": sorted(tool.name for tool in tools.tools),
        "calls": captured,
    }


async def main() -> None:
    meals_calls = [
        ("search success", "search_meals_by_name", {"query": "Arrabiata", "limit": 2}),
        ("ingredient success", "meals_by_ingredient", {"ingredient": "chicken", "limit": 2}),
        ("random success", "random_meal", {}),
        ("details success", "meal_details", {"id": "52772"}),
    ]
    domain_calls = [
        ("search success", "search_trials", {"query": "Seeded Clinical Trial 1", "limit": 2}),
        ("search invalid", "search_trials", {"query": "Seeded Clinical Trial 1", "limit": 26}),
        ("detail success", "get_trial_details", {"nct_code": "NCT00000005"}),
        ("detail invalid", "get_trial_details", {"nct_code": "BAD8561"}),
        ("summary success", "summarize_sponsors", {"min_trials": 100, "limit": 2}),
        ("summary invalid", "summarize_sponsors", {"min_trials": 5001, "limit": 3}),
    ]

    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "Machine-readable copies of the inputs and outputs demonstrated in MCP Inspector.",
        "servers": [
            await capture_server("meals_server.py", meals_calls),
            await capture_server("domain_server.py", domain_calls),
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print("MCP servers captured: 2")
    print("MCP tool calls captured: 10")
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
