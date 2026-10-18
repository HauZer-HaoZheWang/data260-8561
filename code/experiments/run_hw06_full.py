"""Run all HW6 Part 3 settings with fresh users and isolated server configs."""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "reports" / "hw06" / "raw"
LOG = ROOT / "reports" / "hw06" / "RUN_LOG.txt"
BASE_URL = "http://127.0.0.1:8461"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

CONVERSATION = [
    "The trial project studies diabetes interventions.",
    "The primary domain is clinical-trial listings.",
    "The project uses NCT identifiers for studies.",
    "The API runs locally for reproducible experiments.",
    "The student prefers concise evidence-based answers.",
    "The database should preserve facts across sessions.",
    "The model is served locally through Ollama.",
    "The current model is qwen3:8b.",
    "The MongoDB database is s8561_doc.",
    "The application port is 8461.",
    "The assigned domain id is 1.",
    "The SID4 is 8561.",
    "The repository is data260-8561.",
    "Prior homework reports must remain intact.",
    "The FastAPI layer uses Pydantic validation.",
    "MongoDB stores messages, summaries, and episodes.",
    "Short-term memory is a sliding window.",
    "Long-term memory is stored as summaries.",
    "Episodic memory stores short facts and embeddings.",
    "Cosine similarity ranks episodic facts.",
    "The chat endpoint returns memory evidence.",
    "The aggregate endpoint groups messages by date.",
    "The memory endpoint returns recent records.",
    "The experiment uses fresh sessions for each setting.",
    "The experiment records prompt tokens.",
    "The experiment records completion tokens.",
    "The experiment records latency.",
    "The experiment uses five fixed probes.",
    "The report explains the best and worst settings.",
    "The final state receives the hw6 tag.",
]

PROBES = [
    ("What is the project domain?", ["clinical", "trial"]),
    ("What local model is required?", ["qwen3:8b"]),
    ("What MongoDB database should memory use?", ["s8561_doc"]),
    ("Which port does the application use?", ["8461"]),
    ("What must be preserved when adding HW6?", ["repository", "history"]),
]


def log(message: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {message}"
    print(line, flush=True)


def post(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def wait_for_server() -> None:
    for _ in range(120):
        try:
            with urllib.request.urlopen(BASE_URL + "/health", timeout=3) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(1)
    raise RuntimeError("Uvicorn did not become ready within 120 seconds")


def start_server(short_term_n: int, compression: bool):
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT / "code"),
        "SHORT_TERM_N": str(short_term_n),
        "MEMORY_COMPRESSION": "1" if compression else "0",
        "MONGODB_DB": "s8561_doc",
        "OLLAMA_MODEL": "qwen3:8b",
        "OLLAMA_EMBED_MODEL": "nomic-embed-text",
    })
    server_log = LOG.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "memory_application.main:app", "--host", "127.0.0.1", "--port", "8461"],
        cwd=ROOT,
        env=env,
        stdout=server_log,
        stderr=subprocess.STDOUT,
    )
    wait_for_server()
    return process, server_log


def stop_server(process, server_log) -> None:
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    server_log.close()


def run_setting(label: str, short_term_n: int, compression: bool) -> dict:
    user_id = f"hw6-exp-{label.lower().replace('=', '-').replace('+', '-')}-{STAMP}"
    session_id = f"{label}-{STAMP}"
    log(f"START {label} user_id={user_id} session_id={session_id}")
    process, server_log = start_server(short_term_n, compression)
    turns = []
    try:
        for index, message in enumerate(CONVERSATION, 1):
            result = post("/api/chat", {"user_id": user_id, "session_id": session_id, "message": message})
            turns.append({"turn": index, "message": message, "metrics": result["metrics"]})
            log(f"{label} turn={index:02d}/30 prompt_tokens={result['metrics'].get('prompt_tokens')} latency_ms={result['metrics'].get('latency_ms')}")
        probes = []
        for question, criteria in PROBES:
            result = post("/api/chat", {"user_id": user_id, "session_id": session_id, "message": question})
            answer = result["reply"]
            hits = sum(1 for criterion in criteria if criterion.lower() in answer.lower())
            score = round(1 + 4 * hits / len(criteria), 2)
            probes.append({"question": question, "answer": answer, "criteria": criteria, "score": score})
            log(f"{label} probe={question!r} score={score}")
        prompt_values = [row["metrics"].get("prompt_tokens", 0) for row in turns]
        completion_values = [row["metrics"].get("completion_tokens", 0) for row in turns]
        latency_values = [row["metrics"].get("latency_ms", 0) for row in turns]
        result = {
            "label": label,
            "short_term_n": short_term_n,
            "compression": compression,
            "user_id": user_id,
            "session_id": session_id,
            "turns": turns,
            "probes": probes,
            "summary": {
                "mean_prompt_tokens": round(statistics.mean(prompt_values), 2),
                "mean_completion_tokens": round(statistics.mean(completion_values), 2),
                "mean_latency_ms": round(statistics.mean(latency_values), 2),
                "mean_probe_score": round(statistics.mean(row["score"] for row in probes), 2),
            },
        }
        (RAW / f"{label.replace('+', '_')}_{STAMP}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        log(f"DONE {label} summary={result['summary']}")
        return result
    finally:
        stop_server(process, server_log)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    log(f"HW6 Part 3 started; SEED=8561; VERIFY_SEED=268561; timestamp={STAMP}")
    settings = [
        ("N4", 4, False),
        ("N12", 12, False),
        ("N30", 30, False),
        ("N30+compression", 30, True),
    ]
    results = []
    for label, n, compression in settings:
        results.append(run_setting(label, n, compression))
    combined = RAW / f"memory_experiments_{STAMP}.json"
    combined.write_text(json.dumps(results, indent=2), encoding="utf-8")
    log(f"ALL SETTINGS COMPLETE; combined_file={combined}")
    print(json.dumps([{"label": row["label"], **row["summary"]} for row in results], indent=2), flush=True)


if __name__ == "__main__":
    main()
