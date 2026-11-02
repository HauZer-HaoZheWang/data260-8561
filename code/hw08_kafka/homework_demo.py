import asyncio
from common import correlation_id
from rpc_client import KafkaRPC


TRIAL = {
    "brief_title": "Diabetes intervention study",
    "nct_code": "NCT12345678",
    "participant_count": 100,
    "sponsor_id": 1,
}


async def main():
    rpc = KafkaRPC(); await rpc.start()
    try:
        cid = correlation_id()
        print(f"[DEMO] one correlation_id for the complete CREATE_TRIAL -> GET_TRIAL flow: {cid}")
        created = await rpc.request("CREATE_TRIAL", TRIAL,
                                    request_correlation_id=cid)
        trial_id = created.get("trial_id")
        retrieved = await rpc.request("GET_TRIAL", {"trial_id": trial_id},
                                      request_correlation_id=cid)
        print("CREATE_TRIAL response:", created)
        print("GET_TRIAL response:", retrieved)
        print(f"correlation_id preserved across both operations: {cid}")
    finally:
        await rpc.stop()


if __name__ == "__main__":
    asyncio.run(main())
