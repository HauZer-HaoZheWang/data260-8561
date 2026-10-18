from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentStatus = Literal["planned", "recruiting", "active", "completed", "withdrawn"]
DocumentCategory = Literal["interventional", "observational", "expanded_access"]


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    status: DocumentStatus = "planned"
    category: DocumentCategory
    start_date: datetime


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    status: DocumentStatus | None = None
    category: DocumentCategory | None = None
    start_date: datetime | None = None


class DocumentOut(DocumentCreate):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    session_id: str | None = Field(default=None, max_length=100)
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    user_id: str
    session_id: str
    memory_used: dict
    metrics: dict
