from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    raw_input: str
    thread_id: str
    agent_type: Optional[str] = None  # router_agent / contract_agent / claims_agent / general_questions_agent


class ChatResponse(BaseModel):
    reply: str
    handled_by_agent: bool = True
    document_created: bool = False
    is_error: bool = False