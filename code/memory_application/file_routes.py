from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .file_memory import build_system_prompt, handle_command

ROOT = Path(__file__).resolve().parents[2]
router = APIRouter(prefix="/api/file-memory", tags=["HW6 file memory"])


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=200)
    recent_facts: list[str] = Field(default_factory=list, max_length=20)


@router.post("/command")
def file_memory_command(payload: CommandRequest):
    return handle_command(ROOT, payload.command, payload.recent_facts)


@router.get("/prompt")
def file_memory_prompt():
    return {"system_prompt": build_system_prompt(ROOT)}
