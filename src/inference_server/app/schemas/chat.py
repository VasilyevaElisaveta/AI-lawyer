from pydantic import BaseModel
from typing import Optional, Any


class ChatNameRequest(BaseModel):
    raw_input: str
    chat_id: str


class ChatNameResponse(BaseModel):
    chat_id: str
    chat_name: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    run_id: str
    trace_id: str
    process_name: str


class ChatRequest(BaseModel):
    raw_input: str
    thread_id: str
    user_metadata: Optional[dict[str, Any]] = {}
    agent_type: Optional[str] = None  # router_agent / contract_agent / claims_agent / general_questions_agent


class ChatResponse(BaseModel):
    reply: str
    handled_by_agent: bool = True
    document_created: bool = False
    is_error: bool = False
    latency_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    run_id: str
    trace_id: str
    process_name: str