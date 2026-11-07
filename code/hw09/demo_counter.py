import argparse

from sqlalchemy import text

from cache_db import PREFIX, TrialCacheDB


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Reset only the demo trial's view count",
    )
    args = parser.parse_args()

    print("Student: Haozhe Wang")
    print("Homework: DATA 260 HW9")
    print("Part 1: Redis View Counter")
    print(f"PREFIX: {PREFIX}")

    cache = TrialCacheDB()

    with cache.engine.connect() as conn:
        trial_id = conn.execute(
            text("SELECT id FROM trials ORDER BY id LIMIT 1")
        ).scalar_one_or_none()

    if trial_id is None:
        raise RuntimeError(
            "No Trial records found. A test Trial is needed."
        )

    print(f"Test Trial ID: {trial_id}")

    if args.reset_demo:
        # Only the new view_count field is reset.
        # No clinical-trial attributes are changed.
        with cache.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE trials SET view_count = 0 "
                    "WHERE id = :id"
                ),
                {"id": trial_id},
            )
        cache.redis_client.delete(
            f"{PREFIX}:views:trial:{trial_id}"
        )
        print("Demo view counter reset to 0")

    print("\n=== Testing Counter ===")

    start = cache.get_redis_count(trial_id)
    if start is None:
        start = cache.get_database_count(trial_id)

    for access in range(1, 26):
        count = cache.increment_trial_views(trial_id)
        print(f"Access #{access}: Total = {count}")
        assert count == start + access

    redis_count = cache.get_redis_count(trial_id)
    db_count = cache.get_database_count(trial_id)

    print("\n=== Redis vs Database ===")
    print(f"Redis count: {redis_count}")
    print(f"Database count: {db_count}")

    expected_db_count = (
        redis_count // 10
    ) * 10

    assert db_count == expected_db_count
    print("PASS: Redis counter and database sync verified")
    print("=== PART 1 COMPLETE ===")


if __name__ == "__main__":
    main()
