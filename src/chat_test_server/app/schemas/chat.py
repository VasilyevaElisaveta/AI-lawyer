from uuid import UUID
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: str
    reply: str
    document_created: bool
    document_bytes: bytes | None = None
    document_filename: str | None = None