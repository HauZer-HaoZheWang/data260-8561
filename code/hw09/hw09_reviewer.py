import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hw08_kafka'))
import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from agent_common import ask_ollama, log
from common import BOOTSTRAP, DRAFTS, FINAL, dumps, loads


async def main():
    consumer = AIOKafkaConsumer(DRAFTS, bootstrap_servers=BOOTSTRAP,
                                group_id="s8561-hw09-reviewer", auto_offset_reset="latest", max_poll_interval_ms=900000)
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start(); await producer.start(); print("Reviewer ready")
    try:
        async for message in consumer:
            item = loads(message.value); cid = item["correlation_id"]
            answer = await asyncio.to_thread(ask_ollama, "Review this draft and return the approved answer only:\n" + item["draft"])
            output = {"correlation_id": cid, "status": "approved", "answer": answer}
            log("reviewer", {"correlation_id": cid, "input_topic": DRAFTS,
                              "output_topic": FINAL, "message": output})
            await producer.send_and_wait(FINAL, dumps(output)); await consumer.commit()
    finally:
        await consumer.stop(); await producer.stop()


if __name__ == "__main__": asyncio.run(main())
