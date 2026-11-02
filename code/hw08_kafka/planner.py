import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from agent_common import ask_ollama, log
from common import BOOTSTRAP, INBOX, TASKS, dumps, loads


async def main():
    consumer = AIOKafkaConsumer(INBOX, bootstrap_servers=BOOTSTRAP,
                                group_id="s8561-planner", auto_offset_reset="earliest")
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start(); await producer.start(); print("Planner ready")
    try:
        async for message in consumer:
            item = loads(message.value); cid = item["correlation_id"]
            plan = ask_ollama("Create a short numbered plan for this question: " + item["question"])
            output = {"correlation_id": cid, "plan": plan}
            log("planner", {"correlation_id": cid, "input_topic": INBOX,
                             "output_topic": TASKS, "message": output})
            await producer.send_and_wait(TASKS, dumps(output)); await consumer.commit()
    finally:
        await consumer.stop(); await producer.stop()


if __name__ == "__main__": asyncio.run(main())
