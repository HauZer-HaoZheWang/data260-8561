import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from common import BOOTSTRAP, REQUESTS, RESPONSES, correlation_id, dumps, loads


class KafkaRPC:
    def __init__(self):
        # aiokafka 0.12 requires these objects to be created inside a
        # running event loop.  They are therefore initialized in start().
        self.producer = None
        self.consumer = None
        self.pending: dict[str, asyncio.Future] = {}
        self.task = None

    async def start(self):
        self.producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
        self.consumer = AIOKafkaConsumer(
            RESPONSES, bootstrap_servers=BOOTSTRAP, group_id="s8561-rpc-client",
            auto_offset_reset="latest", enable_auto_commit=True,
        )
        await self.producer.start(); await self.consumer.start()
        self.task = asyncio.create_task(self._read_responses())

    async def stop(self):
        if self.task: self.task.cancel()
        if self.consumer: await self.consumer.stop()
        if self.producer: await self.producer.stop()

    async def _read_responses(self):
        async for message in self.consumer:
            response = loads(message.value)
            cid = response.get("correlation_id")
            future = self.pending.pop(cid, None)
            if future and not future.done(): future.set_result(response)

    async def request(self, operation: str, data: dict, timeout: float = 30,
                      request_correlation_id: str | None = None):
        cid = request_correlation_id or correlation_id()
        request = {"correlation_id": cid, "reply_to": RESPONSES,
                   "operation": operation, "data": data}
        print(f"[CLIENT] send topic={REQUESTS} correlation_id={cid} message={request}")
        future = asyncio.get_running_loop().create_future()
        self.pending[cid] = future
        await self.producer.send_and_wait(REQUESTS, dumps(request))
        response = await asyncio.wait_for(future, timeout)
        print(f"[CLIENT] received correlation_id={response.get('correlation_id')} response={response}")
        return response
