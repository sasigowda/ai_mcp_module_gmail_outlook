from pydantic import BaseModel, Field
from typing import Any
import uuid


class ChatMessage(BaseModel):
    role: str  # 'user' | 'assistant'
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = None
    mcp_server_ids: list[str] = Field(default_factory=list)
    llm_provider: str | None = None
    llm_model: str | None = None


class ConversationCreate(BaseModel):
    title: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    mcp_server_ids: list[str] = Field(default_factory=list)


class ConversationOut(BaseModel):
    id: str
    title: str | None
    llm_provider: str
    llm_model: str
    message_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: str
    role: str
    content: str | None
    tool_calls: Any | None
    tool_results: Any | None
    created_at: str

    class Config:
        from_attributes = True
