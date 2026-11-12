import asyncio
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from agent_common import ask_ollama, log
from common import BOOTSTRAP, DRAFTS, FINAL, dumps, loads
from hw10.trace import span, write_queue_wait


async def main():
    consumer = AIOKafkaConsumer(DRAFTS, bootstrap_servers=BOOTSTRAP,
                                group_id="s8561-reviewer", auto_offset_reset="earliest", max_poll_interval_ms=900000)
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start(); await producer.start(); print("Reviewer ready")
    try:
        async for message in consumer:
            item = loads(message.value); cid = item["correlation_id"]
            write_queue_wait(cid, "queue_wait_drafts_to_reviewer", item.get("produced_at", time.time()), time.time())
            with span(cid, "reviewer", input_topic=DRAFTS, output_topic=FINAL):
                answer = await asyncio.to_thread(ask_ollama, "Review this draft and return the approved answer only:\n" + item["draft"])
                output = {"correlation_id": cid, "trace_id": cid, "question": item.get("question", ""),
                          "plan": item.get("plan", ""), "draft": item.get("draft", ""),
                          "status": "approved", "answer": answer, "produced_at": time.time()}
                log("reviewer", {"correlation_id": cid, "input_topic": DRAFTS,
                                  "output_topic": FINAL, "message": output})
                await producer.send_and_wait(FINAL, dumps(output)); await consumer.commit()
    finally:
        await consumer.stop(); await producer.stop()


if __name__ == "__main__": asyncio.run(main())
