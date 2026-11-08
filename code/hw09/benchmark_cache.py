import asyncio
import json
from pathlib import Path
from statistics import mean

from semantic_cache import SemanticCache

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "reports/hw09/part2_benchmark.json"

CASES = [
    ("new", "What should a reader know about a clinical trial?"),
    ("exact", "What should a reader know about a clinical trial?"),
    ("paraphrase", "What are the main things to know before joining a clinical trial?"),
    ("new", "What does informed consent mean in a clinical trial?"),
    ("exact", "What does informed consent mean in a clinical trial?"),
    ("paraphrase", "Explain informed consent for clinical trial participants."),
    ("new", "What are the four phases of clinical trials?"),
    ("exact", "What are the four phases of clinical trials?"),
    ("new", "What is the role of a clinical trial sponsor?"),
    ("exact", "What is the role of a clinical trial sponsor?"),
]


async def main():
    print("Student: Haozhe Wang", flush=True)
    print("DATA 260 HW9 - Part 2 Benchmark", flush=True)
    print("Threshold: 0.85", flush=True)

    cache = SemanticCache(threshold=0.85)
    cache.clear_demo_cache()
    print("Demo cache cleared.", flush=True)

    results = []

    for number, (category, question) in enumerate(CASES, 1):
        print(f"\n===== QUERY {number}/10 =====", flush=True)
        print(f"Category: {category}", flush=True)
        print(f"Question: {question}", flush=True)

        result = await cache.answer(question)
        result["category"] = category
        result["query_number"] = number
        results.append(result)

        print(f"is_cached: {result['is_cached']}", flush=True)
        print(f"similarity: {result['similarity']}", flush=True)
        print(f"latency_ms: {result['latency_ms']}", flush=True)

        # Preserve partial results even if a later query fails.
        OUTPUT.write_text(
            json.dumps(results, indent=2, ensure_ascii=False)
        )

    hits = [r for r in results if r["is_cached"]]
    misses = [r for r in results if not r["is_cached"]]

    summary = {
        "total_queries": len(results),
        "cache_hits": len(hits),
        "cache_misses": len(misses),
        "hit_rate_percent": round(len(hits) / len(results) * 100, 2),
        "avg_hit_latency_ms": (
            round(mean(r["latency_ms"] for r in hits), 2)
            if hits else None
        ),
        "avg_miss_latency_ms": (
            round(mean(r["latency_ms"] for r in misses), 2)
            if misses else None
        ),
    }

    summary_path = ROOT / "reports/hw09/part2_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    print("\n========== FINAL PERFORMANCE ==========")
    for key, value in summary.items():
        print(f"{key}: {value}")

    assert len(results) == 10
    assert hits and misses
    assert all(not r["is_cached"] for r in results if r["query_number"] == 1)
    assert all(
        results[i]["is_cached"]
        for i in [1, 4, 7, 9]
    )

    print("PASS: 10 queries completed")
    print("PASS: Exact duplicate queries hit cache")
    print("=== PART 2 BENCHMARK COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(main())
