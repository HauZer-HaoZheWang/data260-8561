import asyncio
import uuid
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from common import BOOTSTRAP, REQUESTS, RESPONSES, dumps, loads


async def main():
    cid = str(uuid.uuid4())
    request = {"correlation_id": cid, "reply_to": RESPONSES,
               "operation": "CREATE_TRIAL", "data": {
                   "brief_title": "Duplicate delivery test", "nct_code": "NCT87654321",
                   "participant_count": 20, "sponsor_id": 1}}
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    consumer = AIOKafkaConsumer(RESPONSES, bootstrap_servers=BOOTSTRAP,
                                group_id=f"s8561-duplicate-{uuid.uuid4()}",
                                auto_offset_reset="latest")
    await producer.start(); await consumer.start()
    try:
        print("REPLAY_REQUEST", request)
        await producer.send_and_wait(REQUESTS, dumps(request))
        await producer.send_and_wait(REQUESTS, dumps(request))
        replies = []
        async for message in consumer:
            response = loads(message.value)
            if response.get("correlation_id") == cid:
                replies.append(response); print("REPLAY_RESPONSE", response)
                if len(replies) == 2: break
        ids = [item.get("trial_id") for item in replies]
        print("IDEMPOTENCY_RESULT", {"same_correlation_id": True,
              "response_count": len(replies), "trial_ids": ids,
              "same_trial_id": len(set(ids)) == 1})
    finally:
        await consumer.stop(); await producer.stop()


if __name__ == "__main__": asyncio.run(main())
