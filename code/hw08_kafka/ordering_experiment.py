import asyncio
import json
import uuid
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from common import BOOTSTRAP, TASKS, dumps, loads


async def run(use_key: bool):
    run_id = str(uuid.uuid4()); group = f"s8561-order-{run_id}"
    consumer = AIOKafkaConsumer("s8561_drafts", bootstrap_servers=BOOTSTRAP, group_id=group,
                                auto_offset_reset="latest", enable_auto_commit=True)
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start(); await producer.start()
    try:
        for number in range(20):
            item = {"correlation_id": f"{run_id}-{number}", "run_id": run_id,
                    "sequence": number, "entity_key": "trial-order-demo",
                    "plan": f"sequence {number}"}
            key = b"trial-order-demo" if use_key else None
            # Force the no-key baseline across both partitions. The keyed run
            # lets Kafka hash the entity key and keep all messages together.
            partition = None if use_key else number % 2
            await producer.send_and_wait(TASKS, dumps(item), key=key,
                                         partition=partition)
        print("ORDERING_SENT", {"run_id": run_id, "use_key": use_key})
        seen = []
        seen_sequences = set()
        duplicate_count = 0
        async for message in consumer:
            item = loads(message.value)
            if item.get("run_id") == run_id:
                sequence = item["sequence"]
                if sequence in seen_sequences:
                    duplicate_count += 1
                    continue
                seen_sequences.add(sequence)
                seen.append({"sequence": sequence,
                             "task_partition": item.get("task_partition"),
                             "task_offset": item.get("task_offset")})
                if len(seen_sequences) == 20: break
        print("ORDERING_RESULT", json.dumps({"use_key": use_key,
              "unique_count": len(seen), "duplicates_ignored": duplicate_count,
              "processed_completion_order": seen,
              "sequence_order": [item["sequence"] for item in seen]}))
    finally:
        await consumer.stop(); await producer.stop()


async def main():
    await run(False); await run(True)


if __name__ == "__main__": asyncio.run(main())
