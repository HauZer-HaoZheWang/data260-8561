"""Run 50 intentionally unique questions and preserve raw latency evidence."""
from __future__ import annotations
import asyncio, json, sys, time, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hw09"))
from semantic_cache import SemanticCache

def questions():
    return [f"For clinical trial operations, explain the unique monitoring topic number {i}: {uuid.uuid4()}" for i in range(1, 51)]

async def main():
    out = Path(__file__).resolve().parents[2] / "reports/hw10/data/latency_experiment.jsonl"
    cache = SemanticCache(threshold=0.99)
    cache.clear_demo_cache()
    with out.open("w", encoding="utf-8") as f:
        for i, q in enumerate(questions(), 1):
            started = time.perf_counter()
            result = await cache.answer(q)
            total = (time.perf_counter() - started) * 1000
            row = {"request_id": f"miss-{i:02d}", "trace_id": result.get("trace_id"), "cache_threshold": 0.99, "cache_hit": bool(result.get("is_cached")),
                   "question": q, "total_ms": round(total, 3),
                   "cache_lookup_ms": result.get("cache_lookup_ms"),
                   "planner_ms": result.get("planner_ms"), "writer_ms": result.get("writer_ms"),
                   "reviewer_ms": result.get("reviewer_ms"), "queue_wait_ms": result.get("queue_wait_ms"),
                   "evaluation_ms": result.get("evaluation_ms")}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(json.dumps({"i": i, "cache_hit": row["cache_hit"], "total_ms": row["total_ms"]}))

if __name__ == "__main__": asyncio.run(main())
