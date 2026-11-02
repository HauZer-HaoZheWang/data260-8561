import asyncio
import uuid
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from common import BOOTSTRAP, FINAL, INBOX, dumps, loads


async def main():
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    consumer = AIOKafkaConsumer(
        FINAL, bootstrap_servers=BOOTSTRAP, group_id=f"s8561-final-reader-{uuid.uuid4()}",
        auto_offset_reset="earliest", enable_auto_commit=True,
    )
    await producer.start()
    await consumer.start()
    try:
        item = {"correlation_id": str(uuid.uuid4()),
                "question": "What should a reader know about a clinical trial?"}
        await producer.send_and_wait(INBOX, dumps(item))
        print("Sent to inbox:", item)
        async for message in consumer:
            result = loads(message.value)
            if result.get("correlation_id") == item["correlation_id"]:
                print("Received final result from s8561_final:", result)
                break
    finally:
        await consumer.stop(); await producer.stop()


if __name__ == "__main__": asyncio.run(main())
