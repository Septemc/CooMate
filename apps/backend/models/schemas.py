from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    action: str = "chat"  # chat | regenerate_angles | export_review


class StepChunk(BaseModel):
    type: str  # "step" | "done"
    step: Optional[int] = None
    content: Optional[str] = None
    conversation_id: Optional[str] = None


class MessageOut(BaseModel):
    id: str
    role: str  # "user" | "assistant"
    content: str
    steps: Optional[list[dict]] = None
    timestamp: float


class ConversationOut(BaseModel):
    id: str
    title: str
    messages: list[MessageOut]
    created_at: float
    updated_at: float


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: float
