from uuid import UUID
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: str
    reply: str | None = None
    document_created: bool = False
    document_bytes: bytes | None = None
    document_filename: str | None = None