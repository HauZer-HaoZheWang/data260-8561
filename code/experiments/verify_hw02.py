from __future__ import annotations

import json
import multiprocessing
import os
import subprocess
import sys
import time
from pathlib import Path
from queue import Empty
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parents[2]
CODE_DIR = PROJECT_DIR / "code"
WEB_DIR = CODE_DIR / "web_application"

sys.path.insert(0, str(CODE_DIR))


SID4 = "8561"
PORT_BASE = 8461
SEED = 8561
VERIFY_SEED = 268561
MODEL = "qwen3:8b"

GRAPH_MAX_TURNS = 6
GRAPH_TIMEOUT_SECONDS = 180

CASE_PATH = (
    PROJECT_DIR
    / "reports"
    / "hw02"
    / "cases"
    / "schema_input.json"
)

OUT_PATH = (
    PROJECT_DIR
    / "reports"
    / "hw02"
    / "verification.json"
)

API_BASE_URL = f"http://127.0.0.1:{PORT_BASE}"


def get_commit_hash() -> str:
    """Read the current commit from git, so the report and the code agree."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )

    return result.stdout.strip()


def start_api_server() -> subprocess.Popen:
    #Start uvicorn from web_application so static path works.
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT_BASE),
        ],
        cwd=WEB_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    #Give uvicorn two seconds to start
    time.sleep(2)

    #Stop verification if the new server already crashed.
    if process.poll() is not None:
        raise RuntimeError(
            "Uvicorn stopped before the API check started."
        )

    return process


def stop_api_server(process: subprocess.Popen | None) -> None:
    #Do nothing if server was not started.
    if process is None:
        return

    #Ask uvicorn to stop.
    if process.poll() is None:
        process.terminate()

        try:
            process.wait(timeout=5)

        #Force stop if normal terminate takes too long
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def send_json_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None
) -> tuple[int, Any]:
    #Change Python dictionary into JSON bytes when body exists
    request_data = None

    if body is not None:
        request_data = json.dumps(body).encode("utf-8")

    headers = {
        "Accept": "application/json"
    }

    if body is not None:
        headers["Content-Type"] = "application/json"

    request = Request(
        url=API_BASE_URL + path,
        data=request_data,
        headers=headers,
        method=method
    )

    #Send request and read the response
    with urlopen(request, timeout=10) as response:
        status_code = response.status
        response_text = response.read().decode("utf-8")

    #Some endpoints may return an empty response.
    response_json = (
        json.loads(response_text)
        if response_text
        else None
    )

    return status_code, response_json


def check_api() -> dict[str, Any]:
    server = None

    try:
        #Start FastAPI in a separate process
        server = start_api_server()

        #Request the trial list.
        status_code, data = send_json_request(
            "GET",
            "/api/trials"
        )

        passed = (
            status_code == 200
            and isinstance(data, list)
        )

        return {
            "name": "FastAPI responds on port 8461",
            "passed": passed,
            "detail": (
                f"GET /api/trials returned HTTP {status_code} "
                f"and {len(data) if isinstance(data, list) else 0} trials."
            )
        }

    except (HTTPError, URLError, OSError, RuntimeError) as error:
        return {
            "name": "FastAPI responds on port 8461",
            "passed": False,
            "detail": f"{type(error).__name__}: {error}"
        }

    finally:
        #Always stop uvicorn after the check
        stop_api_server(server)


def check_crud() -> dict[str, Any]:
    server = None
    created_id = None

    try:
        #Start a clean FastAPI process for CRUD check.
        server = start_api_server()

        #Count trials before creating a new one
        before_status, before_trials = send_json_request(
            "GET",
            "/api/trials"
        )

        if before_status != 200 or not isinstance(before_trials, list):
            raise RuntimeError(
                "Could not read the original trial list."
            )

        before_count = len(before_trials)

        #Create one temporary trial
        create_status, created_trial = send_json_request(
            "POST",
            "/api/trials",
            {
                "brief_title": "Temporary Verification Trial",
                "sponsor": "HW02 Verification Script"
            }
        )

        if create_status != 201:
            raise RuntimeError(
                f"POST returned HTTP {create_status}."
            )

        if not isinstance(created_trial, dict):
            raise RuntimeError(
                "POST did not return a trial object."
            )

        created_id = created_trial.get("id")

        if not isinstance(created_id, int):
            raise RuntimeError(
                "Created trial did not have an integer id."
            )

        #Read list again and confirm one trial was added.
        list_status, after_trials = send_json_request(
            "GET",
            "/api/trials"
        )

        if list_status != 200 or not isinstance(after_trials, list):
            raise RuntimeError(
                "Could not read trials after POST."
            )

        count_increased = len(after_trials) == before_count + 1

        created_trial_exists = any(
            isinstance(trial, dict)
            and trial.get("id") == created_id
            for trial in after_trials
        )

        if not count_increased or not created_trial_exists:
            raise RuntimeError(
                "POST result was not found in the updated trial list."
            )

        #Delete the temporary trial
        delete_status, _ = send_json_request(
            "DELETE",
            f"/api/trials/{created_id}"
        )

        if delete_status != 200:
            raise RuntimeError(
                f"DELETE returned HTTP {delete_status}."
            )

        #Mark it cleaned so finally does not delete again
        deleted_id = created_id
        created_id = None

        return {
            "name": "CRUD create, list and delete",
            "passed": True,
            "detail": (
                f"Created trial {deleted_id}, confirmed the list "
                "increased by one, then deleted the temporary trial."
            )
        }

    except (
        HTTPError,
        URLError,
        OSError,
        RuntimeError,
        ValueError
    ) as error:
        return {
            "name": "CRUD create, list and delete",
            "passed": False,
            "detail": f"{type(error).__name__}: {error}"
        }

    finally:
        #Try to clean temporary data if an earlier step failed.
        if server is not None and created_id is not None:
            try:
                send_json_request(
                    "DELETE",
                    f"/api/trials/{created_id}"
                )
            except Exception:
                pass

        #Always stop uvicorn after the check
        stop_api_server(server)


def graph_worker(result_queue: multiprocessing.Queue) -> None:
    #Run LangGraph inside a child process, so timeout can stop it.
    try:
        os.environ["MAX_TURNS"] = str(GRAPH_MAX_TURNS)
        os.environ["SEED"] = str(SEED)
        os.environ["VERIFY_SEED"] = str(VERIFY_SEED)

        from graph.state import initialize_state
        from graph.workflow import build_workflow

        #Read the fixed verification input.
        with CASE_PATH.open(
            "r",
            encoding="utf-8"
        ) as case_file:
            case_data = json.load(case_file)

        #Create a fresh state for verification
        initial_state = initialize_state(
            title=case_data.get("title", ""),
            content=case_data.get("content", ""),
            email=case_data.get("email", ""),
            strict=case_data.get("strict", False),
            task=case_data.get("task", "")
        )

        app = build_workflow()
        final_state = app.invoke(initial_state)

        result_queue.put({
            "ok": True,
            "final_state": final_state
        })

    except Exception as error:
        result_queue.put({
            "ok": False,
            "error_type": type(error).__name__,
            "error_message": str(error)
        })


def check_graph(
    graph_result: dict[str, Any]
) -> dict[str, Any]:
    process = None

    try:
        #Use spawn so this works correctly on macOS.
        context = multiprocessing.get_context("spawn")
        result_queue = context.Queue()

        process = context.Process(
            target=graph_worker,
            args=(result_queue,)
        )

        process.start()

        #Wait for graph result until timeout
        deadline = time.time() + GRAPH_TIMEOUT_SECONDS
        worker_result = None

        while time.time() < deadline:
            try:
                worker_result = result_queue.get_nowait()
                break
            except Empty:
                #Stop waiting early if child process crashed.
                if not process.is_alive():
                    break

                time.sleep(0.2)

        #No result means graph timed out or child process crashed.
        if worker_result is None:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)

                return {
                    "name": "LangGraph terminates within timeout",
                    "passed": False,
                    "detail": (
                        "Graph did not finish within "
                        f"{GRAPH_TIMEOUT_SECONDS} seconds."
                    )
                }

            return {
                "name": "LangGraph terminates within timeout",
                "passed": False,
                "detail": (
                    "Graph process stopped without returning a result."
                )
            }

        process.join(timeout=5)

        #Worker returned an error.
        if not worker_result.get("ok"):
            return {
                "name": "LangGraph terminates within timeout",
                "passed": False,
                "detail": (
                    f"{worker_result.get('error_type')}: "
                    f"{worker_result.get('error_message')}"
                )
            }

        final_state = worker_result.get("final_state")

        if not isinstance(final_state, dict):
            return {
                "name": "LangGraph terminates within timeout",
                "passed": False,
                "detail": "Graph did not return a final state dictionary."
            }

        #Save result for the tag count check.
        graph_result["final_state"] = final_state

        return {
            "name": "LangGraph terminates within timeout",
            "passed": True,
            "detail": (
                "Graph returned a final state within "
                f"{GRAPH_TIMEOUT_SECONDS} seconds."
            )
        }

    except Exception as error:
        return {
            "name": "LangGraph terminates within timeout",
            "passed": False,
            "detail": f"{type(error).__name__}: {error}"
        }

    finally:
        #Always stop the graph worker if it is still running
        if process is not None and process.is_alive():
            process.terminate()
            process.join(timeout=5)


def check_tag_count(
    graph_result: dict[str, Any]
) -> dict[str, Any]:
    try:
        #Use the final state returned by check_graph
        final_state = graph_result.get("final_state")

        if not isinstance(final_state, dict):
            raise RuntimeError(
                "Graph result is not available."
            )

        proposal = final_state.get("planner_proposal")

        if not isinstance(proposal, dict):
            raise RuntimeError(
                "planner_proposal is not a dictionary."
            )

        data = proposal.get("data")

        if not isinstance(data, dict):
            raise RuntimeError(
                "planner_proposal data is not a dictionary."
            )

        tags = data.get("tags")

        #Check behavior, not the exact tag wording.
        passed = (
            isinstance(tags, list)
            and len(tags) == 3
            and all(isinstance(tag, str) for tag in tags)
        )

        tag_count = len(tags) if isinstance(tags, list) else 0

        return {
            "name": "Planner returns exactly three string tags",
            "passed": passed,
            "detail": (
                f"Planner returned {tag_count} tags; "
                f"all_string_tags={passed if tag_count == 3 else False}."
            )
        }

    except Exception as error:
        return {
            "name": "Planner returns exactly three string tags",
            "passed": False,
            "detail": f"{type(error).__name__}: {error}"
        }


def main() -> None:
    checks: list[dict[str, Any]] = []

    #Run API response check
    api_check = check_api()
    checks.append(api_check)
    print(api_check)

    #Run CRUD behavior check.
    crud_check = check_crud()
    checks.append(crud_check)
    print(crud_check)

    #Keep graph final state for the next check
    graph_result: dict[str, Any] = {}

    #Run graph termination check.
    graph_check = check_graph(graph_result)
    checks.append(graph_check)
    print(graph_check)

    #Check tag count without running the graph again
    tag_check = check_tag_count(graph_result)
    checks.append(tag_check)
    print(tag_check)

    #Create the verification report.
    verification = {
        "homework_number": "HW02",
        "sid4": SID4,
        "commit_hash": get_commit_hash(),
        "model": MODEL,
        "model_config": {
            "settings_source": "src/model_client.py",
            "api_port": PORT_BASE,
            "graph_max_turns": GRAPH_MAX_TURNS,
            "graph_timeout_seconds": GRAPH_TIMEOUT_SECONDS
        },
        "SEED": SEED,
        "VERIFY_SEED": VERIFY_SEED,
        "checks": checks,
        "all_passed": all(
            check.get("passed") is True
            for check in checks
        )
    }

    #Create reports/hw02 if it does not exist.
    OUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    #Write verification.json
    with OUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as output_file:
        json.dump(
            verification,
            output_file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "Verification finished. "
        f"Result saved to {OUT_PATH}"
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()