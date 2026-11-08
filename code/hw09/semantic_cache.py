import asyncio
import hashlib
import json
import os
import sys
import time
import uuid
from array import array
from pathlib import Path

import redis
import requests
from redis.commands.search.field import TextField, TagField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code/hw08_kafka"))

from common import BOOTSTRAP, FINAL, INBOX, PREFIX, dumps, loads

CACHE_PREFIX = f"{PREFIX}:hw09:semantic"
INDEX_NAME = f"{PREFIX}:hw09:semantic:index"
DOCUMENT_PREFIX = f"{CACHE_PREFIX}:doc:"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


async def run_hw8_agent(question, timeout=240):
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    correlation_id = str(uuid.uuid4())

    consumer = AIOKafkaConsumer(
        FINAL,
        bootstrap_servers=BOOTSTRAP,
        group_id=f"{PREFIX}-hw09-reader-{uuid.uuid4()}",
        auto_offset_reset="latest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)

    await consumer.start()
    try:
        await producer.start()
        try:
            await producer.send_and_wait(
                INBOX,
                dumps({
                    "correlation_id": correlation_id,
                    "question": question,
                }),
            )

            deadline = time.monotonic() + timeout

            while time.monotonic() < deadline:
                messages = await consumer.getmany(
                    timeout_ms=1000,
                    max_records=100,
                )

                for batch in messages.values():
                    for message in batch:
                        result = loads(message.value)

                        if result.get("correlation_id") != correlation_id:
                            continue

                        return result

            raise TimeoutError(
                "HW8 agent timed out. Check planner, writer, "
                "reviewer and Kafka logs."
            )
        finally:
            await producer.stop()
    finally:
        await consumer.stop()


class SemanticCache:
    def __init__(self, threshold=0.85):
        self.threshold = float(threshold)
        self.redis = redis.Redis(
            host="127.0.0.1",
            port=6379,
            decode_responses=False,
        )
        self.redis.ping()

        self.dimension = None
        self.session = requests.Session()

    def embed(self, question):
        response = self.session.post(
            f"{OLLAMA_URL}/api/embed",
            json={
                "model": "nomic-embed-text",
                "input": question,
            },
            timeout=120,
        )
        response.raise_for_status()
        values = response.json()["embeddings"][0]

        if not values:
            raise RuntimeError("Embedding model returned no values")

        return array("f", values).tobytes(), len(values)

    def ensure_index(self, dimension):
        if self.dimension is not None:
            if self.dimension != dimension:
                raise RuntimeError("Embedding dimension changed")
            return

        self.dimension = dimension

        try:
            self.redis.ft(INDEX_NAME).info()
            return
        except ResponseError as exc:
            if "unknown index name" not in str(exc).lower():
                raise

        self.redis.ft(INDEX_NAME).create_index(
            [
                TextField("query"),
                TextField("answer"),
                TagField("data_version"),
                VectorField(
                    "embedding",
                    "HNSW",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": dimension,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
            ],
            definition=IndexDefinition(
                prefix=[DOCUMENT_PREFIX],
                index_type=IndexType.HASH,
            ),
        )
        print(f"Created Redis vector index: {INDEX_NAME}")

    def search(self, vector):
        query = (
            Query("*=>[KNN 1 @embedding $vector AS distance]")
            .sort_by("distance")
            .return_fields(
                "query", "answer", "data_version", "distance"
            )
            .dialect(2)
        )

        result = self.redis.ft(INDEX_NAME).search(
            query,
            query_params={"vector": vector},
        )

        if not result.docs:
            return None

        doc = result.docs[0]
        similarity = 1.0 - float(doc.distance)

        return {
            "answer": doc.answer,
            "query": doc.query,
            "data_version": doc.data_version,
            "similarity": similarity,
        }

    def store(self, question, answer, vector, data_version):
        document_id = str(uuid.uuid4())
        key = f"{DOCUMENT_PREFIX}{document_id}"

        self.redis.hset(
            key,
            mapping={
                "query": question,
                "answer": answer,
                "data_version": data_version,
                "embedding": vector,
            },
        )
        return key

    def clear_demo_cache(self):
        # Delete only this HW9 semantic cache, not the whole Redis DB.
        cursor = 0
        while True:
            cursor, keys = self.redis.scan(
                cursor=cursor,
                match=f"{DOCUMENT_PREFIX}*",
                count=100,
            )
            if keys:
                self.redis.delete(*keys)
            if cursor == 0:
                break

    async def answer(self, question):
        started = time.perf_counter()

        vector, dimension = self.embed(question)
        self.ensure_index(dimension)

        # Part 2 stores a version marker.
        # Part 3 will add record-aware invalidation.
        data_version = f"{PREFIX}_rel:v1"

        match = self.search(vector)
        similarity = match["similarity"] if match else None

        if (
            match
            and similarity >= self.threshold
            and match["data_version"] == data_version
        ):
            result = {
                "question": question,
                "answer": match["answer"],
                "is_cached": True,
                "similarity": round(similarity, 4),
                "latency_ms": round(
                    (time.perf_counter() - started) * 1000, 2
                ),
            }
            print(
                f"CACHE HIT similarity={similarity:.4f} "
                f"latency={result['latency_ms']}ms"
            )
            return result

        print(
            f"CACHE MISS similarity={similarity} "
            f"question={question}"
        )

        final_result = await run_hw8_agent(question)

        for field in (
            "final_answer",
            "answer",
            "response",
            "final",
            "text",
        ):
            value = final_result.get(field)
            if isinstance(value, str) and value.strip():
                final_answer = value
                break
        else:
            # Preserve the actual final Kafka message if its
            # answer uses an unfamiliar schema.
            final_answer = json.dumps(
                final_result,
                ensure_ascii=False,
                sort_keys=True,
            )

        self.store(question, final_answer, vector, data_version)

        return {
            "question": question,
            "answer": final_answer,
            "is_cached": False,
            "similarity": (
                round(similarity, 4)
                if similarity is not None
                else None
            ),
            "latency_ms": round(
                (time.perf_counter() - started) * 1000, 2
            ),
        }
