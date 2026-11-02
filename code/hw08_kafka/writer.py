import asyncio
import os
import time
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from agent_common import ask_ollama, log
from common import BOOTSTRAP, DRAFTS, DLQ, TASKS, dumps, loads

MAX_RETRIES = 3
PAUSE = float(os.getenv("WRITER_PAUSE_SECONDS", "0"))


async def main():
    consumer = AIOKafkaConsumer(TASKS, bootstrap_servers=BOOTSTRAP,
                                group_id="s8561-writers", auto_offset_reset="earliest",
                                enable_auto_commit=False)
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start(); await producer.start(); print("Writer ready")
    try:
        async for message in consumer:
            item = loads(message.value); cid = item.get("correlation_id")
            log("writer", {"event": "START_PROCESSING", "correlation_id": cid,
                            "partition": message.partition, "offset": message.offset})
            if PAUSE:
                print(f"[WRITER] pause_before_llm seconds={PAUSE}; kill now for death test")
                await asyncio.sleep(PAUSE)
            retries = 0
            while True:
                try:
                    if item.get("poison"):
                        raise ValueError("intentional poison message")
                    draft = ask_ollama("Write a concise answer using this plan:\n" + item["plan"])
                    output = {"correlation_id": cid, "draft": draft,
                              "processed_at_ns": time.time_ns(),
                              "task_partition": message.partition,
                              "task_offset": message.offset}
                    for field in ("run_id", "sequence", "entity_key"):
                        if field in item:
                            output[field] = item[field]
                    log("writer", {"event": "SEND_DRAFT", "correlation_id": cid,
                                    "input_topic": TASKS, "output_topic": DRAFTS})
                    await producer.send_and_wait(DRAFTS, dumps(output))
                    await consumer.commit()
                    log("writer", {"event": "COMMIT_SUCCESS", "correlation_id": cid,
                                    "partition": message.partition, "offset": message.offset})
                    break
                except Exception as exc:
                    retries += 1
                    print(f"[WRITER] retry={retries}/{MAX_RETRIES} correlation_id={cid} error={exc}")
                    if retries >= MAX_RETRIES:
                        dlq = {"correlation_id": cid, "error": str(exc),
                               "original_message": item, "retries": retries}
                        await producer.send_and_wait(DLQ, dumps(dlq))
                        await consumer.commit()
                        print(f"[WRITER] sent to {DLQ}; committed poison offset={message.offset}")
                        break
                    await asyncio.sleep(1)
    finally:
        await consumer.stop(); await producer.stop()


if __name__ == "__main__": asyncio.run(main())
