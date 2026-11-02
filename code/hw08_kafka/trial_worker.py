import asyncio
import json
import os
import uuid
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from common import BOOTSTRAP, REQUESTS, dumps, loads, validate_trial

TRIALS: dict[str, dict] = {}
PROCESSED: dict[str, dict] = {}
IDEMPOTENCY_ENABLED = os.getenv("IDEMPOTENCY_ENABLED", "1") != "0"


def process(request: dict) -> dict:
    operation = request.get("operation")
    data = request.get("data")
    if not isinstance(data, dict):
        return {"success": False, "error": "data must be an object"}
    if operation == "CREATE_TRIAL":
        error = validate_trial(data)
        if error:
            return {"success": False, "error": error}
        trial_id = str(uuid.uuid4())
        trial = {"trial_id": trial_id, **data}
        TRIALS[trial_id] = trial
        return {"success": True, "trial_id": trial_id, "message": "Trial created"}
    if operation == "GET_TRIAL":
        trial_id = data.get("trial_id")
        if trial_id not in TRIALS:
            return {"success": False, "error": "Trial not found"}
        return {"success": True, "trial": TRIALS[trial_id]}
    return {"success": False, "error": "Unknown operation"}


async def main():
    consumer = AIOKafkaConsumer(
        REQUESTS, bootstrap_servers=BOOTSTRAP, group_id="s8561-trial-worker",
        auto_offset_reset="earliest", enable_auto_commit=False,
    )
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start(); await producer.start()
    print("Consumer is ready and listening...")
    try:
        async for message in consumer:
            try:
                request = loads(message.value)
                cid = request.get("correlation_id")
                print(f"[WORKER] received correlation_id={cid} offset={message.offset}")
                cache_key = (cid, request.get("operation"))
                if IDEMPOTENCY_ENABLED and cache_key in PROCESSED:
                    result = PROCESSED[cache_key]
                    print(f"[WORKER] idempotent replay correlation_id={cid}")
                else:
                    result = process(request)
                    # Idempotency is scoped to correlation_id and operation;
                    # the demo intentionally reuses one ID for CREATE then GET.
                    if IDEMPOTENCY_ENABLED:
                        PROCESSED[cache_key] = result
                response = {"correlation_id": cid, **result}
                await producer.send_and_wait(request["reply_to"], dumps(response))
                await consumer.commit()
                print(f"[WORKER] replied correlation_id={cid}; committed offset={message.offset}")
            except Exception as exc:
                print(f"[WORKER] processing error: {exc}")
    finally:
        await consumer.stop(); await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
