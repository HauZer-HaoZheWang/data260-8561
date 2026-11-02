import json
import os
import requests
from common import MODEL


def ask_ollama(prompt: str) -> str:
    response = requests.post(
        os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate"),
        json={"model": MODEL, "prompt": prompt, "stream": False}, timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def log(stage, message):
    print(json.dumps({"stage": stage, **message}, sort_keys=True))
