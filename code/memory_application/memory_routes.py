from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from .memory_service import aggregate_view, chat, memory_view
from .schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["HW6 memory"])


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    session_id = payload.session_id or str(uuid4())
    result = chat(payload.user_id, session_id, payload.message)
    return {"reply": result["reply"], "user_id": payload.user_id, "session_id": session_id, "memory_used": result["memory_used"], "metrics": result["metrics"]}


@router.get("/memory/{user_id}")
def get_memory(user_id: str):
    return memory_view(user_id)


@router.get("/aggregate/{user_id}")
def get_aggregate(user_id: str):
    return aggregate_view(user_id)

