from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise ValueError("invalid ObjectId")
    return ObjectId(value)


def serialize_document(doc: dict[str, Any]) -> dict[str, Any]:
    result = dict(doc)
    result["id"] = str(result.pop("_id"))
    return result

