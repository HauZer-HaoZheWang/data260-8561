import os
from pathlib import Path

import redis
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "code/hw09/.env.local", override=True)
load_dotenv(ROOT / ".env")

PREFIX = os.getenv("PREFIX", "s8561")


class TrialCacheDB:
    def __init__(self):
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is missing in .env")

        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True,
        )

        self.redis_client.ping()
        self.prepare_database()

    def prepare_database(self):
        inspector = inspect(self.engine)

        if not inspector.has_table("trials"):
            raise RuntimeError("Existing trials table not found")

        columns = {
            column["name"]
            for column in inspector.get_columns("trials")
        }

        if "view_count" not in columns:
            with self.engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE trials "
                    "ADD COLUMN view_count BIGINT NOT NULL DEFAULT 0"
                ))
            print("Added view_count column to trials")
        else:
            print("view_count column already exists")

    def increment_trial_views(self, trial_id):
        trial_id = int(trial_id)
        if trial_id <= 0:
            raise ValueError("trial_id must be positive")

        key = f"{PREFIX}:views:trial:{trial_id}"

        with self.engine.connect() as conn:
            stored = conn.execute(
                text("SELECT view_count FROM trials WHERE id = :id"),
                {"id": trial_id},
            ).scalar_one_or_none()

        if stored is None:
            raise ValueError(f"Trial {trial_id} does not exist")

        # Initialize Redis from the database only if the key is absent.
        self.redis_client.set(key, int(stored), nx=True)

        # Redis atomic increment.
        count = self.redis_client.incr(key)

        # Persist after every 10 increments.
        if count % 10 == 0:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE trials SET view_count = :count "
                        "WHERE id = :id"
                    ),
                    {"count": count, "id": trial_id},
                )
            print(f"Synced views to database: {count}")

        return count

    def get_database_count(self, trial_id):
        with self.engine.connect() as conn:
            return conn.execute(
                text("SELECT view_count FROM trials WHERE id = :id"),
                {"id": trial_id},
            ).scalar_one()

    def get_redis_count(self, trial_id):
        key = f"{PREFIX}:views:trial:{int(trial_id)}"
        value = self.redis_client.get(key)
        return None if value is None else int(value)
