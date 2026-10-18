from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from model_client import complete  # noqa: E402


def ask(messages: list[dict[str, str]]) -> dict:
    return complete(messages)
