from contextlib import asynccontextmanager
from fastapi import FastAPI
from rpc_client import KafkaRPC
from common import PORT

rpc = KafkaRPC()


@asynccontextmanager
async def lifespan(_app):
    await rpc.start()
    print(f"FastAPI server started at http://127.0.0.1:{PORT}")
    yield
    await rpc.stop()


app = FastAPI(title="HW8 Kafka Trial API", lifespan=lifespan)


@app.get("/")
async def health():
    return {"status": "ok", "service": "hw08-kafka"}


@app.post("/trials")
async def trial_operation(payload: dict):
    return await rpc.request(payload["operation"], payload.get("data", {}))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=PORT)
