import json
import os
import uuid
from typing import Any

PREFIX = os.getenv("PREFIX", "s8561")
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
PORT = int(os.getenv("PORT_BASE", "8461"))
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

REQUESTS = f"{PREFIX}_trial_requests"
RESPONSES = f"{PREFIX}_trial_responses"
INBOX = f"{PREFIX}_inbox"
TASKS = f"{PREFIX}_tasks"
DRAFTS = f"{PREFIX}_drafts"
FINAL = f"{PREFIX}_final"
DLQ = f"{PREFIX}_dead_letter"


def correlation_id() -> str:
    return str(uuid.uuid4())


def dumps(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def loads(value: bytes) -> dict[str, Any]:
    result = json.loads(value.decode())
    if not isinstance(result, dict):
        raise ValueError("message must be a JSON object")
    return result


def validate_trial(data: dict[str, Any]) -> str | None:
    required = ("brief_title", "nct_code", "participant_count", "sponsor_id")
    missing = [field for field in required if field not in data]
    if missing:
        return "missing required fields: " + ", ".join(missing)
    if not isinstance(data["brief_title"], str) or not data["brief_title"].strip():
        return "brief_title must be non-empty"
    if not isinstance(data["nct_code"], str) or not __import__("re").fullmatch(r"NCT\d{8}", data["nct_code"]):
        return "nct_code must match NCT########"
    if not isinstance(data["participant_count"], int) or data["participant_count"] < 0:
        return "participant_count must be a non-negative integer"
    if not isinstance(data["sponsor_id"], int) or data["sponsor_id"] <= 0:
        return "sponsor_id must be a positive integer"
    return None
