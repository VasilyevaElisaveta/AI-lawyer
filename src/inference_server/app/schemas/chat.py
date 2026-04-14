from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    raw_input: str
    thread_id: str
    agent_type: Optional[str] = None  # router / contract / claim / etc


class ChatResponse(BaseModel):
    reply: str
    handled_by_agent: bool = True
    document_created: bool = False