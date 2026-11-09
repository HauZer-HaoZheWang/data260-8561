import json
import sys
import time
import uuid
from pathlib import Path

from redis.commands.search.field import TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

sys.path.insert(0, str(Path(__file__).resolve().parent))
from semantic_cache import SemanticCache

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/hw09/part3_false_hit_actual.json"

SEED_QUESTION = "What is informed consent in a clinical trial?"
INCOMING_QUESTION = (
    "What is parental permission for a child in a clinical trial?"
)

CACHED_ANSWER = (
    "Informed consent is the process of explaining a clinical "
    "trial's purpose, procedures, risks, benefits, and participant "
    "rights so a person can voluntarily decide whether to join."
)

CORRECT_ANSWER = (
    "Parental permission means a parent or legally authorized "
    "guardian gives permission for a child to participate in "
    "research, subject to applicable rules. A child's assent "
    "may also be required when appropriate. Parental permission "
    "is not the same as an adult participant's informed consent."
)

THRESHOLD = 0.75


def main():
    print("Student: Haozhe Wang", flush=True)
    print("DATA 260 HW9 - Part 3.3 Actual False Hit")
    print("Case: C21 | Seed: S01 | Threshold: 0.75")

    cache = SemanticCache(threshold=THRESHOLD)

    seed_vector, seed_dim = cache.embed(SEED_QUESTION)
    query_vector, query_dim = cache.embed(INCOMING_QUESTION)
    assert seed_dim == query_dim

    token = uuid.uuid4().hex
    prefix = f"s8561:hw09:falsehit:{token}:doc:"
    index = f"s8561:hw09:falsehit:{token}:index"
    key = prefix + "seed"

    client = cache.redis
    index_created = False

    try:
        client.ft(index).create_index(
            [
                TextField("query"),
                TextField("answer"),
                VectorField(
                    "embedding",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": seed_dim,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
            ],
            definition=IndexDefinition(
                prefix=[prefix],
                index_type=IndexType.HASH,
            ),
        )
        index_created = True

        client.hset(
            key,
            mapping={
                "query": SEED_QUESTION,
                "answer": CACHED_ANSWER,
                "embedding": seed_vector,
            },
        )

        search_query = (
            Query("*=>[KNN 1 @embedding $vector AS distance]")
            .sort_by("distance")
            .return_fields("query", "answer", "distance")
            .dialect(2)
        )

        result = None
        for _ in range(30):
            result = client.ft(index).search(
                search_query,
                query_params={"vector": query_vector},
            )
            if result.docs:
                break
            time.sleep(0.1)

        if not result or not result.docs:
            raise RuntimeError("Redis did not index the cached answer")

        doc = result.docs[0]
        similarity = 1 - float(doc.distance)
        actual_answer = doc.answer

        if isinstance(actual_answer, bytes):
            actual_answer = actual_answer.decode("utf-8")

        cache_hit = similarity >= THRESHOLD
        assert cache_hit, (
            f"Expected false hit at {THRESHOLD}, "
            f"but similarity was {similarity:.6f}"
        )

        evidence = {
            "student": "Haozhe Wang",
            "case_id": "C21",
            "seed_id": "S01",
            "threshold": THRESHOLD,
            "incoming_question": INCOMING_QUESTION,
            "cached_question": SEED_QUESTION,
            "similarity": round(similarity, 6),
            "is_cached": cache_hit,
            "actual_cached_answer": actual_answer,
            "correct_reference_answer": CORRECT_ANSWER,
            "false_hit": True,
            "experiment_type": (
                "Controlled Redis FT.SEARCH using a temporary "
                "index and explicitly seeded reference answer"
            ),
        }

        OUT.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

        print("\n===== FALSE HIT RESULT =====")
        print(json.dumps(evidence, indent=2, ensure_ascii=False))
        print("\nPASS: Actual Redis cached answer retrieved")
        print("PASS: False hit reproduced at threshold 0.75")
        print("PASS: Correct reference answer documented")

    finally:
        client.delete(key)
        if index_created:
            client.ft(index).dropindex(
                delete_documents=False
            )
        print("PASS: Temporary Redis data cleaned")


if __name__ == "__main__":
    main()
