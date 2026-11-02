import asyncio
import uuid
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from common import BOOTSTRAP, DLQ, TASKS, dumps, loads


async def main():
    poison_id = str(uuid.uuid4()); good_id = str(uuid.uuid4())
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    consumer = AIOKafkaConsumer(DLQ, bootstrap_servers=BOOTSTRAP,
                                group_id=f"s8561-dlq-reader-{uuid.uuid4()}",
                                auto_offset_reset="latest")
    await producer.start(); await consumer.start()
    try:
        await producer.send_and_wait(TASKS, dumps({"correlation_id": poison_id, "poison": True}))
        await producer.send_and_wait(TASKS, dumps({"correlation_id": good_id,
            "plan": "Explain one basic fact about clinical trials."}))
        print("SENT_POISON_AND_GOOD", {"poison_id": poison_id, "good_id": good_id})
        async for message in consumer:
            value = loads(message.value)
            if value.get("correlation_id") == poison_id:
                print("DLQ_RESULT", value); break
    finally:
        await consumer.stop(); await producer.stop()


if __name__ == "__main__": asyncio.run(main())
