"""Offline assert-based runner for the Part 4 execute_tool entry point."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from domain_server import (  # noqa: E402
    Sponsor,
    Trial,
    get_trial_details_data,
    search_trials_data,
    summarize_sponsors_data,
)
from tool_executor import execute_tool  # noqa: E402
from agent_loop import MockModel, run_agent  # noqa: E402


TestFunction = Callable[[], None]


def parse_result(raw_result: str) -> dict:
    result = json.loads(raw_result)
    assert set(result) == {"ok", "data", "error"}
    return result


def build_fixture_handlers(database_path: str) -> dict:
    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    Sponsor.metadata.create_all(engine)
    fixture_session = sessionmaker(bind=engine)

    with fixture_session() as session:
        sponsor = Sponsor(
            name="Fixture Sponsor",
            contact_name="Fixture Contact",
            email="fixture@example.edu",
        )
        session.add(sponsor)
        session.flush()
        trial = Trial(
            brief_title="Fixture Diabetes Trial",
            nct_code="NCT85610001",
            participant_count=120,
            sponsor_id=sponsor.id,
        )
        session.add(trial)
        session.flush()
        detail_class = Trial.details.property.mapper.class_
        trial.details.append(detail_class(detail="Offline fixture detail"))
        session.commit()

    return {
        "search_trials": lambda **inputs: search_trials_data(
            **inputs,
            session_factory=fixture_session,
        ),
        "get_trial_details": lambda **inputs: get_trial_details_data(
            **inputs,
            session_factory=fixture_session,
        ),
        "summarize_sponsors": lambda **inputs: summarize_sponsors_data(
            **inputs,
            session_factory=fixture_session,
        ),
    }


def run_tests() -> None:
    with tempfile.TemporaryDirectory(prefix="hw5-part4-") as directory:
        database_path = os.path.join(directory, "fixtures.sqlite3")
        handlers = build_fixture_handlers(database_path)

        def search_valid() -> None:
            result = parse_result(
                execute_tool(
                    "search_trials",
                    {"query": "Diabetes", "limit": 5},
                    handlers=handlers,
                )
            )
            assert result["ok"] is True
            assert result["data"]["count"] == 1

        def search_invalid() -> None:
            result = parse_result(
                execute_tool(
                    "search_trials",
                    {"query": "Diabetes", "limit": 26},
                    handlers=handlers,
                )
            )
            assert result == {
                "ok": False,
                "data": None,
                "error": "limit must be an integer between 1 and 25",
            }

        def details_valid() -> None:
            result = parse_result(
                execute_tool(
                    "get_trial_details",
                    {"nct_code": "NCT85610001"},
                    handlers=handlers,
                )
            )
            assert result["ok"] is True
            assert result["data"]["sponsor"]["name"] == "Fixture Sponsor"

        def details_invalid() -> None:
            result = parse_result(
                execute_tool(
                    "get_trial_details",
                    {"nct_code": "BAD8561"},
                    handlers=handlers,
                )
            )
            assert result == {
                "ok": False,
                "data": None,
                "error": "nct_code must match NCT########",
            }

        def summary_valid() -> None:
            result = parse_result(
                execute_tool(
                    "summarize_sponsors",
                    {"min_trials": 5, "limit": 5},
                    handlers=handlers,
                )
            )
            assert result["ok"] is True
            assert result["data"]["count"] == 0

        def summary_invalid() -> None:
            result = parse_result(
                execute_tool(
                    "summarize_sponsors",
                    {"min_trials": 5001, "limit": 3},
                    handlers=handlers,
                )
            )
            assert result == {
                "ok": False,
                "data": None,
                "error": "min_trials must be an integer between 1 and 5000",
            }

        def unknown_tool() -> None:
            result = parse_result(
                execute_tool("delete_everything", {}, handlers=handlers)
            )
            assert result == {
                "ok": False,
                "data": None,
                "error": "unknown tool: delete_everything",
            }

        def handler_exception() -> None:
            def broken_handler(**inputs):
                del inputs
                raise RuntimeError("simulated internal failure")

            broken_handlers = {**handlers, "search_trials": broken_handler}
            result = parse_result(
                execute_tool(
                    "search_trials",
                    {"query": "Diabetes", "limit": 5},
                    handlers=broken_handlers,
                )
            )
            assert result == {
                "ok": False,
                "data": None,
                "error": "search_trials failed cleanly: RuntimeError",
            }

        def safety_rule_block() -> None:
            result = parse_result(
                execute_tool(
                    "summarize_sponsors",
                    {"min_trials": 1, "limit": 5},
                    handlers=handlers,
                )
            )
            assert result == {
                "ok": False,
                "data": None,
                "error": (
                    "safety rule: sponsor aggregates require min_trials "
                    "of at least 5"
                ),
            }

        def agent_stops_at_max_steps() -> None:
            model = MockModel(
                [
                    {
                        "type": "tool",
                        "name": "search_trials",
                        "inputs": {"query": "Fixture", "limit": 1},
                    },
                    {
                        "type": "tool",
                        "name": "search_trials",
                        "inputs": {"query": "Fixture", "limit": 1},
                    },
                    {"type": "final", "content": "This must not be reached."},
                ]
            )

            def fake_executor(name, inputs):
                del name, inputs
                return json.dumps({"ok": True, "data": [], "error": None})

            log_path = os.path.join(directory, "mock_agent_runs.jsonl")
            run = run_agent(
                "Keep searching until stopped.",
                model=model,
                max_steps=2,
                executor=fake_executor,
                log_path=__import__("pathlib").Path(log_path),
            )
            assert run["stop_reason"] == "max_steps"
            assert run["step_count"] == 2
            assert run["tool_call_count"] == 2

        tests: list[tuple[str, TestFunction]] = [
            ("search_trials valid input", search_valid),
            ("search_trials rejected input", search_invalid),
            ("get_trial_details valid input", details_valid),
            ("get_trial_details rejected input", details_invalid),
            ("summarize_sponsors valid input", summary_valid),
            ("summarize_sponsors rejected input", summary_invalid),
            ("unknown tool rejected", unknown_tool),
            ("handler exception contained", handler_exception),
            ("safety rule blocks small aggregate", safety_rule_block),
            ("MockModel stops at max_steps", agent_stops_at_max_steps),
        ]

        passed = 0
        for index, (name, test) in enumerate(tests, start=1):
            try:
                test()
            except Exception as error:  # noqa: BLE001 - report every test result
                print(f"FAIL {index}/{len(tests)} - {name}: {error}")
            else:
                passed += 1
                print(f"PASS {index}/{len(tests)} - {name}")

        print(f"Final summary: {passed}/{len(tests)} PASS")
        if passed != len(tests):
            raise SystemExit(1)


if __name__ == "__main__":
    print("HW5 Part 4 offline execute_tool tests")
    run_tests()
