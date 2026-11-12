from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

TRACE_LOG = Path(os.getenv("HW10_SPAN_LOG", "reports/hw10/data/spans.jsonl"))

def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def write_span(span: dict) -> None:
    TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(span, ensure_ascii=False, sort_keys=True) + "\n")

@contextmanager
def span(trace_id: str, stage: str, **metadata):
    started_wall = iso_now()
    started = time.perf_counter()
    status, error = "ok", None
    try:
        yield
    except Exception as exc:
        status, error = "error", repr(exc)
        raise
    finally:
        write_span({
            "trace_id": trace_id,
            "stage": stage,
            "start_time": started_wall,
            "end_time": iso_now(),
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "status": status,
            "error": error,
            **metadata,
        })

def write_queue_wait(trace_id: str, stage: str, produced_at: float, consumed_at: float) -> None:
    write_span({
        "trace_id": trace_id,
        "stage": stage,
        "start_time": datetime.fromtimestamp(produced_at, timezone.utc).isoformat(),
        "end_time": datetime.fromtimestamp(consumed_at, timezone.utc).isoformat(),
        "duration_ms": round((consumed_at - produced_at) * 1000, 3),
        "status": "ok",
        "error": None,
    })
