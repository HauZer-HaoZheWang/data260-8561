"""Run the reproducible HW6 SHORT_TERM_N sweep against a running local API."""

from __future__ import annotations

import json
import os
import statistics
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "reports" / "hw06" / "raw"
BASE_URL = os.getenv("HW6_BASE_URL", "http://127.0.0.1:8461")
USER_ID = os.getenv("HW6_EXPERIMENT_USER", "hw6-experiment-8561")

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


def post(path: str, payload: dict) -> dict:
    request = urllib.request.Request(BASE_URL + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def run_setting(setting: str, compression: bool = False) -> dict:
    session = f"{setting}-{'compressed' if compression else 'baseline'}-{int(time.time())}"
    turns = []
    for message in CONVERSATION:
        result = post("/api/chat", {"user_id": USER_ID, "session_id": session, "message": message})
        turns.append({"message": message, "metrics": result["metrics"]})
    probe_rows = []
    for question, criteria in PROBES:
        result = post("/api/chat", {"user_id": USER_ID, "session_id": session, "message": question})
        answer = result["reply"].lower()
        hits = sum(1 for item in criteria if item.lower() in answer)
        probe_rows.append({"question": question, "answer": result["reply"], "score": round(1 + 4 * hits / len(criteria), 2)})
    prompt_values = [row["metrics"].get("prompt_tokens", 0) for row in turns]
    latency_values = [row["metrics"].get("latency_ms", 0) for row in turns]
    return {"setting": setting, "compression": compression, "session_id": session, "turns": turns, "probes": probe_rows, "summary": {"mean_prompt_tokens": statistics.mean(prompt_values), "mean_latency_ms": statistics.mean(latency_values), "mean_probe_score": statistics.mean(row["score"] for row in probe_rows)}}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    results = [run_setting(f"SHORT_TERM_N={n}") for n in (4, 12, 30)]
    results.append(run_setting("compression", compression=True))
    (RAW / "memory_experiments.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps([{"setting": row["setting"], **row["summary"]} for row in results], indent=2))


if __name__ == "__main__":
    main()
