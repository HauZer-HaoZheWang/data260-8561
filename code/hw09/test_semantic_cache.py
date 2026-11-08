import asyncio
import json

from semantic_cache import SemanticCache


async def main():
    print("Student: Haozhe Wang")
    print("Homework: DATA 260 HW9")
    print("Part 2: Semantic Cache Test")

    cache = SemanticCache(threshold=0.85)

    question = "What should a reader know about a clinical trial?"

    print("\n===== FIRST QUERY: CACHE MISS =====")
    cache.clear_demo_cache()

    first = await cache.answer(question)

    print(json.dumps(first, indent=2, ensure_ascii=False))

    assert first["is_cached"] is False
    assert first["answer"]

    print("\n===== SECOND QUERY: CACHE HIT =====")

    second = await cache.answer(question)

    print(json.dumps(second, indent=2, ensure_ascii=False))

    assert second["is_cached"] is True
    assert second["similarity"] >= 0.85
    assert second["answer"] == first["answer"]

    print("\n===== TEST RESULT =====")
    print("PASS: Cache miss used HW8 agent")
    print("PASS: Cache hit reused stored answer")
    print("PASS: Redis semantic search works")
    print("=== PART 2 SMOKE TEST COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(main())
