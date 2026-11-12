import asyncio
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from agent_common import ask_ollama, log
from common import BOOTSTRAP, INBOX, TASKS, dumps, loads
from hw10.trace import span, write_queue_wait


async def main():
    consumer = AIOKafkaConsumer(INBOX, bootstrap_servers=BOOTSTRAP,
                                group_id="s8561-planner", auto_offset_reset="earliest", max_poll_interval_ms=900000)
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start(); await producer.start(); print("Planner ready")
    try:
        async for message in consumer:
            item = loads(message.value); cid = item["correlation_id"]
            write_queue_wait(cid, "queue_wait_inbox_to_planner", item.get("produced_at", time.time()), time.time())
            with span(cid, "planner", input_topic=INBOX, output_topic=TASKS):
                plan = await asyncio.to_thread(ask_ollama, "Create a short numbered plan for this question: " + item["question"])
                output = {"correlation_id": cid, "trace_id": cid, "question": item["question"], "plan": plan,
                          "produced_at": time.time()}
                log("planner", {"correlation_id": cid, "input_topic": INBOX,
                                 "output_topic": TASKS, "message": output})
                await producer.send_and_wait(TASKS, dumps(output)); await consumer.commit()
    finally:
        await consumer.stop(); await producer.stop()


if __name__ == "__main__": asyncio.run(main())
