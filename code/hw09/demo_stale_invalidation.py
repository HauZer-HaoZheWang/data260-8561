import hashlib
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cache_db import TrialCacheDB
from semantic_cache import SemanticCache


def read_trial(db, trial_id):
    with db.engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id, briefTitle, participant_count "
                "FROM trials WHERE id = :id"
            ),
            {"id": trial_id},
        ).mappings().one()
    return dict(row)


def version_of(row):
    payload = json.dumps(
        {
            "id": row["id"],
            "briefTitle": row["briefTitle"],
            "participant_count": row["participant_count"],
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def answer_from_db(row):
    return (
        f"Trial {row['id']}: {row['briefTitle']}. "
        f"Participant count: {row['participant_count']}."
    )


def main():
    print("Student: Haozhe Wang", flush=True)
    print("DATA 260 HW9 - Part 3 Stale Answer and Invalidation")

    db = TrialCacheDB()
    cache = SemanticCache(threshold=0.85)

    with db.engine.connect() as conn:
        trial_id = conn.execute(
            text("SELECT id FROM trials ORDER BY id LIMIT 1")
        ).scalar_one_or_none()

    if trial_id is None:
        raise RuntimeError("No trial records found")

    original = read_trial(db, trial_id)
    old_count = int(original["participant_count"])
    new_count = old_count + 1

    # Unique query prevents interference from earlier experiments.
    token = uuid.uuid4().hex[:12]
    question = (
        f"Database trial {trial_id} participant count "
        f"verification {token}"
    )

    vector, dimension = cache.embed(question)
    cache.ensure_index(dimension)

    cached_keys = []
    database_changed = False

    try:
        print("\n===== STEP 1: ORIGINAL DATABASE =====")
        print(f"trial_id: {trial_id}")
        print(f"participant_count: {old_count}")

        old_version = version_of(original)
        old_answer = answer_from_db(original)

        old_key = cache.store(
            question, old_answer, vector, old_version
        )
        cached_keys.append(old_key)

        print(f"Original data version: {old_version}")
        print("PASS: Stored database-grounded answer in Redis")

        print("\n===== STEP 2: MODIFY MYSQL RECORD =====")

        with db.engine.begin() as conn:
            result = conn.execute(
                text(
                    "UPDATE trials "
                    "SET participant_count = :new_count "
                    "WHERE id = :trial_id "
                    "AND participant_count = :old_count"
                ),
                {
                    "new_count": new_count,
                    "trial_id": trial_id,
                    "old_count": old_count,
                },
            )
            if result.rowcount != 1:
                raise RuntimeError("Trial changed concurrently")

        database_changed = True
        updated = read_trial(db, trial_id)

        assert updated["participant_count"] == new_count

        print(f"Updated participant_count: {new_count}")
        print("PASS: MySQL record changed")

        print("\n===== STEP 3: DEMONSTRATE STALE ANSWER =====")

        stale_match = cache.search(vector)
        assert stale_match is not None
        assert stale_match["answer"] == old_answer

        print(f"Redis cached answer: {stale_match['answer']}")
        print(f"Current MySQL count: {new_count}")
        print(f"Cached data version: {stale_match['data_version']}")
        print("PASS: Redis still contains the old answer")
        print("STALE ANSWER DETECTED")

        print("\n===== STEP 4: VERSION CHECK =====")

        new_version = version_of(updated)
        assert new_version != old_version

        print(f"Cached version: {old_version}")
        print(f"Current version: {new_version}")
        print(f"Version mismatch: {old_version != new_version}")

        # The cache policy rejects stale entries.
        assert stale_match["data_version"] != new_version
        print("PASS: Version-aware validation rejects stale answer")

        print("\n===== STEP 5: INVALIDATE AND REFRESH =====")

        cache.redis.delete(old_key)
        refreshed_answer = answer_from_db(updated)

        new_key = cache.store(
            question, refreshed_answer, vector, new_version
        )
        cached_keys.append(new_key)

        fresh_match = cache.search(vector)

        assert fresh_match is not None
        assert fresh_match["answer"] == refreshed_answer
        assert fresh_match["data_version"] == new_version

        print(f"Refreshed answer: {fresh_match['answer']}")
        print(f"Refreshed version: {fresh_match['data_version']}")
        print("PASS: Old cache entry invalidated")
        print("PASS: New answer matches updated MySQL record")

    finally:
        print("\n===== STEP 6: CLEANUP =====")

        if database_changed:
            with db.engine.begin() as conn:
                result = conn.execute(
                    text(
                        "UPDATE trials "
                        "SET participant_count = :old_count "
                        "WHERE id = :trial_id "
                        "AND participant_count = :new_count"
                    ),
                    {
                        "old_count": old_count,
                        "trial_id": trial_id,
                        "new_count": new_count,
                    },
                )
                if result.rowcount != 1:
                    print("WARNING: Could not safely restore trial")
                else:
                    print("PASS: Original MySQL value restored")

        if cached_keys:
            cache.redis.delete(*cached_keys)
            print("PASS: Temporary Redis entries removed")

    restored = read_trial(db, trial_id)
    assert restored["participant_count"] == old_count

    print("\n===== FINAL RESULT =====")
    print("PASS: Stale answer demonstrated")
    print("PASS: Version mismatch detected")
    print("PASS: Cache invalidated and refreshed")
    print("PASS: Database restored")
    print("=== PART 3 INVALIDATION COMPLETE ===")


if __name__ == "__main__":
    main()
